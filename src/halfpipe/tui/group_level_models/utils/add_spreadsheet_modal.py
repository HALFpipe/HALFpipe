# -*- coding: utf-8 -*-

from typing import Any, Dict

from textual import on
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Button, Static

from ....ingest.spreadsheet import read_spreadsheet
from ....model.file.spreadsheet import SpreadsheetFileSchema
from ....model.variable import VariableSchema
from ...data_analyzers.context import ctx
from ...general_widgets.draggable_modal_screen import DraggableModalScreen
from ...specialized_widgets.file_browser_modal import FileBrowserModal, path_test_with_isfile_true
from ...general_widgets.multichoice_radioset import MultipleRadioSet

aggregate_order = ["dir", "run", "ses", "task"]


class AddSpreadsheetModal(DraggableModalScreen):
    """
    SelectionModal(options=None, title="", instructions="Select", id=None, classes=None)

    Parameters
    ----------
    options : dict, optional
        A dictionary containing the options for the radio buttons,
        where keys are the option identifiers and values are the
        display text for each option. If not provided, defaults to
        {"a": "A", "b": "B"}.
    title : str, optional
        The title of the modal window, by default an empty string.
    instructions : str, optional
        Instructions or description to be displayed at the top of
        the modal window, by default "Select".
    id : str, optional
        An optional identifier for the modal window, by default None.
    classes : str, optional
        An optional string of classes for applying styles to the
        modal window, by default None.

    Attributes
    ----------
    title_bar.title : str
        Sets the title of the modal window.
    instructions : str
        Holds the instruction text for the modal window.
    widgets_to_mount : list
        A list of widgets to be mounted on the modal window, including
        title, radio buttons, and OK/Cancel buttons.
    choice : str or list
        The selected choice from the radio buttons, defaults to a
        placeholder "default_choice???todo".

    Methods
    -------
    on_mount()
        Called when the window is mounted. Mounts the content widgets.
    _on_ok_button_pressed()
        Handles the OK button press event, dismissing the modal window
        with the current choice.
    _on_cancel_button_pressed()
        Handles the Cancel button press event, dismissing the modal
        window with None value.
    _on_radio_set_changed(event)
        Handles the event when the radio button selection changes.
        Updates the choice attribute with the selected option key.
    """

    instance_count = 0

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.title_bar.title = "Path to the spreadsheet"
        self.instructions = "Select or add path of the covariates/group data spreadsheet file"
        filepaths = ctx.database.get(datatype="spreadsheet")
        self.cache_name = "__spreadsheet_file_" + str(self.instance_count)
        self.instance_count += 1
        self.filedict: dict[str, str | list] = {}
        self.metadata: list[Dict[str, Any]] = []
        self.last_selected = list(filepaths)[-1] if filepaths != set() else None

        # In some cases the user just must make some choice in the selection. In particular this is the case when one is
        # some of the Meta classes (CheckMeta...) are in action. Returning from this stage by hitting the cancel button would
        # not make sense.
        button_panel = Horizontal(
            Button("OK", id="ok"), Button("Cancel", id="cancel"), id="button_panel", classes="components"
        )

        self.widgets_to_mount = [
            ScrollableContainer(
                Container(
                    Static(self.instructions, id="title"),
                    Horizontal(
                        Button("Browse", id="browse"),
                        Static("No spreadsheet selected!", id="spreadsheet_path_label"),
                    ),
                    id="spreadsheet_path_panel",
                    classes="components",
                ),
                button_panel,
                id="top_container",
            )
        ]

    async def on_mount(self) -> None:
        """Called when the window is mounted."""
        await self.content.mount(*self.widgets_to_mount)
        self.get_widget_by_id("spreadsheet_path_panel").border_title = "Spreadsheet path"

    async def update_spreadsheet_list(self, spreadsheet_path: str | bool):
        if spreadsheet_path != "" and isinstance(spreadsheet_path, str):
            self.get_widget_by_id("spreadsheet_path_label").update(spreadsheet_path)
            self.spreadsheet_df = read_spreadsheet(spreadsheet_path)
            self.filedict = {"datatype": "spreadsheet", "path": spreadsheet_path}

            for i, col_label in enumerate(self.spreadsheet_df.columns):
                type = "id" if i == 0 else "continuous"
                self.metadata.append({"name": col_label, "type": type})

            await self.mount(
                Container(
                    Static("Specify the column data types", id="column_assignement_label"),
                    MultipleRadioSet(
                        horizontal_label_set=["id", "continuous", "categorical"],
                        vertical_label_set=list(self.spreadsheet_df.columns.values),
                        default_value_column=1,
                        unique_first_column=True,
                        id="column_assignement",
                    ),
                    id="column_assignement_top_container",
                    classes="components",
                ),
                after=self.get_widget_by_id("spreadsheet_path_panel"),
            )
            self.get_widget_by_id("column_assignement_top_container").border_title = "Column data types"

    @on(MultipleRadioSet.Changed)
    def on_radio_set_changed(self, message):
        # Extract the row number and column label
        row_number = int(message.row.replace("row_radio_sets_", ""))
        col_label = self.spreadsheet_df.columns[row_number]

        # Get unique levels from the selected column
        levels = list(self.spreadsheet_df.iloc[:, row_number].unique())
        # ensure that all are strings
        levels = [str(i) for i in levels]

        # Filter out existing metadata for the column
        self.metadata = [item for item in self.metadata if item.get("name") != col_label]

        # Determine the metadata type based on the column
        metadata_entry = {"name": col_label}
        if message.column == 1:
            metadata_entry["type"] = "id"
        elif message.column == 2:
            metadata_entry["type"] = "categorical"
            metadata_entry["levels"] = levels
        elif message.column == 3:
            metadata_entry["type"] = "continuous"

        # Append the updated metadata entry
        self.metadata.append(metadata_entry)

    @on(Button.Pressed, "#browse")
    async def _on_add_button_pressed(self):
        await self.app.push_screen(
            FileBrowserModal(title="Select spreadsheet", path_test_function=path_test_with_isfile_true),
            self.update_spreadsheet_list,
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        # create new file item
        # dismiss some identification of it
        fileobj = SpreadsheetFileSchema().load(self.filedict)
        if not hasattr(fileobj, "metadata") or fileobj.metadata is None:
            fileobj.metadata = dict()

        if fileobj.metadata.get("variables") is None:
            fileobj.metadata["variables"] = []

        for vardict in self.metadata:
            fileobj.metadata["variables"].append(VariableSchema().load(vardict))

        ctx.cache[self.cache_name]["files"] = fileobj
        self.dismiss((self.cache_name, self.filedict["path"]))

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)

    def request_close(self):
        self.dismiss(False)
