# -*- coding: utf-8 -*-

from copy import deepcopy
from pathlib import Path

from rich.console import RenderResult

# from rich_pixels import Pixels
from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Click
from textual.reactive import Reactive, reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual.widgets._header import HeaderTitle

from ..logging.base import LoggingContext
from .data_analyzers.context import ctx
from .data_input.base import DataInput
from .diagnostics.base import Diagnostics
from .features.base import FeatureSelection
from .group_level_models.base import GroupLevelModelSelection
from .preprocessing.base import Preprocessing
from .run.base import Run
from .specialized_widgets.confirm_screen import Confirm
from .specialized_widgets.event_file_widget import FilePanelTemplate
from .specialized_widgets.filebrowser import FileBrowser
from .specialized_widgets.quit_modal import quit_modal
from .standards import global_settings_defaults
from .working_directory.base import WorkDirectory

# The BASE_DIR is here because of some relative path files of the tcss files when running the pytest.
BASE_DIR = Path(__file__).resolve().parent


class HeaderCloseIcon(Widget):
    """
    A widget to display a close icon in the header.

    This widget provides a clickable close icon (❌) in the header of the
    application. Clicking this icon prompts the user to confirm whether
    they want to quit the application.

    Attributes
    ----------
    icon : Reactive[str]
        The character to use as the icon within the header.
    """

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

    icon = Reactive("EXIT❌")
    """The character to use as the icon within the header."""

    async def on_click(self, event: Click) -> None:
        """
        Handles the click event on the close icon.

        This method is called when the user clicks the close icon. It
        displays a confirmation modal asking the user if they really want
        to quit the application.

        Parameters
        ----------
        event : Click
            The click event object.
        """
        event.stop()
        await quit_modal(self)

    def render(self) -> RenderResult:
        """
        Renders the close icon.

        Returns
        -------
        RenderResult
            The rendered icon.
        """
        return self.icon


class HeaderHelpIcon(Widget):
    """
    A widget to display a help icon in the header.

    This widget provides a clickable help icon (❓) in the header of the
    application. Clicking this icon displays a help message to the user.

    Attributes
    ----------
    icon : Reactive[str]
        The character to use as the icon within the header.
    help_string : str
        The help message to display when the icon is clicked.
    """

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

    # The character to use as the icon within the header.
    icon = Reactive("HELP❓")
    help_string = "Here should be some general help :) Or maybe link to manual?"

    async def on_click(self, event: Click) -> None:
        """
        Handles the click event on the help icon.

        This method is called when the user clicks the help icon. It
        displays a help message in a confirmation modal.

        Parameters
        ----------
        event : Click
            The click event object.
        """
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


class HeaderSaveIcon(Widget):
    """
    A widget to display a close icon in the header.

    This widget provides a clickable close icon (❌) in the header of the
    application. Clicking this icon prompts the user to confirm whether
    they want to quit the application.

    Attributes
    ----------
    icon : Reactive[str]
        The character to use as the icon within the header.
    """

    DEFAULT_CSS = """
    HeaderSaveIcon {
        dock: right;
        padding: 0 1;
        width: 8;
        content-align: left middle;
    }

    HeaderSaveIcon:hover {
        background: $foreground 10%;
    }
    """

    icon = Reactive("SAVE💾")
    """The character to use as the icon within the header."""

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon

    async def on_click(self, event: Click) -> None:
        """
        Handles the click event on the close icon.

        This method is called when the user clicks the close icon. It
        displays a confirmation modal asking the user if they really want
        to quit the application.

        Parameters
        ----------
        event : Click
            The click event object.
        """
        event.stop()
        self.app.get_widget_by_id("run").on_save_button_pressed()


class MyHeader(Header):
    """
    A custom header widget for the application.

    This header includes a title, a help icon, and a close icon.
    """

    def compose(self):
        yield HeaderTitle()
        yield HeaderSaveIcon(id="save_button")
        yield HeaderHelpIcon()
        yield HeaderCloseIcon()


