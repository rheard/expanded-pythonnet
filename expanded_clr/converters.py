"""Converters are responsible from translating types between Python and C#"""

import datetime as dt
import logging

from clr import System, GetClrType

from . import datatypes, utils

logger = logging.getLogger(__name__)


class ValueConverter(object):
    """
    Handle conversions between C# values and Python values for a particular C# class.

    Attributes:
        klasses (set): The C# class we're converting from. Not a RuntimeType, but an actual class.
    """
    klasses = set()

    def __new__(cls, klass):
        """Find the converter for klass, see get_converter."""
        if cls is ValueConverter:
            converter = cls.get_converter(klass)
            if converter:
                return converter

        return super(ValueConverter, cls).__new__(cls)

    def __init__(self, klass):
        if isinstance(klass, System.Type):
            # This is a RuntimeType class
            self.clr_type = klass
            self.klass = utils.get_class_from_name(klass.ToString())
        else:
            # This is a class from C#, not a RuntimeType
            self.klass = klass
            self.clr_type = GetClrType(self.klass)

    @classmethod
    def get_converter(cls, klass):
        """
        Find the converter for klass.

        Args:
            klass (System.Type, or class): The class to get the converter for. Can be a regular C# class
                or a RuntimeType.
        """
        if not isinstance(klass, System.Type):
            klass = GetClrType(klass)

        if klass.IsArray or GetClrType(System.Collections.ICollection).IsAssignableFrom(klass):
            # This is an array or a collection, so just use the WrappedListConverter
            return WrappedListConverter(utils.get_class_from_name(klass.ToString()))

        if klass.Equals(System.Object):
            # Any object will do, so use no special converter...
            return None

        for converter in cls.__subclasses__():
            for klass_ in converter.klasses:
                if klass.Equals(klass_) or klass.IsSubclassOf(klass_):
                    return converter(klass_)

            # Also recursively check this subclass' subclasses.
            subclass_converter = converter.get_converter(klass)
            if subclass_converter:
                return subclass_converter

        return None

    @classmethod
    def to_python(cls, value):
        """Convert the C# value to Python."""
        if isinstance(value, System.Object):
            # This is not a Python friendly object, lets try to find one of our converters...
            converter = cls.get_converter(value.GetType())

            if converter is None or isinstance(converter, WrappedListConverter):
                # We've failed to find a better converter... To play it safe we better wrap whatever
                #   the value is so that we at least get name and type conversion...
                #       Or this is an array/collection that should get wrapped...
                return utils.get_wrapper_class(value.GetType())(instance=value)

            return converter.to_python(value)

        return value  # The basic operation is to just return the value...

    def to_csharp(self, value, force=False):
        """
        Convert the Python value to C#.

        First check if this is a wrapped object, otherwise just return the value...
        """
        return getattr(value, 'instance', value)


# region Basic Type Converters
class BasicTypeConverter(ValueConverter):
    """
    Converts a basic Python type to a basic C# type.

    These conversions should mostly be handled by pythonnet, when taking C# values to Python.

    Going the other way though we want to help things along in certain situations.
        For instance if an attribute is expecting a str but an int is provided, a simple conversion
        by doing str(value) would help.

    However we also don't want to get in the way of overloaded method resolution, hence the force argument.
        We will force type conversion for attributes and method return types, but not for method arguments.

    Attributes:
        python_type (type): The python type to convert to before calling the C# method.
        python_types (tuple, optional): A tuple of python types that this **supports**. The above python_type is
            automatically considered here.

            If we are not forcing conversion, and the provided value is not one of the python_types, a TypeError
                is automatically raised.

            While forcing we can be more flexible in our accepted types, and we will let Python raise those errors.
    """

    def to_csharp(self, value, force=False):
        if isinstance(value, self.klass):
            # This is the C# type we expect already, so do nothing...
            return value

        python_types = getattr(self, 'python_types', tuple()) + (self.python_type, )

        if not force and not isinstance(value, python_types):
            raise TypeError(value)

        return self.klass(self.python_type(value))


