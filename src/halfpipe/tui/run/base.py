# -*- coding: utf-8 -*-
# ok (more-less) to review

import copy
import json
from collections import defaultdict
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Pretty

from ..save import dump_dict_to_contex
from ...model.feature import Feature
from ...model.file.bids import BidsFileSchema
from ...model.model import Model
from ...model.setting import SettingSchema
from ...model.spec import SpecSchema, save_spec
from ...utils.copy import deepcopy
from ..data_analyzers.context import ctx
from ..specialized_widgets.confirm_screen import Confirm


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
                Button("Refresh", id="refresh_button"), Button("Save", id="save_button"), Button("Run", id="run_button")
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

