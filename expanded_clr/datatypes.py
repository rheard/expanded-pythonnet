"""Here are just some simple datatypes that can be imported elsewhere. This module exists to avoid circular imports."""

from clr import System

from .utils import csharp_namedtuple, get_wrapper_class, wrap_python_method


Padding = csharp_namedtuple('Padding', 'Left Top Right Bottom')
Point = csharp_namedtuple('Point', 'X Y')
Size = csharp_namedtuple('Size', 'Width Height')
Rectangle = csharp_namedtuple('Rectangle', 'Location Size')


class EventHandler(get_wrapper_class(System.EventHandler)):
    """
    This is so we can wrap methods that are being added to the event handler,
        to handle conversions between arguments and return types.

    Also we allow for a list/set/tuple of callables to be added, instead of only callables themselves.
    """
    def __iadd__(self, other):
        if callable(other):
            other = wrap_python_method(other)
        elif isinstance(other, (list, set, tuple)):
            # We've been given a list of handlers...
            cur_item = self

            for handler in other:
                cur_item = cur_item.__iadd__(handler)

            return cur_item

        return get_wrapper_class(System.EventHandler)(instance=self.instance.__iadd__(other))
