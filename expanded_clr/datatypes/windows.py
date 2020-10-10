import clr

from clr import System

from ..utils import csharp_namedtuple, get_wrapper_class

# Datatypes from WindowsBase are only available if WindowsBase is available.
try:
    clr.AddReference('WindowsBase')
except System.IO.FileNotFoundException:
    pass
else:
    Rect = get_wrapper_class(System.Windows.Rect)
    Vector = get_wrapper_class(System.Windows.Vector)
    Point = get_wrapper_class(System.Windows.Point)

Padding = csharp_namedtuple('Padding', 'Left Top Right Bottom')
