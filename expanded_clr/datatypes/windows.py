from clr import System

from ..utils import csharp_namedtuple, get_wrapper_class

Padding = csharp_namedtuple('Padding', 'Left Top Right Bottom')
Rect = get_wrapper_class(System.Windows.Rect)
Vector = get_wrapper_class(System.Windows.Vector)
Point = get_wrapper_class(System.Windows.Point)
