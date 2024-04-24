# -*- coding: utf-8 -*-
# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static, Switch

from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

from ...model.file.bids import BidsFileSchema
from ...model.tags import entities
from ..utils.confirm_screen import Confirm
from ..utils.filebrowser import FileBrowser

# from ..utils.path_segment_highlighter import PathSegmentHighlighter
# from ...ui.components import (
# FilePatternInputView,
# SpacerView,
# TextElement,
# TextInputView,
# TextView,
# )
from ..utils.non_bids_file_itemization import FileItem


class DataInput(Widget):
    def __init__(self, app, ctx, available_images, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.available_images = available_images

    def compose(self) -> ComposeResult:
        yield Static(
            "If 'on' then just selectthe BIDS top directory. Otherwise you must select file patterns"
            "for T1-weighted image, BOLD image and event files.",
            id="instructions",
            classes="components",
        )
        yield Horizontal(
            Static("Data in BIDS format", id="bids_format_switch", classes="label"),
            Switch(value=True),
            classes="components",
        )
        yield Grid(
            FileBrowser(app=self.top_parent, path_to="input data directory", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        with VerticalScroll(id="non_bids_panel", classes="components"):
            yield VerticalScroll(Button("Add", id="add_t1_image_button"), id="t1_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_bold_image_button"), id="bold_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_field_map_button"), id="field_map_panel", classes="non_bids_panels")

    # anatomical/structural data
    # functional data

    def on_mount(self) -> None:
        self.get_widget_by_id("instructions").border_title = "Data input"
        self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        self.get_widget_by_id("t1_image_panel").border_title = "T1-weighted image file pattern"
        self.get_widget_by_id("bold_image_panel").border_title = "BOLD image files patterns"
        self.get_widget_by_id("event_file_panel").border_title = "Event files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"

    @on(Button.Pressed, "#add_t1_image_button")
    def _add_t1_image(self):
        self.get_widget_by_id("t1_image_panel").mount(FileItem(classes="file_patterns"))
        self.refresh()

    @on(Button.Pressed, "#add_bold_image_button")
    def _add_bold_image(self):
        self.get_widget_by_id("bold_image_panel").mount(FileItem(classes="file_patterns"))
        self.refresh()

    @on(Button.Pressed, "#add_event_file_button")
    def _add_event_file(self):
        self.get_widget_by_id("event_file_panel").mount(FileItem(classes="file_patterns"))
        self.refresh()

    def on_switch_changed(self, message):
        print("mmmmmmmmmmmmmmmmmmmmmmmm", message.value)
        if message.value:
            self.get_widget_by_id("bids_panel").styles.visibility = "visible"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"

        else:
            self.get_widget_by_id("bids_panel").styles.visibility = "hidden"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "visible"

    def on_file_browser_changed(self, message):
        """Trigger the data read by the Context after a file path is selected."""

        def confirmation(respond: bool):
            print("bla")
            if ~respond:
                self.mount(
                    PathPatternBuilder(
                        path="/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz", classes="components"
                    )
                )

        self.top_parent.push_screen(
            Confirm(text="Are data in BIDS format?", left_button_text="Yes", right_button_text="No"), confirmation
        )

        self.feed_contex_and_extract_available_images(message.selected_path)

    def feed_contex_and_extract_available_images(self, file_path):
        """Feed the Context object with the path to the data fields and extract available images."""
        self.ctx.put(BidsFileSchema().load({"datatype": "bids", "path": file_path}))

        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = self.ctx.database.get(**bold_filedict)
        self.filepaths = list(filepaths)
        assert len(self.filepaths) > 0

        db_entities, db_tags_set = self.ctx.database.multitagvalset(entities, filepaths=self.filepaths)
        self.available_images[db_entities[0]] = sorted(list({t[0] for t in db_tags_set}))

    def manually_change_label(self, label):
        """If the input data folder was set by reading an existing json file via the working directory widget,
        the label must be changed externally. This is done in the most top base.
        """
        self.get_widget_by_id("data_input_file_browser").update_input(label)
