# -*- coding: utf-8 -*-
# from utils.false_input_warning_screen import FalseInputWarning
# from utils.confirm_screen import Confirm
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widget import Widget

from ...model.file.bids import BidsFileSchema
from ...model.tags import entities
from ..utils.filebrowser import FileBrowser


class DataInput(Widget):
    def __init__(self, app, ctx, available_images, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.available_images = available_images

    def compose(self) -> ComposeResult:
        yield Grid(
            FileBrowser(app=self.top_parent, path_to="input data directory", id="data_input_file_browser"),
            id="data_input",
            classes="components",
        )

    def on_file_browser_changed(self, message):
        """Trigger the data read by the Context after a file path is selected."""
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
