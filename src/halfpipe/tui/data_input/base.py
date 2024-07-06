# -*- coding: utf-8 -*-

from typing import List, Type

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static

from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

from ...model.file.bids import BidsFileSchema
from ...model.tags import entities
from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
from ..utils.file_pattern_steps import (
    AnatStep,
    BoldStep,
    EPIStep,
    EventsStep,
    FieldMapStep,
    FilePatternStep,
    Magnitude1Step,
    Magnitude2Step,
    MatEventsStep,
    Phase1Step,
    Phase2Step,
    PhaseDiffStep,
    TsvEventsStep,
    TxtEventsStep,
)
from ..utils.filebrowser import FileBrowser
from ..utils.list_of_files_modal import ListOfFiles
from ..utils.non_bids_file_itemization import FileItem
from ..utils.selection_modal import DoubleSelectionModal, SelectionModal
from ..utils.summary_steps import AnatSummaryStep, BoldSummaryStep, FmapSummaryStep

# There are 4 SummarySteps: FilePatternSummaryStep, AnatSummaryStep, BoldSummaryStep, FmapSummaryStep
# AnatSummaryStep > BoldSummaryStep > get_post_func_steps > FmapSummaryStep > END
# get_post_func_steps: will now be checked in different tab
# def get_post_func_steps(this_next_step_type: Optional[Type[Step]]) -> Type[Step]:
# class DummyScansStep(Step):
# class CheckBoldSliceTimingStep(CheckMetadataStep):
# class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
# class DoSliceTimingStep(YesNoStep):
####################################################################################


class FieldMapFilesPanel(Widget):
    def __init__(self, field_map_type="siemens", step_classes=None, **kwargs) -> None:
        """ """
        super().__init__(**kwargs)
        self.field_map_type = field_map_type
        self.field_map_types_dict = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
        self.echo_time = 0
        self.step_classes = step_classes
        print("thissssssssssssssssssssssss id", self.id)

    def compose(self):
        yield Vertical(
            Button("❌", id="delete_button", classes="icon_buttons"),
            *[
                FileItem(delete_button=False, classes="file_patterns", pattern_class=step_class, id_key=self.id)
                for step_class in self.step_classes
            ],
            classes=self.field_map_type + "_panel",
        )

    def on_mount(self):
        self.query(".{}_panel".format(self.field_map_type)).last(Vertical).border_title = self.field_map_types_dict[
            self.field_map_type
        ]

    # def update_echo_time(self, echo_time):
    # # self.echo_time = variable
    # echo_time_static = self.get_widget_by_id("echo_time")
    # if echo_time_static is not None:
    # echo_time_static.update(Text("Echo time difference in seconds: ") + echo_time)

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """Remove the file pattern item."""
        self.remove()
        ctx.cache.pop(self.id)

    @on(Button.Pressed, "#edit_button2")
    def _on_edit_button_pressed(self):
        """Remove the file pattern item."""


