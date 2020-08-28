import inspect
import logging

from collections import namedtuple, defaultdict
from functools import wraps

import clr

from clr import System

logger = logging.getLogger(__name__)
__WRAPPER_CLASSES = dict()


def python_name_to_csharp_name(name):
    if is_python_name(name):
        return name.title().replace('_', '')

    return name


def is_python_name(name):
    return '_' in name or name.islower()


def get_class_from_name(klass_name, base_module=clr):
    """Get the C# class from the string of the name."""
    splitted = klass_name.split('.', 1)
    attr = getattr(base_module, splitted[0], None)
    if attr and len(splitted) > 1:
        return get_class_from_name(splitted[1], attr)

    if not attr:
        # Now we need to handle nested types.
        splitted = klass_name.split('+', 1)
        attr = getattr(base_module, splitted[0], None)

        # This must be a private subclass, like BoolCondition of Condition. Return the next best thing.
        if not attr:
            return base_module

        if len(splitted) > 1:
            return get_class_from_name(splitted[1], attr)

    return attr


def csharp_namedtuple(*args, **kwargs):
    """Allow for CSharp names and python names."""
    klass = namedtuple(*args, **kwargs)

    class Subclass(klass):
        def __getattr__(self, name):
            return super(Subclass, self).__getattr__(python_name_to_csharp_name(name))

        def __setattr__(self, name, value):
            return super(Subclass, self).__setattr__(python_name_to_csharp_name(name), value)

    Subclass.__name__ = Subclass.__qualname__ = klass.__name__
    return Subclass


def wrap_csharp_method(method, arg_type_sets):
    """
    Wraps a C# method, ensuring the arguments are C# arguments the return type is a Python type.

    Args:
        method (callable): The C# method to wrap.
        arg_type_sets (list): A list of tuples, containing possible argument types. We will try to convert the
            arguments given to the method to one of the given sets of types. If successful, the C# method is called.
            If C# accepts the given types, the method is returned.
    """
    @wraps(method)
    def wrapper(*args):
        for arg_types in arg_type_sets:
            if len(args) != len(arg_types):
                continue

            try:
                # Since type matching is important, do not force here.
                args_ = tuple(converters.ValueConverter(arg_types[arg_i]).to_csharp(arg)
                              for arg_i, arg in enumerate(args))
                return converters.ValueConverter.to_python(method(*args_))
            except TypeError:
                # pythonnet raises a TypeError if the given type doesn't match
                pass

        raise ValueError(f"Could not convert all arguments {args} for {method}")

    return wrapper


def wrap_python_method(method, return_type=None):
    """
    Wraps a Python method, ensuring the arguments are Python arguments and the output is C#.
    """
    @wraps(method)
    def wrapper(*args):
        args_ = tuple(converters.ValueConverter.to_python(arg) for arg in args)

        try:
            ret = method(*args_)
        except Exception:
            logger.error('Exception in wrapped method', exc_info=True)
            raise

        if return_type is not None:
            return converters.ValueConverter(return_type).to_csharp(ret, True)

        return None

    return wrapper


