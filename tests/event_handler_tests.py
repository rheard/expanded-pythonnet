from threading import Thread
from time import sleep

from clr import System

from .utils import ExpandedTestCase, Form, Button


class ButtonHandlerForm(Form):
    """A form with a button that counts the number of times it has been clicked."""

    def __init__(self):
        super(ButtonHandlerForm, self).__init__()
        self.initialize_components()

    def create_button(self):
        self.button1 = Button(
            location=(12, 12),
            name="button1",
            size=(75, 23),
            tab_index=0,
            text=0,
            use_visual_style_back_color=True,
        )
        self.button1.click += self.button1_click

    def initialize_components(self):
        self.suspend_layout()
        #
        # button1
        #
        self.create_button()
        #
        # Form1
        #
        self.auto_scale_dimensions = (6, 13)
        self.auto_scale_mode = System.Windows.Forms.AutoScaleMode.Font
        self.client_size = (99, 47)
        self.controls.add(self.button1)
        self.name = 'Form1'
        self.text = "Form1"
        self.resume_layout(False)

    def button1_click(self, sender, e):
        sender.text = int(sender.text) + 1
        sender.update()


class ButtonInitHandlerForm(ButtonHandlerForm):
    """Similar to ButtonHandlerForm, but the handler is initialized using the Button's __init__"""

    def create_button(self):
        self.button1 = Button(
            location=(12, 12),
            name="button1",
            size=(75, 23),
            tab_index=0,
            text=0,
            use_visual_style_back_color=True,
            click=self.button1_click,
        )


class ButtonMultiHandlerForm(ButtonHandlerForm):
    """Similar to ButtonHandlerForm, but there are 2 handlers added at once"""

    def create_button(self):
        self.button1 = Button(
            location=(12, 12),
            name="button1",
            size=(75, 23),
            tab_index=0,
            text=0,
            use_visual_style_back_color=True,
        )
        self.button1.click += [self.button1_click, self.button1_click2]

    def initialize_components(self):
        super(ButtonMultiHandlerForm, self).initialize_components()
        self.text = 0
        self.update()

    def button1_click2(self, sender, e):
        self.text = int(self.text) + 1
        self.update()


class ButtonInitMultiHandlerForm(ButtonMultiHandlerForm):
    """Similar to ButtonMultiHandlerForm, but the handlers are added via the __init__"""

    def create_button(self):
        self.button1 = Button(
            location=(12, 12),
            name="button1",
            size=(75, 23),
            tab_index=0,
            text=0,
            use_visual_style_back_color=True,
            click=[self.button1_click, self.button1_click2],
        )


class ButtonClickEventHandlerTest(ExpandedTestCase):
    """Spawns the ButtonHandlerForm with a basic button event handler, and tests it"""

    @classmethod
    def setUpClass(cls):
        cls.form = ButtonHandlerForm()

    def setUp(self):
        self.thread = Thread(target=lambda: System.Windows.Forms.Application.Run(self.form.instance))
        self.thread.start()
        sleep(0.5)

    def tearDown(self):
        self.form.close()

    def test_handler(self):
        """Test that a basic event handler works"""
        for i in range(20):
            self.assertEqual(str(i), self.form.button1.text)
            self.form.button1.perform_click()


class ButtonClickInitEventHandlerTest(ButtonClickEventHandlerTest):
    """Spawns the ButtonInitHandlerForm with a basic button event handler, and tests it"""

    @classmethod
    def setUpClass(cls):
        cls.form = ButtonInitHandlerForm()

    def test_handler(self):
        """Test that a basic event handler works through the __init__"""
        super(ButtonClickInitEventHandlerTest, self).test_handler()


class ButtonClickMultiEventHandlerTest(ButtonClickEventHandlerTest):
    """Spawns the ButtonMultiHandlerForm with multiple button event handlers, and tests it"""

    @classmethod
    def setUpClass(cls):
        cls.form = ButtonMultiHandlerForm()

    def test_handler(self):
        """Test that multiple event handlers work"""
        for i in range(20):
            self.assertAllEqual(str(i), self.form.button1.text, self.form.text)
            self.form.button1.perform_click()


class ButtonClickInitMultiEventHandlerTest(ButtonClickMultiEventHandlerTest):
    """
    Spawns the ButtonInitMultiHandlerForm with multiple button event handlers add through the __init__, and tests it
    """

    @classmethod
    def setUpClass(cls):
        cls.form = ButtonInitMultiHandlerForm()

    def test_handler(self):
        """Test that multiple event handlers work through the __init__"""
        super(ButtonClickInitMultiEventHandlerTest, self).test_handler()