class RichImage:
    """
    Convert the image to a Rich image.

    This class is currently not used, but it was intended to display an
    image using the Rich library.
    """

    # def __rich_console__(self, console: Console, options) -> RenderResult:
    #     with Image.open(os.path.join(BASE_DIR, "images/halfpipe_logo_v2.png")) as image:
    #         pixels = Pixels.from_image(image, resize=(110, 92))  # 105, 92
    #     return console.render(pixels)


class ImageContainer(Container):
    """
    A container for displaying an image.

    This container is currently not used, but it was intended to hold the
    image displayed in the `Welcome` modal.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def render(self):
        return RichImage()

    def key_escape(self):
        self.dismiss(False)


class Welcome(ModalScreen):
    """
    An introductory modal screen with an image.

    This modal screen displays an image to welcome the user. It is
    currently not used.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """
        Composes the modal with its child widgets.

        Returns
        -------
        ComposeResult
            The result of composing the modal.
        """
        yield ImageContainer(id="welcome_image")

    def key_escape(self):
        """
        Handles the Escape key press event.

        This method is called when the user presses the Escape key. It
        dismisses the modal.
        """
        self.dismiss(True)

    def on_click(self, event: events.Click) -> None:
        """
        Handles the click event.

        This method is called when the user clicks anywhere on the modal.
        It dismisses the modal.

        Parameters
        ----------
        event : events.Click
            The click event object.
        """
        self.dismiss(True)


