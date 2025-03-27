# -*- coding: utf-8 -*-

from typing import List

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static, Switch

from ...model.file.bids import BidsFileSchema
from ..data_analyzers.context import ctx
from ..data_analyzers.file_pattern_steps import (
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
from ..data_analyzers.meta_data_steps import AcqToTaskMappingStep
from ..data_analyzers.summary_steps import AnatSummaryStep, BoldSummaryStep, FmapSummaryStep
from ..general_widgets.custom_switch import TextSwitch
from ..general_widgets.selection_modal import DoubleSelectionModal, SelectionModal
from ..specialized_widgets.confirm_screen import Confirm, SimpleMessageModal
from ..specialized_widgets.filebrowser import FileBrowser, FileBrowserForBIDS
from ..specialized_widgets.non_bids_file_itemization import FileItem
from .utils.extra_widgets import DataSummaryLine, FieldMapFilesPanel


class DataInput(Widget):
    """
    A widget for handling data input, supporting both BIDS and non-BIDS data formats.

    This widget provides a user interface for specifying the location of
    neuroimaging data, either in BIDS format or using custom file patterns.
    It handles the selection of anatomical (T1-weighted), functional (BOLD),
    and field map files, and provides feedback on the files found.

    Attributes
    ----------
    callback_message : str
        A variable to catch outputs of the meta and summary steps.
    t1_file_pattern_counter : int
        Used to create unique widget IDs for T1 file patterns.
    bold_file_pattern_counter : int
        Used to create unique widget IDs for BOLD file patterns.
    field_map_file_pattern_counter : int
        Used to create unique widget IDs for field map file patterns.
    association_done : bool
        Flag indicating whether the association of the field maps was done or not.
    """

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the DataInput widget.

        Parameters
        ----------
        id : str, optional
            The ID of the widget, by default None.
        classes : str, optional
            CSS classes for the widget, by default None.
        """
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
        # We need this flag to check before loading whether there was no previous data load already.
        # If so, the we need to reload some widget and refresh context cache and database.
        self.data_load_sucess = False

    def callback_func(self, message_dict: dict[str, list[str]]) -> None:
        """
        Processes a dictionary of messages and updates the callback_message with formatted text.

        This method takes a dictionary of messages, formats them into a
        human-readable string, and stores the result in the `callback_message`
        attribute.

        Parameters
        ----------
        message_dict : dict[str, list[str]]
            A dictionary where keys are message categories and values are lists of messages.
        """
        info_string = Text("")
        for key in message_dict:
            # if there is only one item, we do not separate items on new lines
            if len(message_dict[key]) <= 1:
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
        """
        Composes the structure of the widget, switching between BIDS and non-BIDS formats.

        This method defines the layout and components of the DataInput widget,
        including the switch between BIDS and non-BIDS formats, file browsers,
        summary panels, and buttons for adding file patterns.

        Yields
        ------
        ComposeResult
            The composed widgets for data input.
        """
        # First we define widgets (panels) in order to be able later put titles on them
        """Switch in between the BIDS and non BIDS widgets."""
        instructions_panel = Container(
            Static(
                "If 'on' then just select the BIDS top directory. Otherwise you must select file patterns\
for T1-weighted image, BOLD image and event files.",
                id="description",
            ),
            Horizontal(
                Static("Data in BIDS format", id="bids_format_switch", classes="label"),
                TextSwitch(id="bids_non_bids_switch", value=True),
                #        classes="components",
            ),
            id="instructions",
            classes="components",
        )
        """ If BIDS is ON: """
        bids_panel = Grid(
            FileBrowserForBIDS(path_to="INPUT DATA DIRECTORY", id="data_input_file_browser"),
            id="bids_panel",
            classes="components",
        )
        """ This shows files found automatically when path to a BIDS folder is selected. """
        bids_summary_panel = Vertical(
            DataSummaryLine(id="feedback_anat"),
            DataSummaryLine(id="feedback_bold"),
            DataSummaryLine(id="feedback_fmap"),
            id="bids_summary_panel",
            classes="components",
        )
        """ If non-BIDS is ON: """
        # """ For anatomical/structural (T1) file patterns. """
        t1_image_panel = VerticalScroll(
            Button("Add", id="add_t1_image_button"), id="t1_image_panel", classes="non_bids_panels"
        )
        # """ For functional (BOLDS) file patterns. """
        bold_image_panel = VerticalScroll(
            Button("Add", id="add_bold_image_button"), id="bold_image_panel", classes="non_bids_panels"
        )
        # """ For fields map (magnitude, phase,...) file patterns. """
        associate_button = Button("Associate", id="associate_button")
        info_field_maps_button = Button("Info", id="info_field_maps_button")
        field_map_panel = VerticalScroll(
            Horizontal(
                Button("Add", id="add_field_map_button"),
                associate_button,
                info_field_maps_button,
                id="field_maps_button_panel",
            ),
            id="field_map_panel",
            classes="non_bids_panels",
        )
        non_bids_panel = VerticalScroll(
            # """ Some instructions at the beginning. """
            Static(
                "For each file type you need to create a 'path pattern' based on which all files of the particular type will \
be queried. In the pop-up window, choose one particular file (use browse, or copy-paste) and highlight parts \
of the string to be replaced by wildcards. You can also use type hints by starting typing '{' in front of the substring.",
                id="help_top",
            ),
            Static("Example: We have a particular T1 file and highlight parts with '0001' which represents subjects."),
            Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz",
                    spans=[(35, 39, "on red"), (49, 53, "on red")],
                ),
                classes="examples",
            ),
            Static("After submitting the highlighted parts will be replaced with a particular wildcard type"),
            Static(
                Text(
                    "/home/tomas/github/ds002785_v2/sub-{subject}/anat/sub-{subject}_T1w.nii.gz",
                    spans=[(35, 44, "on red"), (54, 63, "on red")],
                ),
                classes="examples",
            ),
            t1_image_panel,
            bold_image_panel,
            field_map_panel,
            # """ If all file patterns for non-BIDS are selected, user should confirm so that we can trigger the
            #     functional/field file matching and CheckBoldEffectiveEchoSpacingStep and CheckBoldPhaseEncodingDirectionStep.
            #     After this is done, any editing should be prohibited and the features and other remaining tabs should become
            #     visible.
            # """
            VerticalScroll(
                Button("Confirm", id="confirm_non_bids_button", variant="error"),
                id="confirm_button_container",
                classes="non_bids_panels",
            ),
            id="non_bids_panel",
            classes="components",
        )

        """
        Sets up the initial state and titles for various panels after the widget is mounted.
        """
        instructions_panel.border_title = "Data format"
        bids_panel.border_title = "Path to BIDS directory"
        bids_summary_panel.border_title = "Data input file summary"
        non_bids_panel.border_title = "Path pattern setup"
        t1_image_panel.border_title = "T1-weighted image file pattern"
        bold_image_panel.border_title = "BOLD image files patterns"
        field_map_panel.border_title = "Field maps"
        non_bids_panel.styles.visibility = "hidden"
        associate_button.styles.visibility = "hidden"
        info_field_maps_button.styles.visibility = "hidden"

        # now populate the generator
        yield instructions_panel
        yield bids_panel
        yield bids_summary_panel
        yield non_bids_panel

    @on(Button.Pressed, "#add_t1_image_button")
    async def _on_button_add_t1_image_button_pressed(self) -> None:
        """
        Handles the event when the "Add" button for T1 images is pressed.

        This method adds a new FileItem widget for specifying a T1 image file pattern.
        """
        if self.data_load_sucess is False:
            await self.add_t1_image(load_object=None)
        else:
            self.forbid_data_change()

    async def add_t1_image(self, load_object=None, message_dict=None, execute_pattern_class_on_mount=True) -> str:
        """
        Adds a FileItem widget for specifying a T1 image file pattern.

        Parameters
        ----------
        load_object : Any, optional
            An object to load into the FileItem, by default None.
        message_dict : dict[str, list[str]], optional
            A dictionary of messages for the FileItem, by default None.
        execute_pattern_class_on_mount : bool, optional
            Whether to execute the pattern class on mount, by default True.

        Returns
        -------
        str
            A tuple containing the ID of the newly added FileItem widget.
        """
        await self.get_widget_by_id("t1_image_panel").mount(
            FileItem(
                id="t1_file_pattern_" + str(self.t1_file_pattern_counter),
                classes="file_patterns",
                pattern_class=AnatStep(app=self.app),
                load_object=load_object,
                message_dict=message_dict,
                execute_pattern_class_on_mount=execute_pattern_class_on_mount,
            )
        )
        self.t1_file_pattern_counter += 1
        return "t1_file_pattern_" + str(self.t1_file_pattern_counter)

    @on(Button.Pressed, "#add_bold_image_button")
    async def _on_button_add_bold_image_button(self) -> None:
        """
        Handles the event when the "Add" button for BOLD images is pressed.

        This method adds a new FileItem widget for specifying a BOLD image file pattern.
        """
        if self.data_load_sucess is False:
            await self.add_bold_image(load_object=None)
        else:
            self.forbid_data_change()

    async def add_bold_image(self, load_object=None, message_dict=None, execute_pattern_class_on_mount=True) -> str:
        """
        Adds a FileItem widget for specifying a BOLD image file pattern.

        Parameters
        ----------
        load_object : Any, optional
            An object to load into the FileItem, by default None.
        message_dict : dict[str, list[str]], optional
            A dictionary of messages for the FileItem, by default None.
        execute_pattern_class_on_mount : bool, optional
            Whether to execute the pattern class on mount, by default True.

        Returns
        -------
        str
            The ID of the newly added FileItem widget.
        """
        await self.get_widget_by_id("bold_image_panel").mount(
            FileItem(
                id="bold_file_pattern_" + str(self.bold_file_pattern_counter),
                classes="file_patterns",
                pattern_class=BoldStep(app=self.app),
                load_object=load_object,
                message_dict=message_dict,
                execute_pattern_class_on_mount=execute_pattern_class_on_mount,
            )
        )
        self.bold_file_pattern_counter += 1
        return "bold_file_pattern_" + str(self.bold_file_pattern_counter)

    @on(Button.Pressed, "#add_field_map_button")
    def _add_field_map_file(self):
        """
         Handles the event when the "Add" button for field map files is pressed.

        This method presents a modal to select the type of field map and then
         mounts the appropriate FieldMapFilesPanel. It supports three types of
         field maps: EPI, Siemens, and Philips. Depending on the selected type,
         it may present additional modals to specify the number and type of
         magnitude and phase images.
        """

        def branch_field_maps(fmap_type):
            """
            Branches the field map setup based on the selected field map type.

            This function determines the appropriate steps to take based on the
            selected field map type. For Siemens and Philips field maps, it
            presents additional modals to specify the type of magnitude and
            phase images. For EPI field maps, it directly mounts the
            FieldMapFilesPanel.

            Parameters
            ----------
            fmap_type : str
                The type of field map selected by the user.
            """
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
        """
        Shows additional buttons in the field map panel.

        This method makes the "Associate" and "Info" buttons visible in the
        field map panel after a field map type has been selected.
        """
        # show new buttons after adding the field map
        self.get_widget_by_id("associate_button").styles.visibility = "visible"
        self.get_widget_by_id("info_field_maps_button").styles.visibility = "visible"

    def _mount_field_item_group(self, field_map_user_choices: list | str):
        """
        Mounts a group of FileItem widgets for field map files based on user choices.

        This method mounts the appropriate FieldMapFilesPanel with the correct
        FileItem widgets based on the user's selection of magnitude and phase
        image types.

        Parameters
        ----------
        field_map_user_choices : list | str
            The user's choices for magnitude and phase image types.
            It can be a list of strings (for Siemens) or a single string (for Philips).
        """
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
    @on(Button.Pressed, "#confirm_non_bids_button")
    async def _confirm_non_bids_button(self):
        """
        Validates non-BIDS file patterns and prepares for the next steps.

        This function checks if the mandatory T1 and BOLD files are present
        based on the user-defined file patterns. If the required files are
        found, it makes the hidden tabs (features, etc.) visible. It also
        checks if field maps are present and if their association with BOLD
        files has been performed. If there are issues, it displays warning
        messages to the user.
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
            self.data_input_sucess()
            self.app.flags_to_show_tabs["from_input_data_tab"] = True
            self.app.show_hidden_tabs()

    @on(Button.Pressed, "#associate_button")
    def _on_associate_button_pressed(self):
        """
        Handles the event when the "Associate" button is pressed.

        This method initiates the association of field map files to BOLD
        files by creating and running an instance of the
        `AcqToTaskMappingStep`. It also sets the `association_done` flag to
        True to indicate that the association process has been started.
        """
        acq_to_task_mapping_step_instance = AcqToTaskMappingStep(app=self.app, callback=self.callback_func)
        acq_to_task_mapping_step_instance.run()
        self.association_done = True

    @on(Button.Pressed, "#info_field_maps_button")
    def _on_info_button_pressed(self):
        """
        Handles the event when the "Info" button is pressed.

        This method displays a modal dialog containing meta information about
        the field map files. The information is retrieved from the
        `callback_message` attribute.
        """
        self.app.push_screen(SimpleMessageModal(self.callback_message, title="Meta information"))

    @on(Switch.Changed)
    def on_switch_changed(self, message: Message):
        """
        Handles the event when the BIDS/non-BIDS switch is toggled.

        This method is triggered when the state of the BIDS/non-BIDS switch
        changes. It calls the `toggle_bids_non_bids_format` method to update
        the UI based on the new switch value.

        Parameters
        ----------
        message : Message
            The message object containing information about the switch change.
        """
        if self.data_load_sucess is False:
            self.toggle_bids_non_bids_format(message.value)
        else:
            self.forbid_data_change()

    def toggle_bids_non_bids_format(self, value: bool):
        """
        Toggles the visibility of BIDS and non-BIDS UI elements.

        This method updates the visibility of the UI elements based on
        whether BIDS or non-BIDS format is selected.

        Parameters
        ----------
        value : bool
            True if BIDS format is selected, False if non-BIDS is selected.
        """
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
    async def _on_file_browser_changed(self, message: Message):
        """
        Handles the event when the file browser selection changes (BIDS case).

        This method is triggered when the user selects a new path in the file
        browser. It updates the context cache with the selected path, sets
        flags to show the hidden tabs, and updates the data summaries.

        Parameters
        ----------
        message : Message
            The message object containing information about the file browser change.
        """
        if self.data_load_sucess is False:
            ctx.cache["bids"]["files"] = message.selected_path
            ctx.put(BidsFileSchema().load({"datatype": "bids", "path": message.selected_path}))
            ctx.refresh_available_images()

            self.app.flags_to_show_tabs["from_input_data_tab"] = True
            self.app.show_hidden_tabs()
            self.update_summaries()
            self.data_input_sucess()
        else:
            # we need to update this back
            self.get_widget_by_id("data_input_file_browser").get_widget_by_id("path_input_box").update(
                ctx.cache["bids"]["files"]
            )
            self.forbid_data_change()

    def update_summaries(self):
        """
        Updates the summary information for anatomical, BOLD, and field map files.

        This method creates instances of `AnatSummaryStep`, `BoldSummaryStep`,
        and `FmapSummaryStep` to generate summary information about the
        selected files. It then updates the corresponding `DataSummaryLine`
        widgets with the new summary data. Finally, it changes the border
        color of the file browser to green to indicate success.
        """

        anat_summary_step = AnatSummaryStep()
        bold_summary_step = BoldSummaryStep()
        fmap_summary_step = FmapSummaryStep()

        self.get_widget_by_id("feedback_anat").update_summary(anat_summary_step.get_summary)
        self.get_widget_by_id("feedback_bold").update_summary(bold_summary_step.get_summary)
        self.get_widget_by_id("feedback_fmap").update_summary(fmap_summary_step.get_summary)

        # at this point, all went well, change border from red to green
        self.get_widget_by_id("data_input_file_browser").styles.border = ("solid", "green")

    @work(exclusive=True, name="data_input_sucess_modal_worker")
    async def data_input_sucess(self):
        """
        Displays a success message after data input is validated.

        This method shows a modal dialog to inform the user that the data
        files have been successfully loaded, either in BIDS or non-BIDS
        format. It also provides instructions on how to proceed to the
        next steps in the pipeline.
        """

        self.data_load_sucess = True
        await self.app.push_screen_wait(
            Confirm(
                "Data files successfully loaded! Proceed to the next tabs:\n\n\
➡️  General preprocessing settings ⬅️\n\
➡️             Features            ⬅️\n\
➡️        Group level models       ⬅️\n\
➡️           Check and run         ⬅️",
                left_button_text=False,
                right_button_text="OK",
                right_button_variant="default",
                title="Data input success",
                id="data_input_sucess",
                classes="confirm_success",
            )
        )

        if ctx.workdir is None:
            await self.app.push_screen_wait(
                Confirm(
                    "Go back to Work dir tab and set the working directory!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Missing work directory",
                    id="missing_workdir",
                    classes="confirm_warning",
                )
            )

    def forbid_data_change(self):
        self.app.push_screen(
            Confirm(
                r"The input data were already setup!\To change restart the UI.",
                left_button_text=False,
                right_button_text="OK",
                right_button_variant="default",
                title="Reload",
                id="reload",
                classes="confirm_warning",
            )
        )
