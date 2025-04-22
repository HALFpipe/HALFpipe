from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static

from ...data_analyzers.context import ctx
from ...general_widgets.list_of_files_modal import ListOfFiles
from ...specialized_widgets.non_bids_file_itemization import FileItem
from ...standards import field_map_labels


class FieldMapFilesPanel(Widget):
    """
    Widget that manages field map files input, including different types of field maps
    (e.g., EPI, Siemens, Philips). Handles composition and user interactions with the UI elements.
    For EPI this mounts only one FileItem widget, for Siemens and Philips the number of FileItem widgets varies
    since user can set different types of magnitude and phase files.

    Attributes
    ----------
    field_map_type : str
        The type of field map being utilized, default is "siemens".
    field_map_types_dict : dict
        A dictionary mapping field map type keys to their corresponding descriptions.
    echo_time : int
        An attribute initialized to 0, likely used for managing timing properties.
    step_classes : list[Type[FilePatternStep]]
        A list of step classes that determine the pattern classes for the file items.
    """

    def __init__(
        self, step_classes: list, field_map_type: str = "siemens", id: str | None = None, classes: str | None = None
    ) -> None:
        """
        Initializes the FieldMapFilesPanel widget.

        Parameters
        ----------
        step_classes : list[Type[FilePatternStep]]
            A list of step classes that determine the pattern classes for the file items.
        field_map_type : str, optional
            The type of field map being utilized, default is "siemens".
        id : str, optional
            The ID of the widget, by default None.
        classes : str, optional
            CSS classes for the widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.field_map_type = field_map_type
        self.field_map_types_dict = field_map_labels
        self.echo_time = 0
        self.step_classes = step_classes

    def compose(self):
        yield Vertical(
            Button("❌", id="delete_button", classes="icon_buttons"),
            *[
                FileItem(id=self.id + "_" + str(i), classes="file_patterns", delete_button=False, pattern_class=step_class)
                for i, step_class in enumerate(self.step_classes)
            ],
            classes=self.field_map_type + "_panel",
        )

    def on_mount(self):
        """
        Sets the title for the panel based on the selected field map type after the widget is mounted.
        """
        self.query(".{}_panel".format(self.field_map_type)).last(Vertical).border_title = self.field_map_types_dict[
            self.field_map_type
        ]

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """
        Removes the file pattern item and updates the context cache when the delete button is pressed.
        """
        self.remove()
        for i in range(len(self.step_classes)):
            if self.id + "_" + str(i) in ctx.cache:
                ctx.cache.pop(self.id + "_" + str(i))

    @on(FileItem.SuccessChanged)
    def _on_file_item_success_changed(self, message: Message):
        """
        Changes widget border from green to red based on whether the files were successfully found.
        """
        success_list = []
        for i in range(len(self.step_classes)):
            success_list.append(self.get_widget_by_id(self.id + "_" + str(i)).success_value)
        if all(success_list) is True:
            self.query(".{}_panel".format(self.field_map_type)).last(Vertical).styles.border = ("thick", "green")
        else:
            self.query(".{}_panel".format(self.field_map_type)).last(Vertical).styles.border = ("thick", "red")


class DataSummaryLine(Widget):
    """
    Widget for displaying a summary of data read-in (T1, BOLD or field map files),
    including a message and a list of files.

    Attributes
    ----------
    summary : dict[str, list[str] | str | dict[str, int]]
        A dictionary containing the summary message, file paths, and tag distribution.
    """

    DEFAULT_CSS = """
    DataSummaryLine {
        height: auto;
        border: $warning;
        width: 100%;
        height: 5;
        align: center
        middle;
        .feedback_container {
            layout: horizontal;
            height: 3;
            width: 65;
            align: left
            middle;
            Static {
                width: auto;
                border: transparent;
            }
            Button {
                dock: right;
            }
        }
    }
    """

    def __init__(self, summary: dict | None = None, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the DataSummaryLine.

        Parameters
        ----------
        summary : dict[str, list[str] | str | dict[str, int]] | None, optional
            A dictionary containing the summary message, file paths, and tag distribution, by default None.
        id : str, optional
            The ID of the widget, by default None.
        classes : str, optional
            CSS classes for the widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.summary = {"message": "Found 0 files.", "files": []} if summary is None else summary

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(self.summary["message"], id="feedback"),
            Button("👁", id="show_button", classes="icon_buttons"),
            classes="feedback_container",
        )

    def update_summary(self, summary: dict[str, list[str] | str | dict[str, int]]) -> None:
        """
        Updates the summary data and the display message, and changes the border color if files are present.
        """
        self.summary = summary
        self.get_widget_by_id("feedback").update(self.summary["message"])
        # if there were some found files, then change border to green
        if len(self.summary["files"]) > 0:
            self.styles.border = ("solid", "green")

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        """
        Handles the event when the show button is pressed, displaying a list of files in a modal dialog.
        """
        self.app.push_screen(ListOfFiles(self.summary))