class MainApp(App):
    """
    The main application class for the HALFpipe TUI.

    This class sets up the main application window, including the header,
    footer, tabbed content, and various widgets for different parts of the
    application.

    Attributes
    ----------
    CSS_PATH : list[Path]
        A list of paths to the CSS files used by the application.
    BINDINGS : list[tuple[str, str, str]]
        A list of key bindings for the application.
    available_images : dict
        A dictionary to store available images (tasks).
    flags_to_show_tabs : reactive[dict]
        A reactive dictionary to control the visibility of tabs.
    is_bids : bool
        A flag indicating whether BIDS format is used.
    """

    CSS_PATH = [
        BASE_DIR / "tcss/base.tcss",
        BASE_DIR / "tcss/general.tcss",
        BASE_DIR / "features/tcss/base.tcss",
        BASE_DIR / "features/tcss/taskbased.tcss",
        BASE_DIR / "features/utils/tcss/model_conditions_and_contrasts.tcss",
        BASE_DIR / "group_level_models/tcss/base.tcss",
        BASE_DIR / "group_level_models/tcss/models.tcss",
        BASE_DIR / "group_level_models/tcss/group_level_model_selection_modal.tcss",
        BASE_DIR / "working_directory/tcss/working_directory.tcss",
        BASE_DIR / "data_input/tcss/data_input.tcss",
        BASE_DIR / "preprocessing/tcss/preprocessing.tcss",
        BASE_DIR / "run/tcss/run.tcss",
        BASE_DIR / "specialized_widgets/tcss/file_browser.tcss",
        BASE_DIR / "specialized_widgets/tcss/path_pattern_builder.tcss",
        BASE_DIR / "general_widgets/tcss/radio_set_changed.tcss",
        BASE_DIR / "diagnostics/tcss/diagnostics.tcss",
    ]

    # TODO: The non active tabs should not show the bindings.
    BINDINGS = [
        ("w", "show_tab('work_dir_tab')", "Working directory"),
        ("i", "show_tab('input_data_tab')", "Input data"),
        ("f", "show_tab('feature_selection_tab')", "Features"),
        ("p", "show_tab('preprocessing_tab')", "General preprocessing settings"),
        ("g", "show_tab('models_tab')", "Group level models"),
        ("r", "show_tab('run_tab')", "Check and run"),
        ("ctrl+c", "action_quit", "Quit"),
        # ("x", "reload", "reload"),
        # ("c", "ctx", "ctx"),
    ]

    # maybe rename to available_tasks? this is a top level class variable that contains available tasks.
    available_images: dict = {}
    # if both flags are True, then we show the hidden tabs.
    flags_to_show_tabs: reactive[dict] = reactive(
        {"from_working_dir_tab": False, "from_input_data_tab": False, "fs_license_file_found": False}
    )
    # flag for bids/non bids data input
    is_bids = True

    def __init__(self, **kwargs) -> None:
        """
        Initializes the MainApp.

        This constructor disables print logging and calls the base class
        constructor.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments passed to the base class constructor.
        """
        LoggingContext.disable_print()
        super().__init__(**kwargs)
        self._global_settings_defaults = deepcopy(global_settings_defaults)
        self.tab_manager = TabbedContent(id="tab_manager")
        self.tabs_are_visible = False

    def compose(self) -> ComposeResult:
        """
        Composes the main application layout.

        This method sets up the main layout of the application, including
        the header, tabbed content, and footer.

        Returns
        -------
        ComposeResult
            The result of composing the application layout.
        """
        yield MyHeader(id="header")
        with self.tab_manager:
            with TabPane("Working directory", id="work_dir_tab", classes="tabs"):
                yield VerticalScroll(WorkDirectory(id="work_dir_content"))
            with TabPane("Input data", id="input_data_tab", classes="tabs"):
                yield VerticalScroll(DataInput(id="input_data_content"))
            with TabPane("General preprocessing settings", id="preprocessing_tab", classes="tabs"):
                yield VerticalScroll(Preprocessing(id="preprocessing_content"))
            with TabPane("Features", id="feature_selection_tab", classes="tabs2 -hidden"):
                yield VerticalScroll(FeatureSelection(id="feature_selection_content"))
            with TabPane("Group level models", id="models_tab", classes="tabs2 -hidden"):
                yield VerticalScroll(GroupLevelModelSelection(id="models_content"))
            with TabPane("Check and run", id="run_tab", classes="tabs"):
                yield VerticalScroll(Run(id="run"), id="run_content")
            with TabPane("Diagnostics", id="diag_tab", classes="tabs"):
                yield VerticalScroll(Diagnostics(), id="diag_content")
        yield Footer()

    @on(TabbedContent.TabActivated, pane="#run_tab")
    def on_run_tab_activated(self) -> None:
        self.get_widget_by_id("run").refresh_context()

    def on_mount(self) -> None:
        """
        Handles actions to be taken when the application is mounted.

        This method is called when the application is mounted. It hides
        some tabs initially and sets the application title and subtitle.
        """
        # hide these tabs until we have data input and the working folder
        self.tab_manager.hide_tab("preprocessing_tab")
        self.tab_manager.hide_tab("feature_selection_tab")
        self.tab_manager.hide_tab("models_tab")

        self.title = "ENIGMA HALFpipe"
        self.sub_title = "development version"
        # self.push_screen(Welcome(id="welcome_screen"))

    def show_hidden_tabs(self) -> None:
        """
        Shows hidden tabs based on flags.

        This method shows the hidden tabs ("preprocessing_tab",
        "feature_selection_tab", "models_tab") when both flags in
        `flags_to_show_tabs` are True.
        """
        # show hidden tabs, when we have working and data folder, now for development just one of these is sufficient
        tab_manager = self.tab_manager
        if sum(self.flags_to_show_tabs.values()) == 2 and not self.tabs_are_visible:
            tab_manager.show_tab("preprocessing_tab")
            tab_manager.show_tab("feature_selection_tab")
            tab_manager.show_tab("models_tab")
            tab_manager.get_widget_by_id("work_dir_tab").styles.opacity = 0.7
            tab_manager.get_widget_by_id("input_data_tab").styles.opacity = 0.7
            tab_manager.get_widget_by_id("work_dir_tab").query_one(FileBrowser).read_only_mode(True)
            tab_manager.get_widget_by_id("input_data_content").read_only_mode(True)
            self.app.push_screen(
                Confirm(
                    "All set successfully! Proceed to the next tabs:\n\n\
➡️  General preprocessing settings ⬅️\n\
➡️             Features            ⬅️\n\
➡️        Group level models       ⬅️\n\
➡️           Check and run         ⬅️\n\
The working tab and data tab are now read only! Do not change entries here!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Input successful",
                    classes="confirm_success",
                )
            )
            self.tabs_are_visible = True

    def hide_tabs(self) -> None:
        """
        Hides the preprocessing, feature selection, and models tabs.
        """
        self.tab_manager.hide_tab("preprocessing_tab")
        self.tab_manager.hide_tab("feature_selection_tab")
        self.tab_manager.hide_tab("models_tab")

    def action_show_tab(self, tab: str) -> None:
        """
        Switches to a new tab.

        Parameters
        ----------
        tab : str
            The ID of the tab to switch to.
        """
        self.get_child_by_type(TabbedContent).active = tab

    def action_toggle_dark(self) -> None:
        """
        Toggles dark mode.
        """
        self.dark: bool = not self.dark

    def action_reload(self):
        """
        Reloads the UI.

        This method calls `reload_ui` to refresh the UI.
        """
        self.reload_ui()

    def reload_ui(self, complete_reset=True) -> None:
        """
        Reloads the UI, optionally resetting the context.

        This method refreshes the UI by recomposing and laying out the
        feature selection, models, and preprocessing widgets. If
        `complete_reset` is True, it also resets the input data and
        working directory widgets, and clears the context cache.

        Parameters
        ----------
        complete_reset : bool, optional
            Whether to perform a complete reset of the context, by
            default True.
        """
        self.get_widget_by_id("input_data_content").refresh(recompose=True, layout=True)
        self.get_widget_by_id("feature_selection_content").refresh(recompose=True, layout=True)
        self.get_widget_by_id("models_content").refresh(recompose=True, layout=True)
        self.get_widget_by_id("preprocessing_content").refresh(recompose=True, layout=True)
        self.flags_to_show_tabs["from_working_dir_tab"] = False
        self.flags_to_show_tabs["from_input_data_tab"] = False
        self.tab_manager.hide_tab("preprocessing_tab")
        self.tab_manager.hide_tab("feature_selection_tab")
        self.tab_manager.hide_tab("models_tab")

        if complete_reset is True:
            self.get_widget_by_id("input_data_content").refresh(recompose=True, layout=True)
            self.get_widget_by_id("work_dir_content").refresh(recompose=True, layout=True)

        feature_selection_content = self.app.get_widget_by_id("feature_selection_tab").get_widget_by_id(
            "feature_selection_content"
        )
        feature_selection_content.feature_items.clear()
        model_selection_content = self.app.get_widget_by_id("models_tab").get_widget_by_id("models_content")
        model_selection_content.feature_items.clear()

        ctx.database.filepaths_by_tags.clear()
        ctx.database.tags_by_filepaths.clear()
        ctx.spec.features.clear()
        ctx.spec.settings.clear()
        ctx.spec.models.clear()
        ctx.spec.files.clear()
        ctx.cache.clear()
        ctx.available_images = {}
        FilePanelTemplate.reset_all_counters()

        # # set global settings to defaults use the defaults dictionary at preprocessing_content widget
        # for key in self.get_widget_by_id("preprocessing_content").default_settings:
        #     ctx.spec.global_settings[key] = self.get_widget_by_id("preprocessing_content").default_settings[key]
        ctx.spec.global_settings["dummy_scans"] = self._global_settings_defaults["dummy_scans"]
        ctx.spec.global_settings["run_reconall"] = self._global_settings_defaults["run_reconall"]
        ctx.spec.global_settings["slice_timing"] = self._global_settings_defaults["slice_timing"]

    async def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            await quit_modal(self)
        elif event.key == "ctrl+s":
            self.app.save_screenshot()
