# -*- coding: utf-8 -*-

from typing import List

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static, Switch

from ..utils.confirm_screen import Confirm, SimpleMessageModal
from ..utils.context import ctx
from ..utils.custom_switch import TextSwitch
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
from ..utils.filebrowser import FileBrowser, FileBrowserForBIDS
from ..utils.list_of_files_modal import ListOfFiles
from ..utils.meta_data_steps import AcqToTaskMappingStep
from ..utils.non_bids_file_itemization import FileItem
from ..utils.selection_modal import DoubleSelectionModal, SelectionModal
from ..utils.summary_steps import AnatSummaryStep, BoldSummaryStep, FmapSummaryStep


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
        self, step_classes: list, field_map_type: str = "siemens", id: str | None = None, classes: str | None = None
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.field_map_type = field_map_type
        self.field_map_types_dict = {
            "epi": "EPI (blip-up blip-down)",
            "siemens": "Phase difference and magnitude (used by Siemens scanners)",
            "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
        }
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
            if self.id + "_" + str(i) in ctx.cache:
                ctx.cache.pop(self.id + "_" + str(i))

    @on(FileItem.SuccessChanged)
    def _on_file_item_success_changed(self, message: Message):
        """Change widget border from green if files were successfully found, to red if no."""
        success_list = []
        for i in range(len(self.step_classes)):
            success_list.append(self.get_widget_by_id(self.id + "_" + str(i)).success_value)
        if all(success_list) is True:
            self.query(".{}_panel".format(self.field_map_type)).last(Vertical).styles.border = ("thick", "green")
        else:
            self.query(".{}_panel".format(self.field_map_type)).last(Vertical).styles.border = ("thick", "red")