def get_wrapper_class(klass):
    """
    Get the wrapper class for the given C# class (or instance).

    Args:
        klass (System.Type, System.Object): If an instance (System.Object), this just gets rerun with `type(klass)`.
            Should NOT be a System.RuntimeType.
    """
    global __WRAPPER_CLASSES
    klass_ = klass

    if isinstance(klass, clr.System.Type):
        return get_wrapper_class(get_class_from_name(klass.ToString()))

    if isinstance(klass, clr.System.Object):
        # This is an instance. Get the type and pass it back in.
        return get_wrapper_class(klass.GetType())

    if klass not in __WRAPPER_CLASSES:
        class MetaWrapper(type):
            def __getattr__(cls, item):
                """This is for static items in the class, ie, System.Windows.Forms.Form.ActiveForm"""
                csharp_name = python_name_to_csharp_name(item)
                ret_val = getattr(cls.klass, csharp_name)

                if csharp_name in cls.attributes:
                    return converters.ValueConverter.to_python(ret_val)
                if csharp_name in cls.methods:
                    arg_type_set = cls.methods[csharp_name]

                    return wrap_csharp_method(ret_val, arg_type_set)
                if csharp_name in cls.events:
                    return get_wrapper_class(System.EventHandler)(instance=ret_val)
                if csharp_name in cls.nested:
                    return WrapperClass(ret_val)

                raise AttributeError(item)

            def __instancecheck__(cls, instance):
                return isinstance(getattr(instance, 'instance', instance), cls.klass)

        class WrapperClass(metaclass=MetaWrapper):
            """
            A wrapper class.

            Attributes:
                klass (System.Type): The original C# Type.
                clrtype (System.RuntimeType): The CLR type.
                methods (set): method name -> list of tuples, consisting of possible argument types.
                attributes (dict): attribute name -> attribute class
                events (set): A set of event names in this class.
                nested (set): A set of nested classes in this class.
                constructors (list): A list of tuples, consisting of possible argument types to constructors.
            """
            klass = klass_
            clrtype = clr.GetClrType(klass_)
            methods = defaultdict(list)
            attributes = dict()
            events = set()
            nested = set()
            constructors = list()

            def __init__(self, *args, instance=None, **kwargs):
                if instance is not None:
                    # We were given an instance, simple.
                    self.instance = instance
                else:
                    # We were not provided an instance but were given args,
                    #   so we must try to match the arguments to one of the constructors
                    for arg_types in self.constructors:
                        if len(args) != len(arg_types):
                            continue

                        try:
                            # Since type matching is important, do not force here.
                            args_ = tuple(converters.ValueConverter(arg_types[arg_i]).to_csharp(arg)
                                          for arg_i, arg in enumerate(args))
                            self.instance = self.klass(*args_)
                            break
                        except TypeError:
                            # pythonnet raises a TypeError if the given type doesn't match
                            pass
                    else:
                        raise ValueError(f"Could not convert all arguments {args} for {self.klass}")

                # Now that the object is setup, lets use the kwargs to set attributes
                for prop_name, val in kwargs.items():
                    csharp_name = python_name_to_csharp_name(prop_name)

                    # TODO: Instead of using a hard coded list here,
                    #   detect if the attribute we're setting is a list or collection
                    if csharp_name in {'Controls', 'DropDownItems', 'Items'}:
                        getattr(self, prop_name).add_range(val)
                        continue

                    if csharp_name in self.attributes:
                        setattr(self, prop_name, val)
                    elif csharp_name in self.events:
                        if callable(val):
                            getattr(self, csharp_name).__iadd__(val)
                        else:
                            for handler in val:
                                getattr(self, csharp_name).__iadd__(handler)
                    else:
                        raise TypeError(f"__init__() got an unexpected keyword argument {prop_name!r}")

            def __getattr__(self, name):
                csharp_name = python_name_to_csharp_name(name)
                csharp_val = getattr(self.instance, csharp_name)

                if csharp_name in self.attributes:
                    return converters.ValueConverter.to_python(csharp_val)
                if csharp_name in self.methods:
                    method = csharp_val
                    arg_type_set = self.methods[csharp_name]

                    return wrap_csharp_method(method, arg_type_set)
                if csharp_name in self.events:
                    return get_wrapper_class(System.EventHandler)(instance=csharp_val)
                if csharp_name in self.nested:
                    return WrapperClass(csharp_val)

                raise AttributeError(name)

            def __setattr__(self, name, value):
                if not name.startswith('_'):
                    csharp_name = python_name_to_csharp_name(name)

                    if csharp_name in self.events:
                        value = converters.ValueConverter(System.EventHandler).to_csharp(value)
                        setattr(self.instance, csharp_name, value)
                    if csharp_name in self.methods:
                        raise ValueError('property is read-only')
                    if csharp_name in self.nested:
                        raise ValueError('property is read-only')
                    if csharp_name in self.attributes:
                        if self.attributes[csharp_name] is None:
                            raise ValueError('property is read-only')

                        return setattr(self.instance, csharp_name,
                                       converters.ValueConverter(self.attributes[csharp_name]).to_csharp(value, True))

                return super(WrapperClass, self).__setattr__(name, value)

            def __getitem__(self, item):
                return self.instance[item]

            def __setitem__(self, item, value):
                self.instance[item] = value

            def __iter__(self):
                return iter(self.instance)

            def __eq__(self, other):
                other_instance = getattr(other, 'instance', other)

                return self.instance.__eq__(other_instance)

        for field in WrapperClass.clrtype.GetMembers(
                # The default search will get public items only, protected not included. We want everything
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance
                | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static):
            field_name = field.Name
            if any(field_name.startswith(x) for x in ['get_', 'set_', 'add_', 'remove_', 'op_']):
                continue

            if isinstance(field, System.Reflection.MethodInfo):
                WrapperClass.methods[field_name].append(tuple(
                    param_info.ParameterType for param_info in field.GetParameters()
                ))
            elif isinstance(field, System.Reflection.EventInfo):
                WrapperClass.events.add(field_name)
            elif isinstance(field, System.Reflection.PropertyInfo):
                WrapperClass.attributes[field_name] = field.PropertyType
            elif isinstance(field, System.Reflection.FieldInfo):
                WrapperClass.attributes[field_name] = field.FieldType
            elif isinstance(field, System.Type):
                WrapperClass.nested.add(field_name)
            elif isinstance(field, System.Reflection.ConstructorInfo):
                WrapperClass.constructors.append(tuple(
                    param_info.ParameterType for param_info in field.GetParameters()
                ))
            else:
                logger.warning('Unknown member type info %r for field %s on class %s',
                               field, field_name, WrapperClass.klass)

        WrapperClass.__name__ = WrapperClass.__qualname__ = klass.__name__

        # We need to set the WrapperClass's module to the module that called us,
        #   eg netforms.drawing or netforms.controls
        calling_frame = inspect.stack()[1]
        calling_module = inspect.getmodule(calling_frame[0])
        WrapperClass.__module__ = calling_module.__name__ \
            if calling_module else '__main__'  # We were called from the command line, for testing...

        __WRAPPER_CLASSES[klass] = WrapperClass

    # Recursively look for subclasses, for the below special stuff...
    wrapper_class_subclasses = __WRAPPER_CLASSES[klass].__subclasses__()
    while wrapper_class_subclasses:
        __WRAPPER_CLASSES[klass] = wrapper_class_subclasses[0]
        wrapper_class_subclasses = __WRAPPER_CLASSES[klass].__subclasses__()

    return __WRAPPER_CLASSES[klass]


from . import converters
