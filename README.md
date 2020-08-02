# expanded-pythonnet
While Pythonnet is powerful, this library hopes to serve as an intermediary to provide 3 key features

1. More types should be converted such as System.DateTime to datetime, or System.Drawing.Point to a namedtuple.
2. Pythonic names should work, ie, fore_color or ForeColor both should work.
3. Type conversion can be helped along. For instance, setting `.text = 0` would normally raise an error, 
    but now we would convert 0 to "0".

To use these features, simply wrap a class from pythonnet using get_wrapper_class

```python
Form = expanded_pythonnet.get_wrapper_class(System.Windows.Forms.Form)
```

All attribute values, return types, or anything else involving the wrapped Form will all be wrapped in 
    expanded_pythonnet wrappers going forward.