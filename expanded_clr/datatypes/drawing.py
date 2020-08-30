from ..utils import csharp_namedtuple

Point = csharp_namedtuple('Point', 'X Y')
Size = csharp_namedtuple('Size', 'Width Height')
Rectangle = csharp_namedtuple('Rectangle', 'Location Size')