class DataSummaryLine(Widget):
    """
    Widget that displays a summary of data input, showing the number of files found. This applies only for the BIDS file type.
    """

    def __init__(self, summary: dict | None = None, id: str | None = None, classes: str | None = None) -> None:
        """
        Parameters
        ----------
        summary : dict or None, optional
            A dictionary containing the summary message and list of files. If None, a default summary is used.
        **kwargs : dict
        """
        super().__init__(id=id, classes=classes)
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
        Updates the summary information displayed in the widget. Used exteranaly.

        Parameters
        ----------
        summary : dict
            A dictionary containing the updated summary message and list of files.
        """
        self.summary = summary
        self.get_widget_by_id("feedback").update(self.summary["message"])
        # if there were some found files, then change border to green
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

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        # Use the following variable to catch outputs of the meta and summary steps.
        self.callback_message = ""
        """ These counters are used to create a unique widget ids. These ids are then used in the ctx.cache. If some pattern
        widget is deleted, this id is used to delete it also from the cache. So it maps widget to the made selections which
        are cached in the ctx.cache.
        """
        self.t1_file_pattern_counter = 0
        self.bold_file_pattern_counter = 0
        self.field_map_file_pattern_counter = 0
        # Flag whether the association of the field maps was done or no.
        self.association_done = False

    def callback_func(self, message_dict):
        info_string = Text("")
        for key in message_dict:
            # print("kkkkkkkkkkkkk", message_dict[key], key)
            # if there is only one item, we do not separate items on new lines
            # print("lllllllllllllllllllllllllll len(message_dict[key])", len(message_dict[key]))
            if len(message_dict[key]) <= 1:
                # print(
                #     "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii am i here?",
                #     (len(key) + len(message_dict[key]) + 3),
                #     len(key),
                #     len(message_dict[key]),
                # )
                sep_char = ""
                separ_line = "-" * (len(key) + len(message_dict[key][0]) + 3)
            else:
                sep_char = "\n"
                separ_line = "-" * (max([len(s) for s in [key] + message_dict[key]]) + 3)
            info_string += Text(key + ": " + sep_char, style="bold green") + Text(
                " ".join(message_dict[key]) + separ_line + "\n", style="white"
            )

        self.callback_message = info_string

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
        self.get_widget_by_id("t1_image_panel").border_title = "T1-weighted image file pattern"
        self.get_widget_by_id("bold_image_panel").border_title = "BOLD image files patterns"
        self.get_widget_by_id("field_map_panel").border_title = "Field maps"
        self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        self.get_widget_by_id("associate_button").styles.visibility = "hidden"
        self.get_widget_by_id("info_field_maps_button").styles.visibility = "hidden"

    @on(Button.Pressed, "#add_t1_image_button")
    async def _on_button_add_t1_image_button_pressed(self):
        await self.add_t1_image(load_object=None)

    async def add_t1_image(self, pattern_class=True, load_object=None, message_dict=None):
        pattern_class = AnatStep(app=self.app) if pattern_class is True else None
        await self.get_widget_by_id("t1_image_panel").mount(
            FileItem(
                id="t1_file_pattern_" + str(self.t1_file_pattern_counter),
                classes="file_patterns",
                pattern_class=pattern_class,
                load_object=load_object,
                message_dict=message_dict,
            )
        )
        self.t1_file_pattern_counter += 1
        return ("t1_file_pattern_" + str(self.t1_file_pattern_counter),)

    @on(Button.Pressed, "#add_bold_image_button")
    async def _on_button_add_bold_image_button(self):
        await self.add_bold_image(load_object=None)

    async def add_bold_image(self, pattern_class=True, load_object=None, message_dict=None):
        pattern_class = BoldStep(app=self.app) if pattern_class is True else None
        await self.get_widget_by_id("bold_image_panel").mount(
            FileItem(
                id="bold_file_pattern_" + str(self.bold_file_pattern_counter),
                classes="file_patterns",
                pattern_class=pattern_class,
                load_object=load_object,
                message_dict=message_dict,
            )
        )
        self.bold_file_pattern_counter += 1
        return "bold_file_pattern_" + str(self.bold_file_pattern_counter)

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

        # actual start of the function, push modal to select the field map type and the mount appropriate FieldMapFilesPanel
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
        )

    def show_additional_buttons_in_field_map_panel(self):
        # show new buttons after adding the field map
        self.get_widget_by_id("associate_button").styles.visibility = "visible"
        self.get_widget_by_id("info_field_maps_button").styles.visibility = "visible"

    def _mount_field_item_group(self, field_map_user_choices: list | str):
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

    @work
    @on(Button.Pressed, "#confirm_field_map_button")
    async def _confirm_field_map_button(self):
        """This function makes checks on the user input non-bids files. If the mandatory T1 and bold files are present,
        then the hidden tabs with features and etc. are made visible. This is done by looping over the panels and walking
        their children, in particular, the FileItem widgets which contains the needed information about the number of found
        files.
        """
        number_of_t1_files = []
        number_of_bold_files = []
        number_of_field_map_files = []
        for widget in self.get_widget_by_id("t1_image_panel").walk_children(FileItem):
            number_of_t1_files.append(len(widget.pattern_match_results["files"]))
        for widget in self.get_widget_by_id("bold_image_panel").walk_children(FileItem):
            number_of_bold_files.append(len(widget.pattern_match_results["files"]))
        for widget in self.get_widget_by_id("field_map_panel").walk_children(FieldMapFilesPanel):
            for sub_widget in widget.walk_children(FileItem):
                number_of_field_map_files.append(len(sub_widget.pattern_match_results["files"]))

        warning_string = ""
        if any(value == 0 for value in number_of_t1_files) or not number_of_t1_files:
            warning_string += "No t1 files found! Check or add the t1 file pattern!\n"
        if any(value == 0 for value in number_of_bold_files) or not number_of_bold_files:
            warning_string += "No bold files found! Check or add the bold file pattern!\n"
        # Fields map are not mandatory, so this does not go to the warning string.
        # if any(value == 0 for value in number_of_field_map_files) or not number_of_field_map_files:
        #     warning_string += "No field map files found! Check or add the field map file pattern!"
        # If the are field maps and the association was needed but was not done
        if self.association_done is False and any(value != 0 for value in number_of_field_map_files):
            await self.app.push_screen_wait(
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
        if warning_string != "":
            await self.app.push_screen_wait(
                Confirm(
                    warning_string,
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Missing files",
                    id="missing_files_modal",
                    classes="confirm_warning",
                )
            )
        else:
            # refresh available images so that the feature tab can use them
            ctx.refresh_available_images()
            # make hidden tabs visible
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
        self.app.push_screen(SimpleMessageModal(self.callback_message, title="Meta information"))

    @on(Switch.Changed)
    def on_switch_changed(self, message: Message):
        """Bids/Non-bids switch"""
        self.toggle_bids_non_bids_format(message.value)

    def toggle_bids_non_bids_format(self, value: bool):
        """Bids/Non-bids switch function"""
        if value:
            self.app.is_bids = True
            self.get_widget_by_id("bids_panel").styles.visibility = "visible"
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "visible"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "hidden"
        else:
            self.app.is_bids = False
            self.get_widget_by_id("bids_panel").styles.visibility = "hidden"
            self.get_widget_by_id("bids_summary_panel").styles.visibility = "hidden"
            self.get_widget_by_id("non_bids_panel").styles.visibility = "visible"

    @on(FileBrowser.Changed)
    def _on_file_browser_changed(self, message: Message):
        """Trigger the data read by the Context after a file path is selected (in bids case)."""
        ctx.cache["bids"]["files"] = message.selected_path
        self.app.flags_to_show_tabs["from_input_data_tab"] = True
        self.app.show_hidden_tabs()
        self.update_summaries()

    def update_summaries(self):
        """Updates summary information and show hidden tabs (in bids case)."""
        # tab_manager_widget = self.app.get_widget_by_id("tabs_manager")

        anat_summary_step = AnatSummaryStep()
        bold_summary_step = BoldSummaryStep()
        fmap_summary_step = FmapSummaryStep()

        self.get_widget_by_id("feedback_anat").update_summary(anat_summary_step.get_summary)
        self.get_widget_by_id("feedback_bold").update_summary(bold_summary_step.get_summary)
        self.get_widget_by_id("feedback_fmap").update_summary(fmap_summary_step.get_summary)

        # at this point, all went well, change border from red to green
        self.get_widget_by_id("data_input_file_browser").styles.border = ("solid", "green")
