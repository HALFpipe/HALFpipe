# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Static, Switch

from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.meta_data_steps import CheckBoldSliceEncodingDirectionStep


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

    def next(self, result):
        # detect_str = "Detect non-steady-state via algorithm"
        if self.result is not None:
            value = next(iter(self.result.values()))
            if isinstance(value, (int, float)):
                ctx.spec.global_settings["dummy_scans"] = int(value)
            elif value == self.detect_str:
                ctx.spec.global_settings["dummy_scans"] = None
            else:
                raise ValueError(f'Unknown dummy_scans value "{value}"')


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
            Container(
                Horizontal(
                    Static("Turn on slice timing", classes="description_labels"),
                    TextSwitch(value=False, id="time_slicing_switch"),
                ),
                Static("", id="slice_timming_info"),
                id="slice_timing",
                classes="components",
            ),
            Vertical(
                Horizontal(
                    Static("Detect non-steady-state via algorithm", classes="description_labels"),
                    TextSwitch(False, id="via_algorithm_switch"),
                ),
                Horizontal(
                    Static(
                        "Remove initial volumes from scans",
                        id="manualy_set_volumes_to_remove_label",
                        classes="description_labels",
                    ),
                    Static("0", id="remove_volumes_value"),
                    Button("🖌", id="edit_button", classes="icon_buttons"),
                    id="manualy_set_volumes_to_remove",
                ),
                id="remove_initial_volumes",
                classes="components",
            ),
            id="anatomical_settings",
            classes="components",
        )
        yield Container(
            Horizontal(
                Static("Run recon all", classes="description_labels"),
                TextSwitch(value=False, id="run_recon_all"),
            ),
            id="functional_settings",
            classes="components",
        )

    def on_mount(self) -> None:
        self.get_widget_by_id("slice_timing").border_title = "Slice timing"
        self.get_widget_by_id("anatomical_settings").border_title = "Anatomical settings"
        self.get_widget_by_id("functional_settings").border_title = "Functional settings"
        self.get_widget_by_id("remove_initial_volumes").border_title = "Initial volumes removal"
        #  self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "hidden"
        #  self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "hidden"
        self.get_widget_by_id("slice_timming_info").styles.visibility = "hidden"
        self.get_widget_by_id("slice_timing").styles.height = "5"

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

    @on(Switch.Changed, "#run_recon_all")
    def on_run_recon_all_switch_changed(self, event):
        ctx.spec.global_settings["run_reconall"] = event.value

    @on(Switch.Changed, "#time_slicing_switch")
    async def on_time_slicing_switch_changed(self, message):
        if message.value is True:
            self.get_widget_by_id("slice_timming_info").styles.visibility = "visible"
            self.get_widget_by_id("slice_timing").styles.height = "auto"

            ctx.spec.global_settings["slice_timing"] = True

            meta_step_instance = CheckBoldSliceEncodingDirectionStep(
                self.app, callback=self.callback_func
            )  # , next_step_type=next_step_instance)
            #   SubSimpleTestClass()
            meta_step_instance.run()

        else:
            ctx.spec.global_settings["slice_timing"] = False
            self.get_widget_by_id("slice_timming_info").styles.visibility = "hidden"
            self.get_widget_by_id("slice_timing").styles.height = "5"

    def callback_func(self, message_dict):
        print("qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq", message_dict)
        info_string = ""
        for key in message_dict:
            info_string += key + ": " + " ".join(message_dict[key]) + "\n"

        self.get_widget_by_id("slice_timming_info").update(info_string)

    # slice_direction_widget = self.get_widget_by_id("select_slice_direction")
    # if value:
    # slice_direction_widget.value = "Inferior to superior"
    # slice_direction_widget.styles.background = "50% green"

    # if message.value:
    # self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "visible"
    # self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "visible"
    # self.get_widget_by_id("slice_timing").styles.height = "auto"
    # self.app.push_screen(
    # SliceTimingModal(found_values_message=self.slice_encoding_direction_message), _update_slicing_direction
    # )
    # else:
    # self.get_widget_by_id("select_slice_timing_panel").styles.visibility = "hidden"
    # self.get_widget_by_id("select_slice_direction_panel").styles.visibility = "hidden"
    # self.get_widget_by_id("slice_timing").styles.height = "5"

    # @on(Select.Changed)
    # def on_select_changed(self, event):
    # select_widget = event.control
    # if event.value != select_widget.BLANK:
    # select_widget.styles.background = "50% green"
    # if "Import from file" in event.value:
    # self.app.push_screen(FileBrowserModal(), self._add_slice_timing_from_file)
    # else:
    # select_widget.styles.background = "40% red"

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
