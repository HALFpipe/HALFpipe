# -*- coding: utf-8 -*-
import sys
from collections import defaultdict
from typing import Any

from PIL import Image
from rich.console import Console, RenderResult
from rich_pixels import Pixels
from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.reactive import Reactive, reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Placeholder, Static, TabbedContent, TabPane
from textual.widgets._header import HeaderTitle

from .data_input.base import DataInput
from .feature_widgets.base import FeatureSelection
from .general_settings.base import GeneralSettings
from .preprocessed_image_output.base import PreprocessedImageOutput
from .preprocessing.base import Preprocessing
from .run.base import RunCLX
from .utils.confirm_screen import Confirm
from .utils.context import Context
from .utils.draggable_modal_screen import DraggableModalScreen
from .working_directory.base import WorkDirectory


class HelpModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Help"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("Some help", id="question"),
                # Input(''),
                Horizontal(Button("Ok", id="ok")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(False)


class QuitModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Quit"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("Do you really want to quit?", id="question"),
                # Input(''),
                Horizontal(Button("Yes", id="ok"), Button("No", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        sys.exit()

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)


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
        await self.app.push_screen(QuitModal())

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon


class IsLockedModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Locked"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("This tab is disabled", id="locked_tab"),
                # Input(''),
                Horizontal(Button("Dismiss", id="ok"), Button("UNLOCK 🔓", id="unlock")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(False)

    @on(Button.Pressed, "#unlock")
    def _on_unlock_button_pressed(self):
        self.dismiss(True)


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

    icon = Reactive("❓")
    """The character to use as the icon within the header."""

    async def on_click(self, event: Click) -> None:
        """Launch the command palette when icon is clicked."""
        event.stop()
        await self.app.push_screen(HelpModal())

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
    def __rich_console__(self, console: Console, options) -> RenderResult:
        with Image.open("./halfpipe/tui/images/halfpipe_logo_v2.png") as image:
            pixels = Pixels.from_image(image, resize=(110, 92))  # 105, 92
        return console.render(pixels)


class ImageContainer(Container):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def render(self):
        return RichImage()

    def key_escape(self):
        self.dismiss(False)


class Welcome(ModalScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield ImageContainer(id="welcome_image")

    def key_escape(self):
        self.dismiss(True)

    def on_click(self, event: events.Click) -> None:
        self.dismiss(True)


class MainApp(App):
    """An example of tabbed content."""

    CSS_PATH = [
        "tcss/base.tcss",
        "./feature_widgets/tcss/base.tcss",
        "./feature_widgets/task_based/tcss/taskbased.tcss",
        "./feature_widgets/task_based/tcss/model_conditions_and_contrasts.tcss",
        #  "./utils/tcss/file_browser.tcss",
        "./utils/tcss/file_browser.tcss",
        "./working_directory/tcss/working_directory.tcss",
        "./data_input/tcss/data_input.tcss",
        "./preprocessing/tcss/preprocessing.tcss",
        "./utils/tcss/path_pattern_builder.tcss",
        "./general_settings/tcss/general_settings.tcss",
        "./dev.tcss",
    ]

    BINDINGS = [
        ("w", "show_tab('work_dir')", "Working directory"),
        ("i", "show_tab('input_data')", "Input data"),
        ("e", "show_tab('features')", "Features"),
        ("m", "show_tab('misc')", "Misc"),
        ("o", "show_tab('output')", "Output"),
        ("r", "show_tab('paul')", "Run"),
    ]
    BINDINGS = BINDINGS + [("d", "toggle_dark", "Toggle dark mode")]

    ctx = Context()
    available_images: dict = {}
    user_selections_dict: defaultdict[str, defaultdict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    flags_to_show_tabs: reactive[dict] = reactive({"from_working_dir_tab": False, "from_input_data_tab": False})
    # input_data_load_is_success = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # this whole "welcome_is_dismissed" mechanism is only to circumvent somehow the fact that the widgets are not yet
        # loaded and the app is already trying to access some of them via @on(TabbedContent.TabActivated)
        # ideally this should be solved with async and await but for some reason that has other issues
        self.welcome_is_dismissed = False

    def compose(self) -> ComposeResult:
        """Compose app with tabbed content."""
        yield MyHeader(id="header")
        with TabbedContent(id="tabs_manager"):
            with TabPane("Working directory", id="work_dir_tab", classes="tabs"):
                yield VerticalScroll(WorkDirectory(self, self.ctx, self.user_selections_dict, id="work_dir_content"))
            with TabPane("Input data", id="input_data_tab", classes="tabs"):
                yield VerticalScroll(DataInput(self, self.ctx, self.available_images, id="input_data_content"))
            with TabPane("General settings", id="misc_tab", classes="tabs"):
                yield VerticalScroll(GeneralSettings(), id="misc_content")
            with TabPane("General preprocessing settings", id="preprocessing_tab", classes="tabs"):
                yield VerticalScroll(Preprocessing(id="preprocessing_content"))
            with TabPane("Features", id="feature_selection_tab", classes="tabs2 -hidden"):
                yield VerticalScroll(
                    FeatureSelection(
                        self, self.ctx, self.available_images, self.user_selections_dict, id="feature_selection_content"
                    )
                )
            with TabPane("Output pre-processed image", id="preprocessed_output_tab", classes="tabs2"):
                yield VerticalScroll(
                    PreprocessedImageOutput(
                        self, self.ctx, self.available_images, self.user_selections_dict, id="preprocessed_output_content"
                    )
                )
            with TabPane("Models", id="models_tab", classes="tabs"):
                yield VerticalScroll(Placeholder(), id="models_content")
            with TabPane("Check and run", id="run_tab", classes="tabs"):
                yield VerticalScroll(RunCLX(self, self.ctx, self.user_selections_dict), id="run_content")
        yield Footer()

    def on_mount(self):
        def welcome_dismissed(message):
            self.get_widget_by_id("tabs_manager").hide_tab("preprocessing_tab")
            self.get_widget_by_id("tabs_manager").hide_tab("feature_selection_tab")
            self.get_widget_by_id("tabs_manager").hide_tab("preprocessed_output_tab")
            self.get_widget_by_id("tabs_manager").hide_tab("models_tab")

        #       self.welcome_is_dismissed = message

        self.title = "ENIGMA HALFpipe"
        self.sub_title = "development version"
        self.push_screen(Welcome(id="welcome_screen"), welcome_dismissed)
        # self.get_widget_by_id('tabs_manager')

    def show_hidden_tabs(self):
        if sum(self.flags_to_show_tabs.values()) == 1:
            self.get_widget_by_id("tabs_manager").show_tab("preprocessing_tab")
            self.get_widget_by_id("tabs_manager").show_tab("feature_selection_tab")
            self.get_widget_by_id("tabs_manager").show_tab("preprocessed_output_tab")
            self.get_widget_by_id("tabs_manager").show_tab("models_tab")
            #       self.input_data_load_is_success = True
            self.get_widget_by_id("preprocessing_content").check_meta_data(key="slice_encoding_direction")
            self.get_widget_by_id("preprocessing_content").check_meta_data(key="slice_timing")

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark: bool = not self.dark

    def on_work_directory_changed(self, message):
        """When a path to a directory with existing json file is selected, the Context object and available images
        are fed via the input_data_content widget.
        """
        if message.value:
            self.get_widget_by_id("input_data_content").feed_contex_and_extract_available_images(
                self.user_selections_dict["files"]["path"]
            )
            self.get_widget_by_id("input_data_content").manually_change_label(self.user_selections_dict["files"]["path"])
            for name in self.user_selections_dict:
                # Need to avoid key 'files' in the dictionary, since this only key is not a feature.
                if name != "files":
                    self.get_widget_by_id("feature_selection_content").add_new_feature(
                        [self.user_selections_dict[name]["features"]["type"], name]
                    )

    def update_tab_pane_label(self, tab_id):
        this_tab_pane = self.get_widget_by_id(tab_id)
        this_tab_pane.update(this_tab_pane.render_str("🔓") + this_tab_pane.label[1:])

    # @on(TabbedContent.TabActivated)
    def on_tab_clicked(self, message):
        def enable_tab(unlock_tab):
            print("uuuuuuuuuuuuuuuuuuuuuuuu", unlock_tab)
            if unlock_tab:
                this_tab_content.disabled = False
                self.update_tab_pane_label(tab_id)

        #      this_tab_content.styles.opacity = '100%'
        #  this_tab_pane.update(this_tab_pane.render_str('🔓')+this_tab_pane_current_label[1:])

        if self.welcome_is_dismissed:
            tab_id = message.tab.id
            tab_content_id = tab_id[14:-3] + "content"
            this_tab_content = self.get_widget_by_id(tab_content_id)

            if this_tab_content.disabled:
                self.push_screen(
                    Confirm(
                        "This tab is currently locked due to missing inputs in the Working and Data input tabs. However, \
you can force to unlock it. How to proceed?",
                        left_button_text="UNLOCK🔓",
                        right_button_text="Dismiss",
                        left_button_variant="error",
                        right_button_variant="success",
                        title="Tab lock warning",
                        id="confirm_unlocking",
                        classes="confirm_warning",
                    ),
                    enable_tab,
                )


# if __name__ == "__main__":
# app = TabbedApp()
# app.run()
