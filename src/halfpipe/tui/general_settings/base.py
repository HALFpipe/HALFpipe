# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Union

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Select, Static, Switch

from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen


def can_convert_to_float(value):
    # Regex to match numbers including integers, floats, exponentials, and special floats
    float_regex = r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$|^nan$|^inf$|^-inf$"
    return bool(re.match(float_regex, value, re.IGNORECASE))


class ValueSetterModal(DraggableModalScreen):
    def __init__(self, title="", message="Set the new value", **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = title
        self.message = message

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static(self.message),
                Input(""),
                Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss(None)
        else:
            self.dismiss(input_widget.value)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)


class HelpModal(DraggableModalScreen):
    def __init__(self, message="XXX", **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Help"
        self.message = message

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static(self.message),
                Horizontal(
                    Button("OK", id="ok"),
                ),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(None)


class LabelledSwitch(Widget):
    def __init__(self, label, value, help_message="Explain the functionality", id=None):
        super().__init__(id=id)
        self.label = label
        self.value = value
        self.help_message = help_message

    def compose(self) -> ComposeResult:
        yield Horizontal(
            #   Button("❓", id="help_button", classes="icon_buttons"),
            Static(self.label),
            TextSwitch(self.value),
        )

    def update_value(self, value):
        self.query_one(Switch).value = value

    @on(Button.Pressed, "#help_button")
    def _on_help_button_pressed(self):
        self.app.push_screen(HelpModal(self.help_message))

    @on(Switch.Changed)
    def _on_select(self, event):
        self.post_message(self.Changed(event.value, self))

    @dataclass
    class Changed(Message):
        """Inform ancestor the selection was changed."""

        value: str
        labelled_switch: LabelledSwitch

        @property
        def control(self) -> LabelledSwitch:
            """The Select that sent the message."""
            return self.labelled_switch


class ChangeableStatic(Widget):
    def __init__(
        self, label, value, title="Set value", message="Set the new value", help_message="Explain the functionality", id=None
    ):
        super().__init__(id=id)
        self.label = label
        self.value = value
        self.title = title
        self.message = message
        self.help_message = help_message

    def compose(self) -> ComposeResult:
        yield Horizontal(
            #  Button("❓", id="help_button", classes="icon_buttons"),
            Static(self.label),
            Static(self.value, id="value_holder"),
            Button("🖌", id="edit_button", classes="icon_buttons"),
        )

    def update_value(self, value):
        self.get_widget_by_id("value_holder").update(value)

    @on(Button.Pressed, "#edit_button")
    def _on_edit_button_pressed(self):
        def update_value(value):
            if value is not None:
                self.get_widget_by_id("value_holder").update(value)
                self.post_message(self.Changed(value, self))

        self.app.push_screen(ValueSetterModal(self.title, self.message), update_value)

    @on(Button.Pressed, "#help_button")
    def _on_help_button_pressed(self):
        self.app.push_screen(HelpModal(self.help_message))

    @dataclass
    class Changed(Message):
        """Inform ancestor the selection was changed."""

        value: str
        changeable_static: ChangeableStatic

        @property
        def control(self) -> ChangeableStatic:
            """The Select that sent the message."""
            return self.changeable_static


class StaticAndSelection(Widget):
    def __init__(self, label, options: list | None = None, help_message="Explain the functionality", id=None):
        super().__init__(id=id)
        self.label = label
        self.options = [] if options is None else options
        self.help_message = help_message
        self.value = self.options[0]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            #         Button("❓", id="help_button", classes="icon_buttons"),
            Static(self.label),
            Select([(str(value), value) for value in self.options], value=self.options[0], allow_blank=False),
        )

    def update_value(self, value):
        self.query_one(Select).value = value

    @on(Button.Pressed, "#help_button")
    def _on_help_button_pressed(self):
        self.app.push_screen(HelpModal(self.help_message))

    @on(Select.Changed)
    def _on_select(self, event):
        self.post_message(self.Changed(event.value, self))

    @dataclass
    class Changed(Message):
        """Inform ancestor the selection was changed."""

        value: str
        static_and_selection: StaticAndSelection

        @property
        def control(self) -> StaticAndSelection:
            """The Select that sent the message."""
            return self.static_and_selection


