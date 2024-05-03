# -*- coding: utf-8 -*-
from collections import defaultdict
from typing import Any

from PIL import Image
from rich.console import Console, RenderResult
from rich_pixels import Pixels
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .data_input.base import DataInput
from .feature_widgets.base import FeatureSelection
from .general_settings.base import GeneralSettings
from .preprocessed_image_output.base import PreprocessedImageOutput
from .preprocessing.base import Preprocessing
from .run.base import RunCLX
from .utils.context import Context
from .working_directory.base import WorkDirectory


class RichImage:
    def __rich_console__(self, console: Console, options) -> RenderResult:
        with Image.open("./halfpipe/tui/images/bulbasaur.png") as image:
            pixels = Pixels.from_image(image)
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
        self.dismiss(False)

    def on_click(self, event: events.Click) -> None:
        self.dismiss(False)


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

    def compose(self) -> ComposeResult:
        """Compose app with tabbed content."""
        yield Header(id="header")
        with TabbedContent(initial="work_dir_tab"):
            with TabPane("Working directory", id="work_dir_tab"):
                yield VerticalScroll(WorkDirectory(self, self.ctx, self.user_selections_dict, id="work_dir_content"))
            with TabPane("Input data", id="input_data_tab"):
                yield VerticalScroll(DataInput(self, self.ctx, self.available_images, id="input_data_content"))
            with TabPane("General preprocessing settings", id="preprocessing_tab"):
                yield VerticalScroll(Preprocessing(self.ctx, id="preprocessing_content"))
            with TabPane("Features", id="feature_selection_tab"):
                yield VerticalScroll(
                    FeatureSelection(
                        self, self.ctx, self.available_images, self.user_selections_dict, id="feature_selection_content"
                    )
                )
            with TabPane("General settings", id="misc_tab"):
                yield VerticalScroll(GeneralSettings())
            with TabPane("Output pre-processed image", id="output_tab"):
                yield VerticalScroll(
                    PreprocessedImageOutput(
                        self, self.ctx, self.available_images, self.user_selections_dict, id="preprocessed_output_content"
                    )
                )
            with TabPane("Check and run", id="run_tab"):
                yield VerticalScroll(RunCLX(self, self.ctx, self.user_selections_dict))
        yield Footer()

    def on_mount(self):
        self.title = "ENIGMA HALFpipe"
        self.sub_title = "development version"
        self.push_screen(Welcome(id="welcome_screen"))

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


# if __name__ == "__main__":
# app = TabbedApp()
# app.run()
