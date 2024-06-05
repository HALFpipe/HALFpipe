# -*- coding: utf-8 -*-
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, RadioButton, RadioSet, Static

from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

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
# There are 4 SummarySteps: FilePatternSummaryStep, AnatSummaryStep, BoldSummaryStep, FmapSummaryStep
# AnatSummaryStep > BoldSummaryStep > get_post_func_steps > FmapSummaryStep > END
# get_post_func_steps: will now be checked in different tab
# def get_post_func_steps(this_next_step_type: Optional[Type[Step]]) -> Type[Step]:
# class DummyScansStep(Step):
# class CheckBoldSliceTimingStep(CheckMetadataStep):
# class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
# class DoSliceTimingStep(YesNoStep):
from ...model.file.anat import T1wFileSchema
from ...model.file.bids import BidsFileSchema
from ...model.file.fmap import (
    BaseFmapFileSchema,
)
from ...model.file.func import BoldFileSchema
from ...model.tags import entities
from ...model.tags import entity_longnames as entity_display_aliases
from ...model.utils import get_schema_entities
from ...utils.format import inflect_engine as p
from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.false_input_warning_screen import FalseInputWarning
from ..utils.filebrowser import FileBrowser
from ..utils.list_of_files_modal import ListOfFiles
from ..utils.non_bids_file_itemization import FileItem


class FilePatternSummaryStep:
    def __init__(self, filetype_str, filedict, schema, ctx=None):
        self.filetype_str = filetype_str
        self.filedict = filedict
        self.schema = schema
        self.entities = get_schema_entities(schema)  # Assumes a function to extract schema entities

        # Assuming ctx and database are accessible here
        self.filepaths = ctx.database.get(**self.filedict)
        self.message = messagefun(
            ctx.database,
            self.filetype_str,
            self.filepaths,
            self.entities,
            entity_display_aliases,  # This should be defined somewhere accessible
        )

    @property
    def get_message(self):
        return self.message

    @property
    def get_summary(self):
        return {"message": self.message, "files": self.filepaths}


class AnatSummaryStep(FilePatternSummaryStep):
    def __init__(self, ctx=None):
        super().__init__(
            filetype_str="T1-weighted image", filedict={"datatype": "anat", "suffix": "T1w"}, schema=T1wFileSchema, ctx=ctx
        )


class BoldSummaryStep(FilePatternSummaryStep):
    def __init__(self, ctx=None):
        super().__init__(
            filetype_str="BOLD image", filedict={"datatype": "func", "suffix": "bold"}, schema=BoldFileSchema, ctx=ctx
        )


class FmapSummaryStep(FilePatternSummaryStep):
    def __init__(self, ctx=None):
        super().__init__(filetype_str="field map image", filedict={"datatype": "fmap"}, schema=BaseFmapFileSchema, ctx=ctx)


# class FilePatternSummaryStep():
# from ..model.tags import entity_longnames as entity_display_aliases

# entity_display_aliases: ClassVar[Dict] = entity_display_aliases

# filetype_str: ClassVar[str] = "file"
# filedict: Dict[str, str] = dict()
# schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

# next_step_type: Optional[Type[Step]] = None

# entities = get_schema_entities(self.schema)

# filepaths = ctx.database.get(**self.filedict)
# message = messagefun(
# ctx.database,
# self.filetype_str,
# filepaths,
# entities,
# self.entity_display_aliases,
# )

# def get_message(self):
# return message

# class AnatSummaryStep(FilePatternSummaryStep):
# filetype_str = "T1-weighted image"
# filedict = {"datatype": "anat", "suffix": "T1w"}
# schema = T1wFileSchema

# #FuncSummaryStep = BoldSummaryStep
# #next_step_type = FuncSummaryStep

# class BoldSummaryStep(FilePatternSummaryStep):
# filetype_str = "BOLD image"
# filedict = {"datatype": "func", "suffix": "bold"}
# schema = BoldFileSchema

# #next_step_type = get_post_func_steps(FmapSummaryStep)

# class FmapSummaryStep(FilePatternSummaryStep):
# from ...model.file.fmap import BaseFmapFileSchema

# filetype_str = "field map image"
# filedict = {"datatype": "fmap"}
# bold_filedict = {"datatype": "func", "suffix": "bold"}

# schema = BaseFmapFileSchema

# # next_step_type = FeaturesStep


