from copy import deepcopy

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget

from ..general_widgets.custom_general_widgets import LabelledSwitch, SwitchWithSelect
from ..standards import global_settings_defaults


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
            LabelledSwitch("Debug", False),
            LabelledSwitch("Profile", False),
            LabelledSwitch("Watchdog", False),
            SwitchWithSelect(
                "Choose which intermediate files to keep",
                options=[("all", "all"), ("some", "some"), ("none", "none")],
                switch_value=True,
                id="keep",
            ),
            id="debuggroup_settings",
            classes="components",
        )

        yield debuggroup_settings_panel
