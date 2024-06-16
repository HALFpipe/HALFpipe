# -*- coding: utf-8 -*-


import numpy as np
from halfpipe.tui.utils.file_browser_modal import FileBrowserModal
from inflection import humanize
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Select, Static, Switch

from ...ingest.metadata.direction import direction_code_str
from ...ingest.metadata.slicetiming import slice_timing_str
from ...model.file.func import BoldFileSchema
from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.false_input_warning_screen import FalseInputWarning


class SetInitialVolumesRemovalModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Remove initial volumes"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("Set number of how many initial volumes to remove"),
                Input(""),
                Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss("0")
        else:
            self.dismiss(input_widget.value)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)


class SliceTimingModal(DraggableModalScreen):
    def __init__(self, found_values_message="No foundings???", **kwargs):
        super().__init__(**kwargs)
        self.found_values_message = found_values_message
        self.title_bar.title = "Check slice acquisition direction values"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static(self.found_values_message, id="found_values"),
                Static("Proceed with these values?", id="question"),
                # Input(''),
                Horizontal(Button("Yes", id="ok"), Button("No", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)


class Preprocessing(Widget):
    def __init__(self, disabled=False, **kwargs) -> None:
        super().__init__(**kwargs, disabled=disabled)
        # self.ctx = self.app.ctx
        self.time_slicing_options = [
            "Sequential increasing (1, 2, ...)",
            "Sequential decreasing (... 2, 1)",
            "Alternating increasing even first (2, 4, ... 1, 3, ...)",
            "Alternating increasing odd first (1, 3, ... 2, 4, ...)",
            "Alternating decreasing even first (... 3, 1, ... 4, 2)",
            "Alternating decreasing odd first (... 4, 2, ... 3, 1)",
            "                 ***Import from file***",
        ]
        self.slice_acquisition_direction = ["Inferior to superior", "Superior to inferior"]
        self.slice_timing_message = ""

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Static("Turn on slice timing", classes="description_labels"),
                TextSwitch(value=False, id="time_slicing_switch"),
            ),
            Horizontal(
                Static("Slice timing", classes="label"),
                Select([(str(value), value) for value in self.time_slicing_options], id="select_slice_timing"),
                id="select_slice_timing_panel",
                classes="timing_setting_panels",
            ),
            Horizontal(
                Static("Slice direction", classes="label"),
                Select([(str(value), value) for value in self.slice_acquisition_direction], id="select_slice_direction"),
                id="select_slice_direction_panel",
                classes="timing_setting_panels",
            ),
            id="slice_timing",
            classes="components",
        )
        yield Vertical(
            Horizontal(
                Static("Detect non-steady-state via algorithm", classes="description_labels"),
                TextSwitch(False, id="via_algorithm_switch"),
            ),
            Horizontal(
                Static(
                    "Remove initial volumes from scans", id="manualy_set_volumes_to_remove_label", classes="description_labels"
                ),
                Static("0", id="remove_volumes_value"),
                Button("🖌", id="edit_button", classes="icon_buttons"),
                id="manualy_set_volumes_to_remove",
            ),
            id="remove_initial_volumes",
            classes="components",
        )

    def on_mount(self) -> None:
        self.get_widget_by_id("slice_timing").border_title = "Slice timing"
        self.get_widget_by_id("remove_initial_volumes").border_title = "Initial volumes removal"
        self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "hidden"
        self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "hidden"
        self.get_widget_by_id("slice_timing").styles.height = "5"

    def check_meta_data(self, key="slice_encoding_direction") -> None:
        #  self.key = "slice_encoding_direction"
        self.key = key
        self._append_view = []
        # ctx = self.ctx
        self.schema = BoldFileSchema
        self.show_summary = True

        def _get_unit(schema, key):
            field = _get_field(schema, key)
            if field is not None:
                return field.metadata.get("unit")

        def _get_field(schema, key):
            if isinstance(schema, type):
                instance = schema()
            else:
                instance = schema
            if "metadata" in instance.fields:
                return _get_field(instance.fields["metadata"].nested, key)
            return instance.fields.get(key)

        def display_str(x):
            if x == "MNI152NLin6Asym":
                return "MNI ICBM 152 non-linear 6th Generation Asymmetric (FSL)"
            elif x == "MNI152NLin2009cAsym":
                return "MNI ICBM 2009c Nonlinear Asymmetric"
            elif x == "slice_encoding_direction":
                return "slice acquisition direction"
            return humanize(x)

        filedict = {"datatype": "func", "suffix": "bold"}

        self.filters = filedict
        self.appendstr = ""

        humankey = display_str(self.key).lower()

        if self.filters is None:
            filepaths = [fileobj.path for fileobj in ctx.database.fromspecfileobj(ctx.spec.files[-1])]
        else:
            filepaths = [*ctx.database.get(**self.filters)]

        ctx.database.fillmetadata(self.key, filepaths)

        vals = [ctx.database.metadata(filepath, self.key) for filepath in filepaths]
        self.suggestion = None

        if self.key in ["phase_encoding_direction", "slice_encoding_direction"]:
            for i, val in enumerate(vals):
                if val is not None:
                    vals[i] = direction_code_str(val, filepaths[i])

        elif self.key == "slice_timing":
            for i, val in enumerate(vals):
                if val is not None:
                    sts = slice_timing_str(val)
                    if "unknown" in sts:
                        val = np.array(val)
                        sts = np.array2string(val, max_line_width=256)
                        if len(sts) > 128:
                            sts = f"{sts[:128]}..."
                    else:
                        sts = humanize(sts)
                    vals[i] = sts

        if any(val is None for val in vals):
            self.is_missing = True

            if self.show_summary is True:
                print(f"Missing {humankey} values")

            vals = [val if val is not None else "missing" for val in vals]
        else:
            self.is_missing = False
            print(f"Check {humankey} values{self.appendstr}")
        ##########################
        uniquevals, counts = np.unique(vals, return_counts=True)
        order = np.argsort(counts)

        column1 = []
        for i in range(min(10, len(order))):
            column1.append(f"{counts[i]} images")
        column1width = max(len(s) for s in column1)

        unit = _get_unit(self.schema, self.key)
        if unit is None:
            unit = ""

        if self.key == "slice_timing":
            unit = ""

        if self.show_summary is True:
            for i in range(min(10, len(order))):
                display = display_str(f"{uniquevals[i]}")
                if self.suggestion is None:
                    self.suggestion = display
                tablerow = f" {column1[i]:>{column1width}} - {display}"
                if uniquevals[i] != "missing":
                    tablerow = f"{tablerow} {unit}"
                self._append_view.append((tablerow))

            if len(order) > 10:
                self._append_view.append(("..."))

        print(self._append_view)
        if self.key in ["phase_encoding_direction", "slice_encoding_direction"]:
            self.slice_encoding_direction_message = " ".join(self._append_view)
        if self.key == "slice_timing":
            self.slice_timing_message = " ".join(self._append_view)

    @on(Switch.Changed, "#via_algorithm_switch")
    def _on_via_algorithm_switch_changed(self, message):
        if message.value:
            self.get_widget_by_id("manualy_set_volumes_to_remove_label").update(
                "Turn of 'Detect non-steady-state via algorithm' to set manually number of initial volumes to remove"
            )
            self.get_widget_by_id("edit_button").styles.visibility = "hidden"
            self.get_widget_by_id("remove_volumes_value").styles.visibility = "hidden"
        else:
            self.get_widget_by_id("manualy_set_volumes_to_remove_label").update("Remove initial volumes from scans")
            self.get_widget_by_id("edit_button").styles.visibility = "visible"
            self.get_widget_by_id("remove_volumes_value").styles.visibility = "visible"

    @on(Switch.Changed, "#time_slicing_switch")
    def on_time_slicing_switch_changed(self, message):
        def _update_slicing_direction(value):
            if self.slice_timing_message != "":
                self.app.push_screen(
                    FalseInputWarning(
                        warning_message="Missing slice timing values" + self.slice_timing_message,
                        title="Missing values!",
                        id="missing_time_slice_vals_warn_modal",
                        classes="error_modal",
                    )
                )

            slice_direction_widget = self.get_widget_by_id("select_slice_direction")
            if value:
                slice_direction_widget.value = "Inferior to superior"
                slice_direction_widget.styles.background = "50% green"

        if message.value:
            self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "visible"
            self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "visible"
            self.get_widget_by_id("slice_timing").styles.height = "auto"
            self.app.push_screen(
                SliceTimingModal(found_values_message=self.slice_encoding_direction_message), _update_slicing_direction
            )
        else:
            self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "hidden"
            self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "hidden"
            self.get_widget_by_id("slice_timing").styles.height = "5"

    @on(Select.Changed)
    def on_select_changed(self, event):
        select_widget = event.control
        if event.value != select_widget.BLANK:
            select_widget.styles.background = "50% green"
            if "Import from file" in event.value:
                self.app.push_screen(FileBrowserModal(), self._add_slice_timing_from_file)
        else:
            select_widget.styles.background = "40% red"

    def _add_slice_timing_from_file(self, path):
        select_widget = self.get_widget_by_id("select_slice_timing")
        if path is not None:
            self.time_slicing_options.insert(-1, path)
            select_widget.set_options([(str(value), value) for value in self.time_slicing_options])
            select_widget.value = path
            select_widget.styles.background = "50% green"
            pass
        else:
            select_widget.value = select_widget.BLANK
            select_widget.styles.background = "40% red"

    @on(Button.Pressed, "#edit_button")
    def _on_edit_button_pressed(self):
        self.app.push_screen(SetInitialVolumesRemovalModal(), self.update_remove_initial_volumes_value)

    def update_remove_initial_volumes_value(self, value):
        remove_volumes_value_widget = self.get_widget_by_id("remove_volumes_value")
        if value is not None:
            remove_volumes_value_widget.update(value)
            remove_volumes_value_widget.styles.border = ("solid", "green")
