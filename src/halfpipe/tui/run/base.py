# -*- coding: utf-8 -*-
# ok (more-less) to review

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Pretty
from textual.worker import Worker, WorkerState

from ...cli.run import run_stage_workflow
from ...model.spec import SpecSchema, save_spec
from ..data_analyzers.context import ctx
from ..general_widgets.draggable_modal_screen import DraggableModalScreen
from ..save import dump_dict_to_contex
from ..specialized_widgets.confirm_screen import Confirm
from ..specialized_widgets.quit_modal import quit_modal


@dataclass
class BatchOptions:
    workdir: Path | None | str = None
    use_cluster: bool = True
    nipype_omp_nthreads: int = 1
    nipype_n_procs: int = 1
    keep: list[str] = field(default_factory=lambda: ["some"])
    subject_exclude: list[str] = field(default_factory=list)
    subject_include: list[str] = field(default_factory=list)
    subject_list: str | None = None
    fs_license_file: Path | None = None
    nipype_resource_monitor: bool = False
    watchdog: bool = False
    verbose: bool = False
    fs_root: str | None = None

    def validate(self):
        valid_keep = ["all", "some", "none"]
        for val in self.keep:
            if val not in valid_keep:
                raise ValueError(f"Invalid value for keep: {val}")


class BatchOptionModal(DraggableModalScreen):
    CSS_PATH = ["./batch_option_modal.tcss"]

    def __init__(self) -> None:
        """
        Initializes the ContrastTableInputWindow instance.

        Parameters
        ----------
        table_row_index : dict[str, str]
            A dictionary representing the row index of the contrast table,
            where keys are condition names and values are their initial values.
        current_col_labels : list[str]
            A list of current column labels in the contrast table.
        """
        super().__init__()
        self.title_bar.title = "Batch script values"
        humanize_option_labels = {
            "nipype_omp_nthreads": "nipype number of threads",
            "nipype_n_procs": "nipype number of processes",
        }
        self.batch_options: dict[str, str] = {"nipype_omp_nthreads": "1", "nipype_n_procs": "1"}

        input_elements = []
        for key, value in self.batch_options.items():
            input_box = Input(
                placeholder="Value",
                value=value,
                name=key,
                classes="input_values",
            )
            label = Label(humanize_option_labels[key])
            label.tooltip = value
            input_elements.append(Horizontal(label, input_box, classes="row_element"))
        self.widgets_to_mount = [
            Label("Specify values for the batch script", id="instruction_label"),
            Vertical(*input_elements),
            Horizontal(
                Button("Ok", classes="ok_button"),
                Button("Cancel", classes="cancel_button"),
                id="button_panel",
            ),
        ]

    def on_mount(self):
        self.content.mount(*self.widgets_to_mount)

    @on(Button.Pressed, ".ok_button")
    def ok(self):
        """
        Confirms the input values and checks for column name conflicts.

        This method is called when the "Ok" button is pressed. It triggers
        the `_confirm_window`.
        """
        self._confirm_window()

    @on(Button.Pressed, ".cancel_button")
    def cancel_window(self):
        """
        Cancels the window and dismisses it without saving user input.

        This method is called when the "Cancel" button is pressed. It
        triggers the `_cancel_window` method to dismiss the modal.
        """
        self._cancel_window()

    def key_escape(self):
        """
        Cancels the window and dismisses it when the escape key is pressed.

        This method is called when the escape key is pressed. It triggers
        the `_cancel_window` method to dismiss the modal.
        """
        self._cancel_window()

    def _confirm_window(self):
        """
        Validates the user inputs and updates the table row index if inputs are valid.

        This method checks if the contrast name is unique and if all input
        values are filled. If the inputs are valid, it updates the
        `table_row_index` and dismisses the modal. Otherwise, it displays
        an error message.
        """
        if any(i.value == "" for i in self.query(".input_values")):
            self.app.push_screen(
                Confirm(
                    "Fill all values!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Missing values",
                    classes="confirm_error",
                )
            )
        else:
            for i in self.query(".input_values"):
                self.batch_options[i.name] = i.value
            self.dismiss(self.batch_options)

    def _cancel_window(self):
        """
        Dismisses the window without saving any user inputs.

        This method dismisses the modal window without making any changes.
        """
        self.dismiss(False)