class StrConverter(BasicTypeConverter):
    klasses = {System.String}
    python_type = str


class IntConverter(BasicTypeConverter):
    klasses = {System.Int64, System.Int32, System.Int16, System.Byte,
               System.UInt64, System.UInt32, System.UInt16, System.SByte,
               System.Char}
    python_type = int
    python_types = (float, )

    def to_csharp(self, value, force=False):
        if isinstance(value, float) and self.klass in {System.Char}:
            raise TypeError("Cannot use a float in place of a char!")

        if isinstance(value, float) and not value.is_integer():
            raise TypeError(f"Got {value} but expected an integer!")

        return super(IntConverter, self).to_csharp(value, force)


class FloatConverter(BasicTypeConverter):
    klasses = {System.Double, System.Single, System.Decimal}
    python_type = float
    python_types = (int, )


class BoolConverter(BasicTypeConverter):
    klasses = {System.Boolean}
    python_type = bool
# endregion


class WrappedListConverter(ValueConverter):
    """
    Handles wrapping arrays and collections of objects.

    Going from C# to Python, the Array or Collection will simply be wrapped like anything else, and the wrapper
        will handle iteration.

    Typically one wouldn't set directly, but would use another method such as `add_range`. However pythonnet will
        accept a list, so we just need to convert each element in the given iterable, and then provide that list.
    """

    def to_csharp(self, value, force=False):
        if hasattr(value, "instance"):
            # This is a wrapped collection/array...
            return value.instance

        if isinstance(value, self.klass):
            # This is a native C# collection/array...
            return value

        # We need to know the expected type of items in this collection/array...
        contains_method = self.clr_type.GetMethod('Contains')
        if contains_method:
            # To get the collection's element type, we're going to get the argument type for Contains.
            element_type = contains_method.GetParameters()[0].ParameterType
        else:
            # To get an array's element type, we're going to get the return type for Get.
            element_type = self.clr_type.GetMethod("Get").ReturnType

        return [ValueConverter(element_type).to_csharp(value_, force) for value_ in value]


