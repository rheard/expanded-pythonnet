import expanded_clr

from clr import System

from .utils import ExpandedTestCase, Form


class BasicInterfaceTests(ExpandedTestCase):
    """Basic tests to ensure that we can correctly interface between C# and Python names and types."""

    def test_setting_csharp_attr(self):
        """Test that we can set a C# attribute, and that the Python attribute reflects the change"""
        form = Form()
        form.Text = "Testing"
        self.assertAllEqual(form.text, form.Text, "Testing")

    def test_setting_python_attr(self):
        """Test that we can set a Python attribute, and that the C# attribute reflects the change"""
        form = Form()
        form.text = "Testing"
        self.assertAllEqual(form.text, form.Text, "Testing")

    def test_setting_attr_in_init(self):
        """Test that we can use a Python attribute in the __init__"""
        form = Form(text="Testing")
        self.assertAllEqual(form.text, form.Text, "Testing")

    def test_implicit_attr_value_type_conversion(self):
        """Test that we can set an attribute using a Python type and have it converted on the fly"""
        form = Form(text=0)
        self.assertEqual(form.text, "0")


class PointConversionTests(ExpandedTestCase):
    """Tests to ensure that System.Drawing.Point is converted correctly"""

    def test_conversion(self):
        """Test that Point is converted correctly from C# to begin with"""
        form = Form()
        self.assertIsInstance(form.location, expanded_clr.datatypes.drawing.Point)

    def test_original_type(self):
        """Test that setting the original Point type works"""
        form = Form(location=System.Drawing.Point(12, 12))
        self.assertEqual(form.location, (12, 12))
        self.assertIsInstance(form.location, expanded_clr.datatypes.drawing.Point)

    def test_python_basic_type(self):
        """Test that setting the native Python tuple type works"""
        form = Form(location=(12, 12))
        self.assertEqual(form.location, (12, 12))
        self.assertIsInstance(form.location, expanded_clr.datatypes.drawing.Point)

    def test_python_type(self):
        """Test that setting the Python namedtuple type works"""
        form = Form(location=expanded_clr.datatypes.drawing.Point(12, 12))
        self.assertEqual(form.location, (12, 12))
        self.assertIsInstance(form.location, expanded_clr.datatypes.drawing.Point)


class SizeConversionTests(ExpandedTestCase):
    """Tests to ensure that System.Drawing.Size is converted correctly"""

    def test_conversion(self):
        """Test that Size is converted correctly from C# to begin with"""
        form = Form()
        self.assertIsInstance(form.size, expanded_clr.datatypes.drawing.Size)
        self.assertIsInstance(form.auto_scale_dimensions, expanded_clr.datatypes.drawing.Size)  # Test SizeF

    def test_original_type(self):
        """Test that setting the original Size type works"""
        form = Form(size=System.Drawing.Size(200, 200))
        self.assertEqual(form.size, (200, 200))
        self.assertIsInstance(form.size, expanded_clr.datatypes.drawing.Size)

    def test_python_basic_type(self):
        """Test that setting the native Python tuple type works"""
        form = Form(size=(200, 200))
        self.assertEqual(form.size, (200, 200))
        self.assertIsInstance(form.size, expanded_clr.datatypes.drawing.Size)

    def test_python_type(self):
        """Test that setting the Python namedtuple type works"""
        form = Form(size=expanded_clr.datatypes.drawing.Size(200, 200))
        self.assertEqual(form.size, (200, 200))
        self.assertIsInstance(form.size, expanded_clr.datatypes.drawing.Size)


class RectangleConversionTests(ExpandedTestCase):
    """Tests to ensure that System.Drawing.Rectangle is converted correctly"""

    def test_conversion(self):
        """Test that Rectangle is converted correctly from C# to begin with"""
        form = Form()
        self.assertIsInstance(form.desktop_bounds, expanded_clr.datatypes.drawing.Rectangle)


class PaddingConversionTests(ExpandedTestCase):
    """Tests to ensure that System.Drawing.Padding is converted correctly"""

    def test_conversion(self):
        """Test that Size is converted correctly from C# to begin with"""
        form = Form()
        self.assertIsInstance(form.margin, expanded_clr.datatypes.windows.Padding)

    def test_original_type(self):
        """Test that setting the original Size type works"""
        form = Form(margin=System.Windows.Forms.Padding(10, 11, 12, 13))
        self.assertEqual(form.margin, (10, 11, 12, 13))
        self.assertIsInstance(form.margin, expanded_clr.datatypes.windows.Padding)

    def test_python_basic_type(self):
        """Test that setting the native Python tuple type works"""
        form = Form(margin=(10, 11, 12, 13))
        self.assertEqual(form.margin, (10, 11, 12, 13))
        self.assertIsInstance(form.margin, expanded_clr.datatypes.windows.Padding)

    def test_python_type(self):
        """Test that setting the Python namedtuple type works"""
        form = Form(margin=expanded_clr.datatypes.windows.Padding(10, 11, 12, 13))
        self.assertEqual(form.margin, (10, 11, 12, 13))
        self.assertIsInstance(form.margin, expanded_clr.datatypes.windows.Padding)
