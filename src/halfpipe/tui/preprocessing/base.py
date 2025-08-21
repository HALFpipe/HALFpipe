# -*- coding: utf-8 -*-

from copy import deepcopy

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static, Switch

from ...model.file.base import File
from ..data_analyzers.context import ctx
from ..data_analyzers.meta_data_steps import CheckBoldSliceEncodingDirectionStep
from ..general_widgets.custom_general_widgets import LabelledSwitch, SwitchWithInputBox
from ..general_widgets.custom_switch import TextSwitch
from ..help_functions import widget_exists
from ..standards import global_settings_defaults


class Preprocessing(Widget):
    """
    A widget for configuring preprocessing settings.

    This widget provides a user interface for configuring various
    preprocessing steps, including anatomical and functional settings. Moreover,
    an advanced settings are available if needed.

    Attributes
    ----------
    default_settings : dict[str, Any]
        Default settings for preprocessing operations.

    Methods
    -------
    __init__(id, classes)
        Initializes the Preprocessing widget.
    compose() -> ComposeResult
        Composes the widget's components.
    _on_advanced_settings_switch_switch_changed(message)
        Handles changes in the advanced settings switch.
    _on_via_algorithm_switch_changed(message)
        Handles changes in the "Detect non-steady-state via algorithm" switch.
    on_run_reconall_switch_changed(message)
        Handles changes in the "Run recon all" switch.
    on_time_slicing_switch_changed(message)
        Handles changes in the "Turn on slice timing" switch.
    callback_func(message_dict)
        Callback function to handle messages from the FilePattern or
        CheckMetaData classes.
    _add_slice_timing_from_file(path)
        Adds slice timing information from a file (currently a TODO).
    _on_edit_vols_to_remove_button_pressed()
        Handles the "Edit" button press for setting initial volumes to remove.
    """

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

        ctx.spec.global_settings.setdefault(_global_settings_defaults["dummy_scans"])
        ctx.spec.global_settings.setdefault(_global_settings_defaults["run_reconall"])
        ctx.spec.global_settings.setdefault(_global_settings_defaults["slice_timing"])

        # self.default_settings = {"run_reconall": False, "slice_timing": False,
        # "via_algorithm_switch": False, "dummy_scans": 0}

    def compose(self) -> ComposeResult:
        """
        Composes the widget's components.

        This method defines the layout and components of the widget,
        including anatomical settings, functional settings, advanced
        settings, and debug settings.

        Yields
        ------
        ComposeResult
            The composed widgets.
        """
        # Widgets for settings that go to the json files
        anatomical_settings_panel = Container(
            Horizontal(
                Static("Run FreeSurfer Recon-all", classes="description_labels"),
                TextSwitch(value=ctx.spec.global_settings["run_reconall"], id="run_reconall"),
                id="run_reconall_panel",
            ),
            id="anatomical_settings",
            classes="components",
        )
        slice_timming_info_panel = Static("", id="slice_timming_info")
        slice_timing_panel = Container(
            Horizontal(
                Static("Turn on slice timing", classes="description_labels"),
                TextSwitch(value=ctx.spec.global_settings["slice_timing"], id="time_slicing_switch"),
            ),
            slice_timming_info_panel,
            id="slice_timing",
            classes="components",
        )
        remove_initial_volumes_panel = Vertical(
            Horizontal(
                Static("Detect non-steady-state via algorithm", classes="description_labels"),
                TextSwitch(False if ctx.spec.global_settings["dummy_scans"] is not None else True, id="via_algorithm_switch"),
            ),
            Grid(
                Static(
                    "Remove initial volumes from scans",
                    id="manualy_set_volumes_to_remove_label",
                    classes="description_labels",
                ),
                Input(
                    value=str(ctx.spec.global_settings["dummy_scans"]),
                    placeholder="value",
                    id="number_of_remove_initial_volumes",
                ),
                # Static(str(self.default_settings["dummy_scans"]), id="remove_volumes_value"),
                # Button("🖌", id="edit_vols_to_remove_button", classes="icon_buttons"),
                id="manualy_set_volumes_to_remove",
            ),
            id="remove_initial_volumes",
            classes="components",
        )
        functional_settings_panel = Container(
            slice_timing_panel,
            remove_initial_volumes_panel,
            id="functional_settings",
            classes="components",
        )
        # Advanced setting widgets switch
        advanced_settings_switch_panel = Container(
            Horizontal(
                Static("Advanced settings", classes="description_labels"),
                TextSwitch(value=False, id="advanced_settings_switch"),
            ),
            id="advanced_settings_switch_panel",
            classes="components",
        )

        # The titles and the other styling settings need to be set in the compose because on load from a spec file
        # the settings from the spec file are passed as the default_settings variable and the whole widget needs to be
        # recomposed. When recomposing, the titles and etc. are deleted and can be newly added when they are defined
        # only in the compose function.
        functional_settings_panel.border_title = "Functional settings"
        anatomical_settings_panel.border_title = "Anatomical settings"
        slice_timing_panel.border_title = "Slice timing"
        slice_timing_panel.styles.height = "5"
        remove_initial_volumes_panel.border_title = "Initial volumes removal"
        slice_timming_info_panel.styles.visibility = "hidden"

        advanced_settings_switch_panel.border_title = "Advanced settings"

        # workflowgroup_settings_panel.styles.visibility = "hidden"
        # debuggroup_settings_panel.styles.visibility = "hidden"
        # rungroup_settings_panel.styles.visibility = "hidden"

        yield anatomical_settings_panel
        yield functional_settings_panel
        yield advanced_settings_switch_panel
        # yield workflowgroup_settings_panel
        # yield debuggroup_settings_panel
        # yield rungroup_settings_panel

    def build_advanced_settings_widgets(self):
        # Advanced setting widgets for halfpipe settings

        self.rungroup_settings_panel = Container(
            SwitchWithInputBox(
                label="Merge subject workflows to n chunks",
                value="",
                switch_value=False,
                classes="switch_with_input_box",
                id="n-chunks",
            ),
            SwitchWithInputBox(
                label="Max chunk size",
                value="64",
                classes="switch_with_input_box",
                id="max-chunks",
            ),
            LabelledSwitch("Subject chunks", False),
            SwitchWithInputBox(
                label="Select which chunk to run",
                value="",
                switch_value=False,
                classes="switch_with_input_box",
                id="only-chunk-index",
            ),
            SwitchWithInputBox(
                label="Nipype memory in GB",
                value="64",
                classes="switch_with_input_box",
                id="nipype-memory-gb",
            ),
            SwitchWithInputBox(
                label="Nipype number of processes",
                value="",
                switch_value=False,
                classes="switch_with_input_box",
                id="num-threads",
            ),
            SwitchWithInputBox(
                label="Nipype run plugin",
                value="MultiProc",
                classes="switch_with_input_box",
                id="nipype-run-plugin",
            ),
            id="rungroup_settings",
            classes="components",
        )
        self.rungroup_settings_panel.border_title = "Run settings"

    @on(Switch.Changed, "#advanced_settings_switch")
    async def _on_advanced_settings_switch_switch_changed(self, message):
        """
        Handles changes in the advanced settings switch.

        This method is called when the state of the advanced settings
        switch changes. It shows or hides the advanced settings panels
        based on the switch state.

        Parameters
        ----------
        message : Switch.Changed
            The message object containing information about the switch
            state change.
        """

        if message.value:
            # self.get_widget_by_id("workflowgroup_settings").styles.visibility = "visible"
            # self.get_widget_by_id("debuggroup_settings").styles.visibility = "visible"
            # self.get_widget_by_id("rungroup_settings").styles.visibility = "visible"
            self.build_advanced_settings_widgets()
            await self.mount(self.rungroup_settings_panel)
        else:
            if widget_exists(self, "workflowgroup_settings") is True:
                await self.get_widget_by_id("workflowgroup_settings").remove()
            if widget_exists(self, "debuggroup_settings") is True:
                await self.get_widget_by_id("debuggroup_settings").remove()
            if widget_exists(self, "rungroup_settings") is True:
                await self.get_widget_by_id("rungroup_settings").remove()
            # self.get_widget_by_id("workflowgroup_settings").styles.visibility = "hidden"
            # self.get_widget_by_id("debuggroup_settings").styles.visibility = "hidden"
            # self.get_widget_by_id("rungroup_settings").styles.visibility = "hidden"

    @on(Switch.Changed, "#via_algorithm_switch")
    def _on_via_algorithm_switch_changed(self, message):
        """
        Handles changes in the "Detect non-steady-state via algorithm" switch.

        This method is called when the state of the "Detect non-steady-state
        via algorithm" switch changes. It updates the UI and the
        application's context based on the switch state. For manual option,
        an input modal is raised.

        Parameters
        ----------
        message : Switch.Changed
            The message object containing information about the switch
            state change.
        """
        if message.value:
            self.get_widget_by_id("manualy_set_volumes_to_remove_label").update(
                "Turn of 'Detect non-steady-state via algorithm' to set manually number of initial volumes to remove"
            )
            self.get_widget_by_id("number_of_remove_initial_volumes").styles.visibility = "hidden"
            ctx.spec.global_settings["dummy_scans"] = None
        else:
            self.get_widget_by_id("manualy_set_volumes_to_remove_label").update("Remove initial volumes from scans")
            self.get_widget_by_id("number_of_remove_initial_volumes").styles.visibility = "visible"
            # raise imedietely the modal
            # self._on_edit_vols_to_remove_button_pressed()

    @on(Switch.Changed, "#run_reconall")
    def on_run_reconall_switch_changed(self, message: Message):
        """
        Handles changes in the "Turn on slice timing" switch.

        This method is called when the state of the "Turn on slice timing"
        switch changes. It updates the UI and the application's context
        based on the switch state. It also runs the
        `CheckBoldSliceEncodingDirectionStep` to gather metadata.

        Parameters
        ----------

        message : Switch.Changed
            The message object containing information about the switch
            state change.
        """
        ctx.spec.global_settings["run_reconall"] = message.value

    @work(exclusive=True, name="time_slicing_worker")
    @on(Switch.Changed, "#time_slicing_switch")
    async def on_time_slicing_switch_changed(self, message: Message):
        if message.value is True:
            self.get_widget_by_id("slice_timming_info").styles.visibility = "visible"
            self.get_widget_by_id("slice_timing").styles.height = "auto"

            ctx.spec.global_settings["slice_timing"] = True
            meta_step_instance = CheckBoldSliceEncodingDirectionStep(self.app, callback=self.callback_func)
            await meta_step_instance.run()
        else:
            ctx.spec.global_settings["slice_timing"] = False
            self.get_widget_by_id("slice_timming_info").styles.visibility = "hidden"
            self.get_widget_by_id("slice_timing").styles.height = "5"

            # need to delete in from all the bold filebojs
            for widget_id, the_dict in ctx.cache.items():
                # should always be there
                if "files" in the_dict:
                    if isinstance(the_dict["files"], File):
                        is_ok = True
                        if the_dict["files"].datatype != "func":
                            is_ok = False
                        if the_dict["files"].suffix != "bold":
                            is_ok = False
                        if is_ok:
                            # add dict if it does not exist
                            ctx.cache[widget_id]["files"].metadata.pop("slice_timing_code", None)
                            ctx.cache[widget_id]["files"].metadata.pop("slice_encoding_direction", None)

    def callback_func(self, message_dict: dict):
        """
        The callback function is passed to the FilePattern or CheckMetaData classes where they gather all of the messages
        so that the user can view them again.

        Parameters
        ----------
        message_dict : dict
            Dictionary containing key-value pairs where keys are strings
            and values are lists of strings. This dictionary is used to
            generate a formatted string with the key and concatenated
            values for each entry.
        """
        info_string = ""
        for key in message_dict:
            info_string += key + ": " + " ".join(message_dict[key]) + "\n"

        self.get_widget_by_id("slice_timming_info").update(info_string)

    def _add_slice_timing_from_file(self, path: str):
        """
        Adds slice timing information from a file (currently a TODO).

        This method is intended to allow users to specify slice timing
        information from a file, but it is currently not implemented.

        Parameters
        ----------
        path : str
            The path to the file containing slice timing information.
        """
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

    @on(Input.Changed, "#number_of_remove_initial_volumes")
    def _on_number_of_remove_initial_volumes_changed(self, message: Message) -> None:
        ctx.spec.global_settings["dummy_scans"] = message.value
