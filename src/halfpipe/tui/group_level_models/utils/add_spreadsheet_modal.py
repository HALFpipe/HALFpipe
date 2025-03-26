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
from ...general_widgets.multichoice_radioset import MultipleRadioSet
from ...specialized_widgets.file_browser_modal import FileBrowserModal, path_test_with_isfile_true

aggregate_order = ["dir", "run", "ses", "task"]


class AddSpreadsheetModal(DraggableModalScreen):
    """
    A modal dialog for adding a spreadsheet file and specifying its column data types.

    This modal allows the user to select a spreadsheet file, view its columns,
    and assign data types (id, continuous, categorical) to each column. It
    integrates with the `FileBrowserModal` for file selection and the
    `MultipleRadioSet` for column type assignment.

    Attributes
    ----------
    instance_count : int
        A class-level counter to keep track of the number of instances.
    title_bar.title : str
        The title of the modal window.
    instructions : str
        The instruction text displayed at the top of the modal.
    cache_name : str
        A unique name used to store the spreadsheet file in the application's cache.
    filedict : dict[str, str | list]
        A dictionary to store file-related information, such as the file path.
    metadata : list[Dict[str, Any]]
        A list to store metadata about the spreadsheet columns, including their
        names and assigned data types.
    last_selected : str | None
        The path of the last selected spreadsheet file, or None if no file has
        been selected.
    widgets_to_mount : list[Widget]
        A list of widgets to be mounted on the modal window.

    Methods
    -------
    __init__(id, classes)
        Initializes the modal with optional ID and classes.
    on_mount()
        Mounts the initial widgets and sets up the layout.
    update_spreadsheet_list(spreadsheet_path)
        Updates the UI with the selected spreadsheet file and its columns.
    on_radio_set_changed(message)
        Handles changes in the column type assignments.
    _on_add_button_pressed()
        Opens the `FileBrowserModal` to select a spreadsheet file.
    _on_ok_button_pressed()
        Handles the OK button press, saving the spreadsheet file and its
        metadata to the cache.
    _on_cancel_button_pressed()
        Handles the Cancel button press, dismissing the modal.
    request_close()
        Handles the event when the close button is pressed.
    """

    instance_count = 0
    """A class-level counter to keep track of the number of instances."""

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the AddSpreadsheetModal.

        Parameters
        ----------
        id : str, optional
            An optional identifier for the modal window, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the modal
            window, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.title_bar.title = "Path to the spreadsheet"
        self.instructions = "Select or add path of the covariates/group data spreadsheet file"
        filepaths = ctx.database.get(datatype="spreadsheet")
        self.cache_name = "__spreadsheet_file_" + str(self.instance_count)
        self.instance_count += 1
        # A dictionary to store file-related information, such as the file path.
        self.filedict: dict[str, str | list] = {}
        # A list to store metadata about the spreadsheet columns.
        self.metadata: list[Dict[str, Any]] = []
        # The path of the last selected spreadsheet file.
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
        """
        Updates the UI with the selected spreadsheet file and its columns.

        This method is called when a spreadsheet file is selected. It updates
        the spreadsheet path label, reads the spreadsheet, and dynamically
        adds a `MultipleRadioSet` to assign data types to the columns.

        Parameters
        ----------
        spreadsheet_path : str | bool
            The path to the selected spreadsheet file, or False if no file
            was selected.
        """
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
        """
        Handles changes in the column type assignments.

        This method is called when a radio button selection changes in the
        `MultipleRadioSet`. It updates the metadata for the corresponding
        column based on the selected data type.

        Parameters
        ----------
        message : MultipleRadioSet.Changed
            The message object containing information about the radio button
            selection change.
        """
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
        """
        Opens the `FileBrowserModal` to select a spreadsheet file.

        This method is called when the "Browse" button is pressed. It
        pushes the `FileBrowserModal` onto the screen to allow the user
        to select a spreadsheet file.
        """
        await self.app.push_screen(
            FileBrowserModal(title="Select spreadsheet", path_test_function=path_test_with_isfile_true),
            self.update_spreadsheet_list,
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        """
        Handles the OK button press, saving the spreadsheet file and its metadata to the cache.

        This method is called when the "OK" button is pressed. It creates a
        `SpreadsheetFileSchema` object, populates it with the selected file
        and metadata, and stores it in the application's cache.
        """
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
        """
        Handles the Cancel button press, dismissing the modal.

        This method is called when the "Cancel" button is pressed. It
        dismisses the modal with a value of False.
        """
        self.dismiss(False)

    def request_close(self):
        """
        Handles the event when the close button is pressed.

        This method is called when the user attempts to close the modal
        window. It dismisses the modal with a value of False.
        """
        self.dismiss(False)