class Run(Widget):
    """
    A widget for managing the dumping the cached data to create the spec.json file,
    saving it and finally run the pipeline.

    This class provides a user interface for refreshing the spec data, saving the
    configuration to a spec file, and running the pipeline. It also
    manages the conversion of cached data to the context format and gives a preview
    of the generated spec.json file.

    Attributes
    ----------
    old_cache : defaultdict[str, defaultdict[str, dict[str, Any]]] | None
        A cache of old data, structured as a defaultdict of defaultdicts
        containing dictionaries.
    json_data : str | None
        A JSON string representation of the current configuration.

    Methods
    -------
    __init__(id, classes)
        Initializes the Run widget.
    compose() -> ComposeResult
        Composes the widget's components.
    on_run_button_pressed()
        Handles the event when the "Run" button is pressed.
    on_save_button_pressed()
        Handles the event when the "Save" button is pressed.
    on_refresh_button_pressed()
        Handles the event when the "Refresh" button is pressed.
    refresh_context()
        Refreshes the context by dumping the cached data and updating the UI.
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the Run widget.

        Parameters
        ----------
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.old_cache: defaultdict[str, defaultdict[str, dict[str, Any]]] | None = None
        self.json_data = None

    def compose(self) -> ComposeResult:
        """
        Composes the widget's components.

        This method defines the layout and components of the widget,
        including the "Refresh", "Save", and "Run" buttons, and the output
        area.

        Yields
        ------
        ComposeResult
            The composed widgets.
        """
        with ScrollableContainer():
            yield Horizontal(
                Button("Refresh spec file", id="refresh_button"),
                Button("Save spec file", id="save_button"),
                Button("Generate batch script", id="generate_batch_script_button"),
                Button("Exit UI and Run", id="run_button"),
                Button("Exit UI", id="exit_button"),
            )
            yield Pretty("", id="this_output")

    @on(Button.Pressed, "#run_button")
    def on_run_button_pressed(self):
        """
        Handles the event when the "Run" button is pressed.

        This method is called when the user presses the "Run" button. It
        exits the application and returns the working directory.
        """
        self.app.exit(result=ctx.workdir)

    @on(Button.Pressed, "#save_button")
    def on_save_button_pressed(self):
        """
        Handles the event when the "Save" button is pressed.

        This method is called when the user presses the "Save" button. It
        refreshes the context, saves the spec file to the working
        directory, and success modal is raised.
        """

        def save(value):
            """
            Saves the spec file to the working directory.

            This method is called after the user confirms the save
            operation. It saves the current pipeline configuration to a
            spec file in the working directory.

            Parameters
            ----------
            value : bool
                The value returned by the confirmation dialog (not used).
            """
            save_spec(ctx.spec, workdir=ctx.workdir)

        self.refresh_context()
        self.app.push_screen(
            Confirm(
                "The spec file was saved to working directory!",
                left_button_text=False,
                right_button_text="OK",
                right_button_variant="success",
                title="Spec file saved",
                classes="confirm_success",
            ),
            save,
        )

    @on(Button.Pressed, "#generate_batch_script_button")
    def on_generate_batch_script_button_pressed(self):
        """
        Handles the event when the "Refresh" button is pressed.

        This method is called when the user presses the "Refresh" button.
        It refreshes the context and updates the UI spec preview with the new data.
        """

        def generate_batch_script(batch_option_values):
            batch_options = BatchOptions(batch_option_values)
            batch_options.workdir = ctx.workdir
            self._run_stage_workflow(batch_options)

        self.app.push_screen(BatchOptionModal(), generate_batch_script)

    @work(exclusive=True, name="run_stage_workflow_worker")
    async def _run_stage_workflow(self, batch_options):
        run_stage_workflow(batch_options)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """
        Handles state changes in the pattern matching worker.

        This method is called when the state of the `update_worker`
        changes. If the worker is successful, it updates the
        `pattern_match_results` with the callback message and posts a
        `PathPatternChanged` message.

        Parameters
        ----------
        event : Worker.StateChanged
            The event object containing information about the worker state
            change.
        """
        if event.worker.name == "run_stage_workflow_worker":
            if event.state == WorkerState.SUCCESS:
                self.app.push_screen(
                    Confirm(
                        "The batch script was saved to working directory!",
                        left_button_text=False,
                        right_button_text="OK",
                        right_button_variant="success",
                        title="Spec file saved",
                        classes="confirm_success",
                    )
                )

    @on(Button.Pressed, "#exit_button")
    async def on_exit_button_pressed(self):
        """
        Handles the event when the "Refresh" button is pressed.

        This method is called when the user presses the "Refresh" button.
        It refreshes the context and updates the UI spec preview with the new data.
        """
        await quit_modal(self)

    @on(Button.Pressed, "#refresh_button")
    def on_refresh_button_pressed(self):
        """
        Handles the event when the "Refresh" button is pressed.

        This method is called when the user presses the "Refresh" button.
        It refreshes the context and updates the UI spec preview with the new data.
        """
        self.refresh_context()

    def refresh_context(self):
        """
        Refreshes the context by dumping the cached data and updating the spec preview.

        This method dumps the cached data to the context, converts it to a
        JSON string, and updates the output widget with the JSON data.
        """
        dump_dict_to_contex(self)
        self.json_data = SpecSchema().dumps(ctx.spec, many=False, indent=4, sort_keys=False)
        if self.json_data is not None:
            self.get_widget_by_id("this_output").update(json.loads(self.json_data))