# ctx.spec.global_settings
class GeneralSettings(Widget):
    def __init__(self):
        super().__init__()
        self.global_settings: Dict[str, Dict[str, Union[str, bool, List[str]]]] = {
            "dummy_scans": {"label": "Dummy scans", "value": "0"},
            "slice_timing": {"label": "Slice timing", "value": False},
            "use_bbr": {"label": "Use BBR", "value": ["null"]},
            "skull_strip_algorithm": {"label": "Skull stripping algorithm", "value": ["ants"]},
            "run_mriqc": {"label": "Run MRIQC", "value": False},
            "run_fmriprep": {"label": "Run fmriprep", "value": True},
            "run_halfpipe": {"label": "Run halfpipe", "value": True},
            "fd_thres": {"label": "FD Threshold", "value": "0.5"},
            "anat_only": {"label": "Anatomy Only", "value": False},
            "write_graph": {"label": "Write Graph", "value": False},
            "hires": {"label": "High Resolution", "value": False},
            "run_reconall": {"label": "Run Recon-All", "value": False},
            "t2s_coreg": {"label": "T2* Coregistration", "value": False},
            "medial_surface_nan": {"label": "Medial Surface NaN", "value": False},
            "bold2t1w_dof": {"label": "BOLD to T1w DOF", "value": "9"},
            "fmap_bspline": {"label": "Fieldmap Bspline", "value": True},
            "force_syn": {"label": "Force SyN", "value": False},
            "longitudinal": {"label": "Longitudinal", "value": False},
            "regressors_all_comps": {"label": "Regressors All Components", "value": False},
            "regressors_dvars_th": {"label": "Regressors DVARS Threshold", "value": "1.5"},
            "regressors_fd_th": {"label": "Regressors FD Threshold", "value": "0.5"},
            "skull_strip_fixed_seed": {"label": "Skull Strip Fixed Seed", "value": False},
            "skull_strip_template": {"label": "Skull Strip Template", "value": ["OASIS30ANTs"]},
            "aroma_err_on_warn": {"label": "AROMA Error on Warning", "value": False},
            "aroma_melodic_dim": {"label": "AROMA Melodic Dimension", "value": "-200"},
            "sloppy": {"label": "Sloppy", "value": False},
        }

        self.global_settings_defaults = deepcopy(self.global_settings)

    def compose(self) -> ComposeResult:
        with Container(id="top_container", classes="components"):
            #       yield "dummy_scans": 0,
            yield Static(
                "These are general recommended settings. If you are not 100% sure what you are doing, leave them as \
they are.",
                id="description",
            )
            with Container(id="inner_container"):
                yield Horizontal(Static("Reset all values to default"), Button("reset", id="reset_button"), id="intro")
                for key in self.global_settings.keys():
                    label = self.global_settings[key]["label"]
                    value = self.global_settings[key]["value"]
                    if isinstance(value, bool):
                        yield LabelledSwitch(label, value, id=key)
                    elif isinstance(value, list):
                        yield StaticAndSelection(label, options=value, help_message="Explain the functionality", id=key)
                    elif can_convert_to_float(value):
                        yield ChangeableStatic(label, value, help_message="Explain the functionality", id=key)

    def on_mount(self):
        self.get_widget_by_id("top_container").border_title = "General settings"

    @on(ChangeableStatic.Changed)
    @on(StaticAndSelection.Changed)
    @on(LabelledSwitch.Changed)
    def _on_general_settings_changed(self, event):
        print("global_settings_defaults", self.global_settings_defaults)
        self.global_settings[event.control.id]["value"] = event.value
        print("global_settings", self.global_settings)
        self.app.ctx.spec.global_settings[event.control.id] = event.value

    @on(Button.Pressed, "#reset_button")
    def _on_reset_button_pressed(self):
        for key, setting in self.global_settings_defaults.items():
            default_value = setting["value"]
            # this exercise is needed to avoid mypy errors, otherwise it could have been much simpler
            if isinstance(default_value, list):
                value: str | bool = default_value[0]
            else:
                value = default_value
            # widget should always exists
            self.get_widget_by_id(key).update_value(value)