def messagefun(database, filetype, filepaths, tagnames, entity_display_aliases: dict | None = None):
    entity_display_aliases = dict() if entity_display_aliases is None else entity_display_aliases
    message = ""
    if filepaths is not None:
        message = p.inflect(f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})")
        if len(filepaths) > 0:
            n_by_tag = dict()
            for tagname in tagnames:
                tagvalset = database.tagvalset(tagname, filepaths=filepaths)
                if tagvalset is not None:
                    n_by_tag[tagname] = len(tagvalset)
            tagmessages = [
                p.inflect(f"{n} plural('{entity_display_aliases.get(tagname, tagname)}', {n})")
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)
    return message


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


class DataSummaryLine(Widget):
    def __init__(self, summary=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.summary = {"message": "Found 0 files.", "files": []} if summary is None else summary

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(self.summary["message"], id="feedback"),
            Button("👁", id="show_button", classes="icon_buttons"),
            classes="feedback_container",
        )

    def update_summary(self, summary):
        self.summary = summary
        self.get_widget_by_id("feedback").update(self.summary["message"])
        if len(self.summary["files"]) > 0:
            self.styles.border = ("solid", "green")

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        self.app.push_screen(ListOfFiles(self.summary))


class DataInput(Widget):
    def __init__(self, app, ctx, available_images, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.available_images = available_images

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "If 'on' then just select the BIDS top directory. Otherwise you must select file patterns\
for T1-weighted image, BOLD image and event files.",
                id="description",
            ),
            Horizontal(
                Static("Data in BIDS format", id="bids_format_switch", classes="label"),
                TextSwitch(value=True),
                #        classes="components",
            ),
            id="instructions",
            classes="components",
        )
        yield Grid(
            FileBrowser(app=self.top_parent, path_to="INPUT DATA DIRECTORY", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        yield Vertical(
            DataSummaryLine(id="feedback_anat"),
            DataSummaryLine(id="feedback_bold"),
            DataSummaryLine(id="feedback_fmap"),
            id="bids_summary_panel",
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
        self.get_widget_by_id("bids_summary_panel").border_title = "Data input file summary"

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
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "visible"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"

        else:
            self.get_widget_by_id("bids_panel").styles.visibility = "hidden"
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "hidden"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "visible"

    def on_file_browser_changed(self, message):
        """Trigger the data read by the Context after a file path is selected."""

        def on_dismiss_this_modal(value):
            self.get_widget_by_id("data_input_file_browser").update_input(None)

        def confirmation(respond: bool):
            print("bla")
            if ~respond:
                self.mount(
                    PathPatternBuilder(
                        path="/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz", classes="components"
                    )
                )

        try:
            self.feed_contex_and_extract_available_images(message.selected_path)
        except:  # noqa E722
            self.app.push_screen(
                FalseInputWarning(
                    warning_message="The selected data directory seems not be a BIDS directory!",
                    title="Error - Non a bids directory",
                    id="not_bids_dir_warning_modal",
                    classes="error_modal",
                ),
                on_dismiss_this_modal,
            )

    def feed_contex_and_extract_available_images(self, file_path):
        """Feed the Context object with the path to the data fields and extract available images."""
        self.ctx.put(BidsFileSchema().load({"datatype": "bids", "path": file_path}))

        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = self.ctx.database.get(**bold_filedict)
        self.filepaths = list(filepaths)
        assert len(self.filepaths) > 0

        db_entities, db_tags_set = self.ctx.database.multitagvalset(entities, filepaths=self.filepaths)
        self.available_images[db_entities[0]] = sorted(list({t[0] for t in db_tags_set}))

        anat_summary_step = AnatSummaryStep(ctx=self.app.ctx)
        bold_summary_step = BoldSummaryStep(ctx=self.app.ctx)
        fmap_summary_step = FmapSummaryStep(ctx=self.app.ctx)

        self.get_widget_by_id("feedback_anat").update_summary(anat_summary_step.get_summary)
        self.get_widget_by_id("feedback_bold").update_summary(bold_summary_step.get_summary)
        self.get_widget_by_id("feedback_fmap").update_summary(fmap_summary_step.get_summary)

        # at this point, all went well, change border from red to green
        self.get_widget_by_id("data_input_file_browser").styles.border = ("solid", "green")
        # contribute with True to show hidden tabs
        self.app.flags_to_show_tabs["from_input_data_tab"] = True
        self.app.show_hidden_tabs()

    def manually_change_label(self, label):
        """If the input data folder was set by reading an existing json file via the working directory widget,
        the label must be changed externally. This is done in the most top base.
        """
        self.get_widget_by_id("data_input_file_browser").update_input(label)
