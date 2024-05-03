# -*- coding: utf-8 -*-
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, RadioButton, RadioSet, Static, Switch

from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

from ...model.file.bids import BidsFileSchema
from ...model.tags import entities
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.filebrowser import FileBrowser
from ..utils.non_bids_file_itemization import FileItem

# TODO
# For bids, this is automatic message
# Found 0 field map image files
# after putting BOLD images, i need this message
# Check repetition time values
# 18 images - 0.75 seconds
# 36 images - 2.0 seconds
# Proceed with these values?
# [Yes] [No]
# Specify repetition time in seconds
# [0]


class SetEchoTimeDifferenceModal(DraggableModalScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_bar.title = "Echo time difference"

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Static("Set Echo time difference in seconds"),
                Input(""),
                Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        input_widget = self.query_one(Input)
        if input_widget.value == "":
            self.dismiss(Text("Not Specified!", "on red"))
        else:
            self.dismiss(Text(input_widget.value, "on green"))

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)


class FieldMapFilesPanel(Widget):
    def __init__(self, field_map_type="siemens", **kwargs) -> None:
        """ """
        super().__init__(**kwargs)
        self.field_map_type = field_map_type
        self.field_map_types_dict = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
        self.echo_time = 0

    def compose(self):
        if self.field_map_type == "siemens":
            yield Vertical(
                Button("❌", id="delete_button", classes="icon_buttons"),
                Horizontal(
                    Static(Text("Echo time difference in seconds: ") + Text("Not Specified!", "on red"), id="echo_time"),
                    Button("🖌", id="edit_button2", classes="icon_buttons"),
                ),
                FileItem(delete_button=False, classes="file_patterns", title="Path pattern of the magnitude image files"),
                FileItem(
                    delete_button=False,
                    classes="file_patterns",
                    title="Path pattern of the phase/phase difference image files",
                ),
                classes=self.field_map_type + "_panel",
            )
        elif self.field_map_type == "philips":
            yield Vertical(
                Button("❌", id="delete_button", classes="icon_buttons"),
                FileItem(delete_button=False, classes="file_patterns", title="Path pattern of the field map image files"),
                FileItem(delete_button=False, classes="file_patterns", title="Path pattern of the magnitude image files"),
                classes=self.field_map_type + "_panel",
            )
        elif self.field_map_type == "epi":
            yield Vertical(
                Button("❌", id="delete_button", classes="icon_buttons"),
                FileItem(
                    delete_button=False, classes="file_patterns", title="Path pattern of the blip-up blip-down EPI image files"
                ),
                classes=self.field_map_type + "_panel",
            )

    def on_mount(self):
        self.query(".{}_panel".format(self.field_map_type)).last(Vertical).border_title = self.field_map_types_dict[
            self.field_map_type
        ]
        if self.field_map_type == "siemens":
            self.app.push_screen(SetEchoTimeDifferenceModal(), self.update_echo_time)

    def update_echo_time(self, echo_time):
        # self.echo_time = variable
        echo_time_static = self.get_widget_by_id("echo_time")
        if echo_time_static is not None:
            echo_time_static.update(Text("Echo time difference in seconds: ") + echo_time)

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """Remove the file pattern item."""
        self.remove()

    @on(Button.Pressed, "#edit_button2")
    def _on_edit_button_pressed(self):
        """Remove the file pattern item."""
        self.app.push_screen(SetEchoTimeDifferenceModal(), self.update_echo_time)


class FieldMapTypeModal(DraggableModalScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_bar.title = "Field map type specification"
        RadioButton.BUTTON_INNER = "X"
        self.options = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }

    def on_mount(self) -> None:
        """Called when the window is mounted."""
        self.content.mount(
            Container(
                Static("Specify type of the field maps", id="title"),
                RadioSet(*[RadioButton(self.options[key]) for key in self.options]),
                Horizontal(Button("OK", id="ok"), Button("Cancel", id="cancel")),
                id="top_container",
            )
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        self.dismiss(self.choice)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(None)

    @on(RadioSet.Changed)
    def _on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.choice = list(self.options.keys())[event.index]


class DataInput(Widget):
    def __init__(self, app, ctx, available_images, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.available_images = available_images

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "If 'on' then just selectthe BIDS top directory. Otherwise you must select file patterns"
                "for T1-weighted image, BOLD image and event files.",
            ),
            Horizontal(
                Static("Data in BIDS format", id="bids_format_switch", classes="label"),
                Switch(value=True),
                #        classes="components",
            ),
            id="instructions",
            classes="components",
        )
        yield Grid(
            FileBrowser(app=self.top_parent, path_to="input data directory", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        with VerticalScroll(id="non_bids_panel", classes="components"):
            yield Static(
                "For each file type you need to create a 'path pattern' based on which all files of the particular type will \
be queried. In the pop-up window, choose one particular file (use browse, or copy-paste) and highlight parts \
of the string to be replaced by wildcards. You can also use type hints by starting typing '{' in front of the substring.",
                id="help_top",
            )
            yield Static("Example: We have a particular T1 file and highlight parts with '0001' which represents subjects.")
            yield Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz",
                    spans=[(35, 39, "on red"), (49, 53, "on red")],
                ),
                classes="examples",
            )
            yield Static("After submitting the highlighted parts will be replaced with a particular wildcard type")
            yield Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-{subject}/anat/sub-{subject}_T1w.nii.gz",
                    spans=[(35, 44, "on red"), (54, 63, "on red")],
                ),
                classes="examples",
            )

            yield VerticalScroll(Button("Add", id="add_t1_image_button"), id="t1_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_bold_image_button"), id="bold_image_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")
            yield VerticalScroll(Button("Add", id="add_field_map_button"), id="field_map_panel", classes="non_bids_panels")

    # anatomical/structural data
    # functional data

    def on_mount(self) -> None:
        self.get_widget_by_id("instructions").border_title = "Data format"
        self.get_widget_by_id("bids_panel").border_title = "Path to BIDS directory"
        self.get_widget_by_id("non_bids_panel").border_title = "Path pattern setup"

        self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        self.get_widget_by_id("t1_image_panel").border_title = "T1-weighted image file pattern"
        self.get_widget_by_id("bold_image_panel").border_title = "BOLD image files patterns"
        self.get_widget_by_id("event_file_panel").border_title = "Event files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"

    @on(Button.Pressed, "#add_t1_image_button")
    def _add_t1_image(self):
        self.get_widget_by_id("t1_image_panel").mount(
            FileItem(classes="file_patterns", title="T1-weighted image file pattern")
        )
        self.refresh()

    @on(Button.Pressed, "#add_bold_image_button")
    def _add_bold_image(self):
        self.get_widget_by_id("bold_image_panel").mount(FileItem(classes="file_patterns", title="BOLD image file pattern"))
        self.refresh()

    @on(Button.Pressed, "#add_event_file_button")
    def _add_event_file(self):
        self.get_widget_by_id("event_file_panel").mount(FileItem(classes="file_patterns", title="Event file pattern"))
        self.refresh()

    @on(Button.Pressed, "#add_field_map_button")
    def _add_field_map_file(self):
        self.app.push_screen(FieldMapTypeModal(), self._mount_field_item_group)

    def _mount_field_item_group(self, field_map_type):
        self.get_widget_by_id("field_map_panel").mount(FieldMapFilesPanel(field_map_type=field_map_type))
        self.refresh()

    def on_switch_changed(self, message):
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

        # self.top_parent.push_screen(
        # Confirm(text="Are data in BIDS format?", left_button_text="Yes", right_button_text="No"), confirmation
        # )

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
