# -*- coding: utf-8 -*-

from PIL import Image
from rich.console import Console, RenderResult
from rich_pixels import Pixels
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Click
from textual.reactive import Reactive, reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, Placeholder, TabbedContent, TabPane
from textual.widgets._header import HeaderTitle

from .data_input.base import DataInput
from .feature_widgets.base import FeatureSelection
from .preprocessing.base import Preprocessing
from .run.base import RunCLX
from .utils.confirm_screen import Confirm
from .working_directory.base import WorkDirectory


class HeaderCloseIcon(Widget):
    """Display an 'icon' on the left of the header."""

    DEFAULT_CSS = """
    HeaderCloseIcon {
        dock: right;
        padding: 0 1;
        width: 8;
        content-align: left middle;
    }

    HeaderCloseIcon:hover {
        background: $foreground 10%;
    }
    """

    icon = Reactive("❌")
    """The character to use as the icon within the header."""

    async def on_click(self, event: Click) -> None:
        """Launch the command palette when icon is clicked."""
        event.stop()

        def quit(modal_value):
            if modal_value:
                exit()
            else:
                pass

        await self.app.push_screen(
            Confirm(
                "Do you really want to quit?",
                left_button_text="YES",
                right_button_text="NO",
                left_button_variant="error",
                right_button_variant="success",
                title="Quit?",
                id="quit_modal",
                classes="confirm_warning",
            ),
            quit,
        )

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon


class HeaderHelpIcon(Widget):
    """Display an 'icon' on the left of the header."""

    DEFAULT_CSS = """
    HeaderHelpIcon {
        dock: right;
        padding: 0 1;
        width: 8;
        content-align: left middle;
        offset-x: -3;
    }

    HeaderHelpIcon:hover {
        background: $foreground 10%;
    }
    """
    """The character to use as the icon within the header."""
    icon = Reactive("❓")
    help_string = "Here should be some general help :) Or maybe link to manual?"

    async def on_click(self, event: Click) -> None:
        """Launch the command palette when icon is clicked."""
        event.stop()
        await self.app.push_screen(
            Confirm(
                self.help_string,
                left_button_text=False,
                right_button_text="OK",
                right_button_variant="default",
                title="Help",
                id="help_modal",
                #   classes="confirm_warning",
            )
        )

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon


class MyHeader(Header):
    def compose(self):
        yield HeaderTitle()
        yield HeaderHelpIcon()
        yield HeaderCloseIcon()


class RichImage:
    """Convert the image to a Rich image."""

    def __rich_console__(self, console: Console, options) -> RenderResult:
        with Image.open("./halfpipe/tui/images/halfpipe_logo_v2.png") as image:
            pixels = Pixels.from_image(image, resize=(110, 92))  # 105, 92
        return console.render(pixels)


class ImageContainer(Container):
    """Create a container for the image."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def render(self):
        return RichImage()

    def key_escape(self):
        self.dismiss(False)


class Welcome(ModalScreen):
    """Intro screen with an intro image."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield ImageContainer(id="welcome_image")

    def key_escape(self):
        self.dismiss(True)

    def on_click(self, event: events.Click) -> None:
        self.dismiss(True)


class MainApp(App):
    CSS_PATH = [
        "tcss/base.tcss",
        "./feature_widgets/tcss/base.tcss",
        "./feature_widgets/tcss/taskbased.tcss",
        "./feature_widgets/tcss/model_conditions_and_contrasts.tcss",
        #  "./utils/tcss/file_browser.tcss",
        "./utils/tcss/file_browser.tcss",
        "./working_directory/tcss/working_directory.tcss",
        "./data_input/tcss/data_input.tcss",
        "./preprocessing/tcss/preprocessing.tcss",
        "./utils/tcss/path_pattern_builder.tcss",
        "./general_settings/tcss/general_settings.tcss",
        "./dev.tcss",
        "./utils/tcss/radio_set_changed.tcss",
    ]

    # TODO: The non active tabs should not show the bindings.
    BINDINGS = [
        ("w", "show_tab('work_dir_tab')", "Working directory"),
        ("i", "show_tab('input_data_tab')", "Input data"),
        ("f", "show_tab('feature_selection_tab')", "Features"),
        ("p", "show_tab('preprocessing_tab')", "General preprocessing settings"),
        ("g", "show_tab('models_tab')", "Group level models"),
        ("r", "show_tab('run_tab')", "Check and run"),
    ]

    BINDINGS = BINDINGS + [("d", "toggle_dark", "Toggle dark mode")]

    # maybe rename to available_tasks? this is a top level class variable that contains available tasks.
    available_images: dict = {}
    # if both flags are True, then we show the hidden tabs.
    flags_to_show_tabs: reactive[dict] = reactive({"from_working_dir_tab": False, "from_input_data_tab": False})
    # flag for bids/non bids data input
    is_bids = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """Compose app with tabbed content."""
        yield MyHeader(id="header")
        with TabbedContent(id="tabs_manager"):
            with TabPane("Working directory", id="work_dir_tab", classes="tabs"):
                yield VerticalScroll(WorkDirectory(id="work_dir_content"))
            with TabPane("Input data", id="input_data_tab", classes="tabs"):
                yield VerticalScroll(DataInput(id="input_data_content"))
            with TabPane("General preprocessing settings", id="preprocessing_tab", classes="tabs"):
                yield VerticalScroll(Preprocessing(id="preprocessing_content"))
            with TabPane("Features", id="feature_selection_tab", classes="tabs2 -hidden"):
                yield VerticalScroll(FeatureSelection(id="feature_selection_content"))
            with TabPane("Group level models", id="models_tab", classes="tabs"):
                yield VerticalScroll(Placeholder(), id="models_content")
            with TabPane("Check and run", id="run_tab", classes="tabs"):
                yield VerticalScroll(RunCLX(), id="run_content")
        yield Footer()

    def on_mount(self):
        # hide these tabs until we have data input and the working folder
        self.get_widget_by_id("tabs_manager").hide_tab("preprocessing_tab")
        self.get_widget_by_id("tabs_manager").hide_tab("feature_selection_tab")
        self.get_widget_by_id("tabs_manager").hide_tab("models_tab")

        self.title = "ENIGMA HALFpipe"
        self.sub_title = "development version"
        self.push_screen(Welcome(id="welcome_screen"))

    def show_hidden_tabs(self):
        # show hidden tabs, when we have working and data folder, now for development just one of these is sufficient
        if sum(self.flags_to_show_tabs.values()) >= 1:
            print("wwwwwwwwwwwwwwwwwwwwwwhere is the self here????", self.app.walk_children())
            # self.get_widget_by_id("tabs_manager").show_tab("preprocessing_tab")
            # self.get_widget_by_id("tabs_manager").show_tab("feature_selection_tab")
            # self.get_widget_by_id("tabs_manager").show_tab("models_tab")

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark: bool = not self.dark