#      self.app.push_screen(SetEchoTimeDifferenceModal(), self.update_echo_time)


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
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._id_counter = 0

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
            FileBrowser(path_to="INPUT DATA DIRECTORY", id="data_input_file_browser"),
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
            # move this to features tab somewhere

            # yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")
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
        # self.get_widget_by_id("event_file_panel").border_title = "Event files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"

    @on(Button.Pressed, "#add_t1_image_button")
    def _add_t1_image(self):
        self.get_widget_by_id("t1_image_panel").mount(FileItem(classes="file_patterns", pattern_class=AnatStep()))
        self.refresh()

    @on(Button.Pressed, "#add_bold_image_button")
    def _add_bold_image(self):
        self.get_widget_by_id("bold_image_panel").mount(
            FileItem(classes="file_patterns", pattern_class=BoldStep(app=self.app))
        )
        self.refresh()

    @on(Button.Pressed, "#add_event_file_button")
    def _add_event_file(self):
        def mount_file_item_widget(event_file_type):
            events_step_type: Type[EventsStep] | None = None  # Initialize with a default value
            if event_file_type == "bids":
                events_step_type = TsvEventsStep
            elif event_file_type == "fsl":
                events_step_type = TxtEventsStep
            elif event_file_type == "spm":
                events_step_type = MatEventsStep
            if events_step_type is not None:
                self.get_widget_by_id("event_file_panel").mount(
                    FileItem(classes="file_patterns", pattern_class=events_step_type())
                )
                self.refresh()
            else:
                print("isssssssssssssssssssssss none")

        options = {
            "spm": "SPM multiple conditions",
            "fsl": "FSL 3-column",
            "bids": "BIDS TSV",
        }
        self.app.push_screen(
            SelectionModal(
                title="Event file type specification",
                instructions="Specify the event file type",
                options=options,
                id="event_files_type_modal",
            ),
            mount_file_item_widget,
        )

    @on(Button.Pressed, "#add_field_map_button")
    def _add_field_map_file(self):
        def branch_field_maps(fmap_type):
            if fmap_type == "siemens":
                self.app.push_screen(
                    DoubleSelectionModal(
                        title="Magnitude & phase images",
                        instructions=["Specify the type of the magnitude images", "Specify the type of the phase images"],
                        options=[
                            {
                                "siemens_one_mag_image_file": "One magnitude image file",
                                "siemens_two_mag_image_file": "Two magnitude image file",
                            },
                            {
                                "siemens_one_phase_image_file": "One phase difference image",
                                "siemens_two_phase_image_file": "Two phase images",
                            },
                        ],
                        #  id='magnitude_images_modal'
                    ),
                    self._mount_field_item_group,
                )
            elif fmap_type == "philips":
                self.app.push_screen(
                    SelectionModal(
                        title="Magnitude & phase images",
                        instructions="Specify the type of the magnitude images",
                        options={
                            "philips_one_phase_image_file": "One phase difference image",
                            "philips_two_phase_image_file": "Two phase images",
                        },
                        # id='magnitude_images_modal'
                    ),
                    self._mount_field_item_group,
                )
            elif fmap_type == "epi":
                self.get_widget_by_id("field_map_panel").mount(
                    FieldMapFilesPanel(field_map_type=fmap_type, step_classes=[EPIStep()])
                )
                self.refresh()

        options = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
        self.app.push_screen(
            SelectionModal(
                title="Field map type specification",
                instructions="Specify type of the field maps",
                options=options,
                id="field_maps_type_modal",
            ),
            branch_field_maps,
            #   self._mount_field_item_group # this was here before
        )

    def _mount_field_item_group(self, field_map_user_choices):
        print("fffffffffffffffffffff", field_map_user_choices)
        # wrap to list, because from the single selection, the choices is just a string and not a list
        field_map_user_choices = (
            field_map_user_choices if isinstance(field_map_user_choices, list) else [field_map_user_choices]
        )
        # get string whether siemens or philips
        field_map_type = field_map_user_choices[0].split("_")[0]
        # find which classes are needed
        step_classes: List[FilePatternStep] = []

        if any("one_mag_image_file" in s for s in field_map_user_choices):
            step_classes += [Magnitude1Step()]
        elif any("two_mag_image_file" in s for s in field_map_user_choices):
            step_classes += [Magnitude1Step(), Magnitude2Step()]
        if any("one_phase_image_file" in s for s in field_map_user_choices):
            step_classes += [PhaseDiffStep(app=self.app)]
        elif any("two_phase_image_file" in s for s in field_map_user_choices):
            step_classes += [Phase1Step(), Phase2Step()]
        if field_map_type == "philips":
            step_classes += [FieldMapStep()]
            step_classes = step_classes[::-1]
        print(
            "ooooooooooooo",
            field_map_user_choices,
            any("one_phase_image_file" in s for s in field_map_user_choices),
            any("two_phase_image_file" in s for s in field_map_user_choices),
        )
        print("1qqqqqqqqqqqqqqqqqssssssssss step_classes", step_classes)
        print("2qqqqqqqqqqqqqqqqqssssssssss step_classes", step_classes)
        if field_map_type is not None:
            self.get_widget_by_id("field_map_panel").mount(
                FieldMapFilesPanel(
                    field_map_type=field_map_type, step_classes=step_classes, id="field_maps_" + str(self._id_counter)
                )
            )
            self._id_counter += 1
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

        self.feed_contex_and_extract_available_images(message.selected_path)
        # try:
        # self.feed_contex_and_extract_available_images(message.selected_path)
        # except:  # noqa E722
        # self.app.push_screen(
        # FalseInputWarning(
        # warning_message="The selected data directory seems not be a BIDS directory!",
        # title="Error - Non a bids directory",
        # id="not_bids_dir_warning_modal",
        # classes="error_modal",
        # ),
        # on_dismiss_this_modal,
        # )

    def feed_contex_and_extract_available_images(self, file_path):
        """Feed the Context object with the path to the data fields and extract available images."""
        ctx.put(BidsFileSchema().load({"datatype": "bids", "path": file_path}))

        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = ctx.database.get(**bold_filedict)
        print("bbbbbbbbbbbbbbbbbbbbbbbbbbbb", file_path, filepaths)
        self.filepaths = list(filepaths)
        assert len(self.filepaths) > 0

        db_entities, db_tags_set = ctx.database.multitagvalset(entities, filepaths=self.filepaths)
        self.app.available_images[db_entities[0]] = sorted(list({t[0] for t in db_tags_set}))

        anat_summary_step = AnatSummaryStep()
        bold_summary_step = BoldSummaryStep()
        fmap_summary_step = FmapSummaryStep()

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
