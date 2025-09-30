from copy import deepcopy

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Select, Static

from ..general_widgets.custom_general_widgets import LabelledSwitch
from ..standards import global_settings_defaults, opts


class Diagnostics(Widget):
    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the Preprocessing widget.

        Parameters
        ----------
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        # To overriding the default settings is done only when loading from a spec file. To do this, this attribute needs
        # firstly to be redefined and then the widget recomposed as is done in the working_directory widget.
        _global_settings_defaults = deepcopy(global_settings_defaults)

        # self.default_settings = {"run_reconall": False, "slice_timing": False,
        # "via_algorithm_switch": False, "dummy_scans": 0}

    def compose(self) -> ComposeResult:
        debuggroup_settings_panel = Container(
            LabelledSwitch("Debug", False, id="debug_switch"),
            LabelledSwitch("Verbose", False, id="verbose_switch"),
            LabelledSwitch("Watchdog", False, id="watchdog_switch"),
            Horizontal(
                Static("Choose which intermediate files to keep", id="keep_label"),
                Select(
                    [("some", "some"), ("all", "all"), ("none", "none")],
                    value="some",
                    allow_blank=False,
                    id="keep_selection",
                ),
                id="keep_selection_panel",
            ),
            id="debuggroup_settings",
            classes="components",
        )
        debuggroup_settings_panel.border_title = "Diagnostic options"

        yield debuggroup_settings_panel

    @on(Select.Changed, "#keep_selection")
    def on_keep_selection_changed(self, message: Message):
        opts["keep"] = message.value

    @on(LabelledSwitch.Changed, "#debug_switch")
    def on_debug_switch_changed(self, message: Message):
        if message.value:
            opts["debug"] = True
        else:
            opts["debug"] = False

    @on(LabelledSwitch.Changed, "#watchdog_switch")
    def on_watchdog_switch_changed(self, message: Message):
        if message.value:
            opts["watchdog"] = True
        else:
            opts["watchdog"] = False

    @on(LabelledSwitch.Changed, "#verbose_switch")
    def on_verbose_switch_changed(self, message: Message):
        if message.value:
            opts["verbose"] = True
        else:
            opts["verbose"] = False