class DateTimeTypeConverter(ValueConverter):
    """
    Converts between System.DateTime and datetime.datetime

    Notes:
        C# does not distinguish between dates and datetimes like Python does.
            In C#, a date is just a datetime at midnight.

        This can lead to some inconsistencies. Such as the fact that a date can be accepted,
            but it will come back out as a datetime. Take the following for example:

        >>> today = datetime.now().date()
        >>> control.max_date = today
        >>> print(control.max_date == today)
        False
        >>> print(control.max_date.date() == today)
        True

        To fix this one would have to try to guess if a C# System.DateTime object is referencing a
            time at midnight or just a date. An effort to guess is doomed to failure so a datetime
            is always returned; if a date is expected use .date().
    """
    klasses = {System.DateTime}

    def to_csharp(self, value, force=False):
        if isinstance(value, self.klass):
            return value

        if not isinstance(value, dt.date):
            raise TypeError(value)

        # We may have been given a date instead of a datetime, so fill in the time info...
        hour = getattr(value, 'hour', 0)
        minute = getattr(value, 'minute', 0)
        second = getattr(value, 'second', 0)
        microsecond = getattr(value, 'microsecond', 0)
        tzinfo = getattr(value, 'tzinfo')

        # C# just does not provide a lot of options for timezone... Its either UTC, Local, or unspecified
        timezone_info = System.DateTimeKind.Unspecified
        if tzinfo == dt.datetime.now().astimezone().tzinfo:  # Is this the local timezone?
            timezone_info = System.DateTimeKind.Local
        elif tzinfo == dt.timezone.utc:
            timezone_info = System.DateTimeKind.Utc
        elif tzinfo is not None:
            ValueError(f"A timezone other than None, UTC or local was used ({value.tzinfo})")

        return self.klass(value.year, value.month, value.day, hour, minute, second,
                          microsecond // 1000, timezone_info)

    @classmethod
    def to_python(cls, value):
        tzinfo = None
        if value.Kind == System.DateTimeKind.Local:
            tzinfo = dt.datetime.now().astimezone().tzinfo
        elif value.Kind == System.DateTimeKind.Utc:
            tzinfo = dt.timezone.utc

        return dt.datetime(value.Year, value.Month, value.Day, value.Hour, value.Minute, value.Second,
                           value.Millisecond * 1000, tzinfo)


class TimeDeltaTypeConverter(ValueConverter):
    """
    Converts between System.TimeSpan and datetime.timedelta

    Accepted types are:
        timedelta: Will be converted.
        datetime: Will be converted to a timedelta by finding the difference between the given datetime and now.
        float or int: The number of seconds. Can be infinity for the max timedelta.
    """
    klasses = {System.TimeSpan}

    def to_csharp(self, value, force=False):
        if isinstance(value, self.klass):
            return value

        if not isinstance(value, (dt.timedelta, dt.datetime, int, float)):
            raise TypeError(value)

        if value == float('inf'):
            value = dt.timedelta.max
        elif isinstance(value, dt.datetime):
            now = dt.datetime.now()
            if now > value:
                value = now - value
            elif value < now:
                value -= now
        elif isinstance(value, (float, int)):
            value = dt.timedelta(seconds=value)

        days = value.days
        hours = value.seconds // 60**2
        minutes = value.seconds // 60
        seconds = value.seconds % 60
        milliseconds = value.microseconds // 1000

        return self.klass(days, hours, minutes, seconds, milliseconds)

    @classmethod
    def to_python(cls, value):
        return dt.timedelta(
            days=value.Days,
            seconds=value.Seconds,
            milliseconds=value.Milliseconds,
            minutes=value.Minutes,
            hours=value.Hours,
        )


# region Namedtuple Converters
class NamedTupleConverter(ValueConverter):
    """
    Handles conversion for classes that can be handled with a simple namedtuple, such as System.Drawing.Point.

    Going from Python to C#, the default behavior is to call the C# constructor using *value, meaning a namedtuple or
        tuple are acceptable.

    Going from C# to Python, we simply need to provide the values to the declared namedtuple.

    Attributes:
        python_klass: The Python class to use. By default, fields will be supplied as arguments.
    """

    @classmethod
    def to_python(cls, value):
        """Convert the input C# value to Python."""
        args = (getattr(value, field) for field in cls.python_klass._fields)
        args = (ValueConverter.to_python(value) if isinstance(value, System.Object) else value for value in args)
        return cls.python_klass(*args)

    def to_csharp(self, value, force=False):
        """Convert the input Python value to C#."""
        if isinstance(value, self.klass):
            return value

        wrapper_class = utils.get_wrapper_class(self.klass)

        # Here we iterate over the fields in the namedtuple, and use those field names to get the fields'
        #   expected types from C#, and then convert the values in the tuple to those expected types.
        #       We won't force since these are effectively arguments for a constructor.
        value = tuple(ValueConverter(wrapper_class.attributes[field]).to_csharp(value[field_i])

                      for field_i, field in enumerate(self.python_klass._fields)

                      if field in wrapper_class.attributes)

        return self.klass(*value)


class PaddingConverter(NamedTupleConverter):
    klasses = {System.Windows.Forms.Padding}
    python_klass = datatypes.windows.Padding


class PointConverter(NamedTupleConverter):
    klasses = {System.Drawing.Point, System.Drawing.PointF}
    python_klass = datatypes.drawing.Point


class SizeConverter(NamedTupleConverter):
    klasses = {System.Drawing.Size, System.Drawing.SizeF}
    python_klass = datatypes.drawing.Size


class RectangleConverter(NamedTupleConverter):
    klasses = {System.Drawing.Rectangle}
    python_klass = datatypes.drawing.Rectangle
# endregion
