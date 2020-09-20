import clr

# TODO: Build a searching mechanism (is there one in pythonnet or C#) so these don't need to be in the cwd.
clr.AddReference('WindowsBase')


from . import utils, converters, datatypes
from .utils import get_wrapper_class, wrap_python_method, wrap_csharp_method
