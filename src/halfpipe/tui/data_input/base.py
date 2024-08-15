# -*- coding: utf-8 -*-

from typing import List

import pandas as pd
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static

from ...model.tags import entities
from ..utils.confirm_screen import Confirm
from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
from ..utils.false_input_warning_screen import SimpleMessageModal
from ..utils.file_pattern_steps import (
    AnatStep,
    BoldStep,
    EPIStep,
    FieldMapStep,
    FilePatternStep,
    Magnitude1Step,
    Magnitude2Step,
    Phase1Step,
    Phase2Step,
    PhaseDiffStep,
)
from ..utils.filebrowser import FileBrowserForBIDS
from ..utils.list_of_files_modal import ListOfFiles
from ..utils.meta_data_steps import AcqToTaskMappingStep
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
    """
    Widget that manages field map files input, including different types of field maps
    (e.g., EPI, Siemens, Philips). Handles composition and user interactions with the UI elements.
    For EPI this mounts only one FileItem widget, for Siemens and Philips the number of FileItem widgets varies
    since user can set different types of magnitude and phase files.

    Parameters
    ----------
    id : str or None, optional
        Unique identifier for the widget.
    classes : str or None, optional
        CSS classes to apply to the widget.
    field_map_type : str, optional
        Type of the field map, by default "siemens".
    step_classes : list, optional
        List of step classes to be used in the panel.
    **kwargs : dict
        Additional keyword arguments.
    """

    def __init__(
        self, id: str | None = None, classes: str | None = None, field_map_type="siemens", step_classes=None, **kwargs
    ) -> None:
        """ """
        super().__init__(id=id, classes=classes)
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
                FileItem(id=self.id + "_" + str(i), classes="file_patterns", delete_button=False, pattern_class=step_class)
                for i, step_class in enumerate(self.step_classes)
            ],
            classes=self.field_map_type + "_panel",
        )

    def on_mount(self):
        """Sets the title for the panel based on the selected field map type after the widget is mounted."""
        self.query(".{}_panel".format(self.field_map_type)).last(Vertical).border_title = self.field_map_types_dict[
            self.field_map_type
        ]

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """
        Removes the file pattern item and updates the context cache.
        """
        self.remove()
        for i in range(len(self.step_classes)):
            ctx.cache.pop(self.id + "_" + str(i))

    def get_number_of_found_files(self):
        number_of_field_map_files = 1
        for i in range(len(self.step_classes)):
            # The multiplying is here on purpose. Because all of the entries of the whole panel, i.e., magnitude, phase files
            # have to have a non zero number of files. If just one has a zero found files, then something is not right/
            print(
                "ttttttttttttttttttttttttttttt len fmaps",
                len(self.get_widget_by_id(self.id + "_" + str(i)).pattern_match_results["files"]),
            )
            number_of_field_map_files *= len(self.get_widget_by_id(self.id + "_" + str(i)).pattern_match_results["files"])
        return number_of_field_map_files

    # @on(Button.Pressed, "#edit_button2")
    # def _on_edit_button_pressed(self):
    # """Remove the file pattern item."""


#      self.app.push_screen(SetEchoTimeDifferenceModal(), self.update_echo_time)


class DataSummaryLine(Widget):
    """
    Widget that displays a summary of data input, showing the number of files found. This applies only for the BIDS file type.
    """

    def __init__(self, summary=None, **kwargs) -> None:
        """
        Parameters
        ----------
        summary : dict or None, optional
            A dictionary containing the summary message and list of files. If None, a default summary is used.
        **kwargs : dict
        """
        super().__init__(**kwargs)
        self.summary = {"message": "Found 0 files.", "files": []} if summary is None else summary

    def compose(self) -> ComposeResult:
        """
        Yields
        ------
        Horizontal
            A horizontal container with the summary message and a button to show the files.
        """
        yield Horizontal(
            Static(self.summary["message"], id="feedback"),
            Button("👁", id="show_button", classes="icon_buttons"),
            classes="feedback_container",
        )

    def update_summary(self, summary):
        """
        Updates the summary information displayed in the widget.

        Parameters
        ----------
        summary : dict
            A dictionary containing the updated summary message and list of files.
        """
        self.summary = summary
        self.get_widget_by_id("feedback").update(self.summary["message"])
        if len(self.summary["files"]) > 0:
            self.styles.border = ("solid", "green")

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        """Displays a list of files in a modal dialog."""
        self.app.push_screen(ListOfFiles(self.summary))


