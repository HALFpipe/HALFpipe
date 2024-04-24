# -*- coding: utf-8 -*-

import sys

sys.path.append("/home/tomas/github/HALFpipe/src/")

from textual import on
from textual.app import App
from textual.containers import Grid, HorizontalScroll, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static

from halfpipe.tui.utils.list_of_files_modal import ListOfFiles
from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder


class FileItem(Widget):
    def __init__(self, **kwargs) -> None:
        """ """
        super().__init__(**kwargs)
        # dictionary for results from the PathPatternBuilder
        self.pattern_match_results = {"file_pattern": "", "message": "Found 0 files.", "files": []}

    def compose(self):
        yield HorizontalScroll(Static("Edit to enter the file pattern", id="static_file_pattern"))
        with Grid(id="icon_buttons_container"):
            yield Button("🖌", id="edit_button", classes="icon_buttons")
            yield Button("👁", id="show_button", classes="icon_buttons")
            yield Button("❌", id="delete_button", classes="icon_buttons")

    def on_mount(self) -> None:
        self.get_widget_by_id("edit_button").tooltip = "Edit"
        self.get_widget_by_id("delete_button").tooltip = "Delete"
        self.app.push_screen(
            PathPatternBuilder(
                path="/home/tomas/github/ds002785_v2/sub-0001/func/sub-0001_task-emomatching_acq-seq_bold.nii.gz"
            ),
            self._update_file_pattern,
        )

    @on(Button.Pressed, "#edit_button")
    def _on_edit_button_pressed(self):
        """
        Opens modal for selecting the search file pattern.
        The results from this modal goes then to _update_file_pattern function.
        """
        self.app.push_screen(
            PathPatternBuilder(
                path="/home/tomas/github/ds002785_v2/sub-0001/func/sub-0001_task-emomatching_acq-seq_bold.nii.gz"
            ),
            self._update_file_pattern,
        )

    def _update_file_pattern(self, pattern_match_results):
        """Update various variables based on the results from the PathPatternBuilder"""
        self.pattern_match_results = pattern_match_results
        # Update the static label using the file pattern.
        self.get_widget_by_id("static_file_pattern").update(pattern_match_results["file_pattern"])
        # Tooltip telling us how many files were  found.
        self.get_widget_by_id("show_button").tooltip = pattern_match_results["message"]
        # If 0 files were found, the border is red, otherwise green.
        if len(pattern_match_results["files"]) > 0:
            self.styles.border = ("solid", "green")
        else:
            self.styles.border = ("solid", "red")

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """Remove the file pattern item."""
        self.remove()

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        """Shows a modal with the list of files found using the given pattern."""
        self.app.push_screen(ListOfFiles(self.pattern_match_results))


class Main(App):
    CSS_PATH = ["./tcss/path_segment_highlighter2.tcss"]

    def compose(self):
        with VerticalScroll(id="test_container"):
            yield Button("Add", id="add_button")

    def on_mount(self) -> None:
        self.get_widget_by_id("add_button").tooltip = "Add new file pattern"

    @on(Button.Pressed, "#add_button")
    def _add_file_time(self):
        self.get_widget_by_id("test_container").mount(FileItem(classes="file_patterns"))
        self.refresh()


if __name__ == "__main__":
    app = Main()
    app.run()
