from unittest import TestCase

from clr import System

import expanded_clr


# region Wrapped test classes
Form = expanded_clr.get_wrapper_class(System.Windows.Forms.Form)
Button = expanded_clr.get_wrapper_class(System.Windows.Forms.Button)
# endregion


class ExpandedTestCase(TestCase):
    def assertAllEqual(self, *args, msg=None):
        """Modify assertEqual to allow for multiple inputs."""
        for arg1, arg2 in zip(args, args[1:]):
            self.assertEqual(arg1, arg2, msg=msg)