class DataInput(Widget):
    """
    Widget that manages the input of data, including BIDS and non-BIDS data formats.
    Nested in a tab in the main widget.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        #  self._id_counter = 0
        self.callback_message = ""
        """ These counters are used to create a unique widget ids. These ids are then used in the ctx.cache. If some pattern
        widget is deleted, this id is used to delete it also from the cache. So it maps widget to the made selections which
        are cached in the ctx.cache.
        """
        self.t1_file_pattern_counter = 0
        self.bold_file_pattern_counter = 0
        self.field_map_file_pattern_counter = 0
        self.association_done = False

    def compose(self) -> ComposeResult:
        """Switch in between the BIDS and non BIDS widgets."""
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
        """ If BIDS is ON: """
        yield Grid(
            FileBrowserForBIDS(path_to="INPUT DATA DIRECTORY", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        """ This shows files found automatically when path to a BIDS folder is selected. """
        yield Vertical(
            DataSummaryLine(id="feedback_anat"),
            DataSummaryLine(id="feedback_bold"),
            DataSummaryLine(id="feedback_fmap"),
            id="bids_summary_panel",
            classes="components",
        )
        """ If non-BIDS is ON: """
        with VerticalScroll(id="non_bids_panel", classes="components"):
            """ Some instructions at the beginning. """
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
            """ For anatomical/structural (T1) file patterns. """
            yield VerticalScroll(Button("Add", id="add_t1_image_button"), id="t1_image_panel", classes="non_bids_panels")
            """ For functional (BOLDS) file patterns. """
            yield VerticalScroll(Button("Add", id="add_bold_image_button"), id="bold_image_panel", classes="non_bids_panels")
            """ For fields map (magnitude, phase,...) file patterns. """
            yield VerticalScroll(
                Horizontal(
                    Button("Add", id="add_field_map_button"),
                    Button("Associate", id="associate_button"),
                    Button("Info", id="info_field_maps_button"),
                    id="field_maps_button_panel",
                ),
                id="field_map_panel",
                classes="non_bids_panels",
            )
            """ If all file patterns for non-BIDS are selected, user should confirm so that we can trigger the functional/field
                file matching and CheckBoldEffectiveEchoSpacingStep and CheckBoldPhaseEncodingDirectionStep.
                After this is done, any editing should be prohibited and the features and other remaining tabs should become
                visible.
            """
            yield VerticalScroll(
                Button("Confirm", id="confirm_field_map_button", variant="error"),
                id="confirm_button_container",
                classes="non_bids_panels",
            )

            # TODO: shift this to features
            # yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")

    def on_mount(self) -> None:
        """
        Sets up the initial state and titles for various panels after the widget is mounted.
        """
        self.get_widget_by_id("instructions").border_title = "Data format"
        self.get_widget_by_id("bids_panel").border_title = "Path to BIDS directory"
        self.get_widget_by_id("bids_summary_panel").border_title = "Data input file summary"

        self.get_widget_by_id("non_bids_panel").border_title = "Path pattern setup"

        self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        self.get_widget_by_id("t1_image_panel").border_title = "T1-weighted image file pattern"
        self.get_widget_by_id("bold_image_panel").border_title = "BOLD image files patterns"
        # self.get_widget_by_id("event_file_panel").border_title = "Event files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"
        self.get_widget_by_id("associate_button").styles.visibility = "hidden"
        self.get_widget_by_id("info_field_maps_button").styles.visibility = "hidden"

    @on(Button.Pressed, "#add_t1_image_button")
    def _add_t1_image(self):
        self.get_widget_by_id("t1_image_panel").mount(
            FileItem(
                id="t1_file_pattern_" + str(self.t1_file_pattern_counter), classes="file_patterns", pattern_class=AnatStep()
            )
        )
        self.t1_file_pattern_counter += 1
        self.refresh()

    @on(Button.Pressed, "#add_bold_image_button")
    def _add_bold_image(self):
        self.get_widget_by_id("bold_image_panel").mount(
            FileItem(
                id="bold_file_pattern_" + str(self.bold_file_pattern_counter),
                classes="file_patterns",
                pattern_class=BoldStep(app=self.app),
            )
        )
        self.bold_file_pattern_counter += 1
        self.refresh()

    @on(Button.Pressed, "#add_field_map_button")
    def _add_field_map_file(self):
        def branch_field_maps(fmap_type):
            if fmap_type == "siemens":
                self.show_additional_buttons_in_field_map_panel()
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
                self.show_additional_buttons_in_field_map_panel()
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
                    FieldMapFilesPanel(
                        field_map_type=fmap_type,
                        step_classes=[EPIStep()],
                        id="field_map_file_pattern_" + str(self.field_map_file_pattern_counter),
                    )
                )
                self.field_map_file_pattern_counter += 1
                self.refresh()
            # self.get_widget_by_id('field_maps_button_panel').mount()

        # mount new buttons after adding the field map

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

    def show_additional_buttons_in_field_map_panel(self):
        self.get_widget_by_id("associate_button").styles.visibility = "visible"
        self.get_widget_by_id("info_field_maps_button").styles.visibility = "visible"

    def callback_func(self, message_dict):
        info_string = ""
        for key in message_dict:
            info_string += key + ": " + " ".join(message_dict[key]) + "\n"
        self.callback_message = info_string

    @on(Button.Pressed, "#confirm_field_map_button")
    def _confirm_field_map_button(self):
        number_of_t1_files = 0
        number_of_bold_files = 0
        number_of_field_map_files = 0
        index_list = pd.DataFrame.from_dict(ctx.cache)
        print("lllllllllllllllllllllll", index_list)

        if "files" in index_list.index:
            print("lllllllllllllllllllllll", index_list.loc["files",].index)
            for widget_id in list(pd.DataFrame.from_dict(ctx.cache).loc["files",].index):
                if widget_id.startswith("t1_file_pattern_"):
                    # for i in range(self.t1_file_pattern_counter):
                    print("iiiiiii")
                    number_of_t1_files += len(
                        self.get_widget_by_id("t1_image_panel").get_widget_by_id(widget_id).pattern_match_results["files"]
                    )
                if widget_id.startswith("bold_file_pattern_"):
                    #    for i in range(self.bold_file_pattern_counter):
                    number_of_bold_files += len(
                        self.get_widget_by_id("bold_image_panel").get_widget_by_id(widget_id).pattern_match_results["files"]
                    )
                if widget_id.startswith("field_map_file_pattern_"):
                    # for i in range(self.field_map_file_pattern_counter):
                    number_of_field_map_files += self.get_widget_by_id(widget_id).get_number_of_found_files()
                    print(self.get_widget_by_id(widget_id).get_number_of_found_files())

        warning_string = ""
        if any(value == 0 for value in [number_of_t1_files, number_of_bold_files, number_of_field_map_files]):
            if number_of_t1_files == 0:
                warning_string += "No t1 files found! Check or add the t1 file pattern!\n"
            if number_of_bold_files == 0:
                warning_string += "No bold files found! Check or add the bold file pattern!\n"
            if number_of_field_map_files == 0:
                warning_string += "No field map files found! Check or add the field map file pattern!"
            self.app.push_screen(
                Confirm(
                    warning_string,
                    left_button_text=False,
                    right_button_text="OK",
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Missing files",
                    id="missing_files_modal",
                    classes="confirm_warning",
                )
            )
        if self.association_done is False:
            self.app.push_screen(
                Confirm(
                    "Check for field map association! Button 'Associate'",
                    left_button_text=False,
                    right_button_text="OK",
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Check association",
                    id="association_modal",
                    classes="confirm_warning",
                )
            )
        else:
            self.app.flags_to_show_tabs["from_input_data_tab"] = True
            self.app.show_hidden_tabs()

    @on(Button.Pressed, "#associate_button")
    def _on_associate_button_pressed(self):
        acq_to_task_mapping_step_instance = AcqToTaskMappingStep(app=self.app, callback=self.callback_func)
        acq_to_task_mapping_step_instance.run()
        self.association_done = True

    @on(Button.Pressed, "#info_field_maps_button")
    def _on_info_button_pressed(self):
        """Shows a modal with the list of files found using the given pattern."""
        print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiii", self.callback_message)
        self.app.push_screen(SimpleMessageModal(self.callback_message, title="Meta information"))

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
                    field_map_type=field_map_type,
                    step_classes=step_classes,
                    id="field_map_file_pattern_" + str(self.field_map_file_pattern_counter),
                )
            )
            self.field_map_file_pattern_counter += 1
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
        ctx.cache["bids"]["files"] = message.selected_path
        self.feed_contex_and_extract_available_images()

        # def confirmation(respond: bool):
        # print("bla")
        # if ~respond:
        # self.mount(
        # PathPatternBuilder(
        # path="/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz", classes="components"
        # )
        # )

    #   ctx.put(BidsFileSchema().load({"datatype": "bids", "path": message.selected_path}))
    #  self.feed_contex_and_extract_available_images(message.selected_path)
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

    def feed_contex_and_extract_available_images(self):
        """Feed the Context object with the path to the data fields and extract available images."""

        #  def on_dismiss_this_modal(value):
        #     self.get_widget_by_id("data_input_file_browser").update_input(None)

        # if len(file_path) > 0:
        #  ctx.put(BidsFileSchema().load({"datatype": "bids", "path": file_path}))

        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = ctx.database.get(**bold_filedict)

        # print("bbbbbbbbbbbbbbbbbbbbbbbbbbbb", file_path, filepaths)
        # self.filepaths = list(filepaths)
        # if len(self.filepaths) > 0:

        db_entities, db_tags_set = ctx.database.multitagvalset(entities, filepaths=filepaths)
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
        # else:
        # # self.app.push_screen(
        # # FalseInputWarning(
        # # warning_message="The selected data directory seems not be a BIDS directory!",
        # # title="Error - Non a bids directory",
        # # id="not_bids_dir_warning_modal",
        # # classes="error_modal",
        # # ),
        # # on_dismiss_this_modal,
        # # )
        # self.app.push_screen(
        # Confirm(
        # "The selected data directory seems not be a BIDS directory!",
        # title="Error - Non a bids directory",
        # left_button_text=False,
        # right_button_text="OK",
        # id="not_bids_dir_warning_modal",
        # classes="confirm_error",
        # )
        # )

    def manually_change_label(self, label):
        """If the input data folder was set by reading an existing json file via the working directory widget,
        the label must be changed externally. This is done in the most top base.
        """
        self.get_widget_by_id("data_input_file_browser").update_input(label)
