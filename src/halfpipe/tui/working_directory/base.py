# -*- coding: utf-8 -*-
# ok to review

import os
from pathlib import Path

from niworkflows.utils.misc import check_valid_fs_license
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static
from textual.worker import Worker, WorkerState

from ...model.spec import load_spec
from ...workdir import init_workdir
from ..data_analyzers.context import ctx
from ..help_functions import copy_and_rename_file
from ..load import cache_file_patterns, fill_ctx_spec, mount_features, mount_file_panels, mount_models
from ..specialized_widgets.confirm_screen import Confirm
from ..specialized_widgets.file_browser_modal import path_test_with_isfile_true
from ..specialized_widgets.filebrowser import FileBrowser


class WorkDirectory(Widget):
    """
    Manages the working directory selection and initialization for the application.

    This widget provides the user interface for selecting a working directory,
    which serves as the root for storing all output files and loading
    configurations from existing 'spec.json' files. It handles the
    interaction with the file browser, validation of the selected directory,
    and the loading or overriding of existing configurations.

    Attributes
    ----------
    existing_spec : Spec | None
        The loaded specification object from 'spec.json', or None if no
        specification file is found.
    data_input_success : bool
        A flag indicating whether the data input process was successful.
    event_file_objects : list[File]
        A list of event file objects loaded from the specification.
    atlas_file_objects : list[File]
        A list of atlas file objects loaded from the specification.
    seed_map_file_objects : list[File]
        A list of seed map file objects loaded from the specification.
    spatial_map_file_objects : list[File]
        A list of spatial map file objects loaded from the specification.
    feature_widget : Widget
        The feature selection widget.
    model_widget : Widget
        The model selection widget.

    Methods
    -------
    compose()
        Composes the widgets for the working directory interface.
    _on_file_browser_changed(message)
        Handles file browser's changed event, including verifying selected directory and loading configuration
        from 'spec.json'.
    working_directory_override(override)
        Manages overriding an existing spec file, if one is found in the selected directory.
    existing_spec_file_decision(load)
        Manages user decision whether to load an existing spec file or override it.
    load_from_spec()
        Loads settings from 'spec.json' and updates the context cache.
    cache_file_patterns()
        Caches data from 'spec.json' into context and creates corresponding widgets.
    mount_features()
        Mounts feature selection widgets based on the spec file.
    on_worker_state_changed(event)
        Handles state change events for workers, progressing through stages of loading.
    mount_file_panels()
        Initializes file panels for various file types (events, atlas, seed, spatial maps).
    mount_models()
        Initializes the model selection widgets based on the spec file.
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the WorkDirectory widget.

        Parameters
        ----------
        id : str | None, optional
            Identifier for the widget, by default None.
        classes : str | None, optional
            Classes for CSS styling, by default None.
        """
        super().__init__(id=id, classes=classes)
        self.fs_license_file_found = False

    def compose(self) -> ComposeResult:
        """
        Composes the widgets for the working directory interface.

        This method creates the layout for the working directory selection,
        including a descriptive static text and a file browser.

        Returns
        -------
        ComposeResult
            The result of composing the child widgets.
        """
        work_directory = Vertical(
            Static(
                "Set path to the working directory. Here all output will be stored. By selecting a directory with existing \
spec.json file it is possible to load the therein configuration.",
                id="description",
            ),
            FileBrowser(path_to="WORKING DIRECTORY", id="work_dir_file_browser"),
            id="work_directory",
            classes="components",
        )
        freesurfer_directory = Vertical(
            Static(
                "Path to the freesurfer license. By default the path will be set to the working directory.", id="description"
            ),
            FileBrowser(
                path_to="FREESURFER LICENSE", path_test_function=path_test_with_isfile_true, id="fs_license_file_browser"
            ),
            id="fs_license_file_panel",
            classes="components",
        )
        work_directory.border_title = "Select working directory"
        freesurfer_directory.border_title = "Select freesurfer license directory"

        yield work_directory
        yield freesurfer_directory

    @on(FileBrowser.Changed, "#work_dir_file_browser")
    async def _on_work_dir_file_browser_changed(self, message: Message) -> None:
        try:
            init_workdir(message.selected_path)
            self._working_dir_path_passed(message.selected_path)
        except RuntimeError as e:
            await self.app.push_screen(
                Confirm(
                    f"{e}",
                    left_button_text=False,
                    right_button_text="OK",
                    title="Path Error",
                    classes="confirm_error",
                )
            )
            self.get_widget_by_id("work_dir_file_browser").update_input(None, send_message=False)
            self.get_widget_by_id("work_dir_file_browser").styles.border = ("solid", "red")
            ctx.workdir = None

    @on(FileBrowser.Changed, "#fs_license_file_browser")
    async def _on_fs_license_file_browser_changed(self, message: Message) -> None:
        self.evaluate_fs_license(message.selected_path)

    @work(exclusive=True, name="evaluate_fs_license_worker")
    async def evaluate_fs_license(self, fs_file_path) -> None:
        os.environ["FS_LICENSE"] = fs_file_path
        if not check_valid_fs_license():
            await self.app.push_screen_wait(
                Confirm(
                    "No freesurfer license found!\nSet path to a valid Freesurfer license file.",
                    left_button_text=False,
                    right_button_text="OK",
                    title="Path Error",
                    classes="confirm_error",
                )
            )
            self.get_widget_by_id("fs_license_file_browser").styles.border = ("solid", "red")
            self.fs_license_file_found = False
        else:
            await self.app.push_screen_wait(
                Confirm(
                    "Valid freesurfer license found!",
                    left_button_text=False,
                    right_button_text="OK",
                    title="License found",
                )
            )
            ctx.fs_license_file = fs_file_path
            self.get_widget_by_id("fs_license_file_browser").styles.border = ("solid", "green")
            self.fs_license_file_found = True

    @work(exclusive=True, name="work_dir_path_passed_worker")
    async def _working_dir_path_passed(self, selected_path: str | Path):
        """
        Handles the FileBrowser's Changed event.

        This method is called when the user selects a directory in the
        FileBrowser. It validates the selected directory, updates the UI,
        and checks for an existing 'spec.json' file. If a 'spec.json' file
        is found, it prompts the user to decide whether to load or override
        the existing configuration.

        Note
        ----
        The FileBrowser itself makes checks over the selected working directory
        validity. If it passes then we get here and no more checks are needed.

        Parameters
        ----------
        message : Message
            The message object containing information about the change.
        """
        async def working_directory_override(override) -> None:
            """
            Handles the user's decision to override an existing spec file.

            This nested function is called after the user has been prompted
            about overriding an existing 'spec.json' file. If the user
            chooses to override, it backs up the original 'spec.json' file.

            Parameters
            ----------
            override : bool
                True if the user chose to override the existing file,
                False otherwise.
            """
            if override:
                # make a backup copy from the original spec file
                if ctx.workdir is not None:
                    copy_and_rename_file(os.path.join(ctx.workdir, "spec.json"))
            else:
                self.get_widget_by_id("work_dir_file_browser").update_input(None)
                ctx.workdir = None

        async def existing_spec_file_decision(load):
            """
            Handles the user's decision to load or override an existing spec file.

            This nested function is called when an existing 'spec.json' file
            is found in the selected working directory. It prompts the user
            to decide whether to load the existing settings or override them.

            Parameters
            ----------
            load : bool
                True if the user chose to load the existing file,
                False otherwise.
            """
            if load:
                await self._load_from_spec()
            else:
                result = await self.app.push_screen_wait(
                    Confirm(
                        "This action will override the existing spec in the selected working directory. Are you sure?",
                        title="Override existing working directory",
                        id="confirm_override_spec_file_modal",
                        classes="confirm_warning",
                    )
                )
                await working_directory_override(result)

        # Change border to green
        self.get_widget_by_id("work_dir_file_browser").styles.border = ("solid", "green")
        # add flag signaling that the working directory was set
        self.app.flags_to_show_tabs["from_working_dir_tab"] = True
        self.app.show_hidden_tabs()

        # add path to context object
        ctx.workdir = Path(selected_path)
        # Load the spec and by this we see whether there is existing spec file or not
        self.existing_spec = load_spec(workdir=ctx.workdir)
        if self.existing_spec is not None:
            result = await self.app.push_screen_wait(
                Confirm(
                    "Existing spec file was found! Do you want to load the settings or \
overwrite the working directory and start a new analysis?",
                    title="Spec file found",
                    left_button_text="Load",
                    right_button_text="Override",
                    id="confirm_spec_load_modal",
                    classes="confirm_warning",
                )
            )
            await existing_spec_file_decision(result)

        # freesurfer license block
        full_fs_license_path = os.path.join(selected_path, "license.txt")
        if not self.fs_license_file_found:
            self.get_widget_by_id("fs_license_file_browser").update_input(full_fs_license_path, send_message=False)
            self.evaluate_fs_license(full_fs_license_path)


    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """
        Handles state change events for workers.

        This method is called when the state of a worker changes. If the worker
        ended with SUCCESS, it manages the progression through different stages
        of loading, such as filling the spec context object, caching file patterns,
        mounting features, mounting file panels,and mounting models.

        Parameters
        ----------
        event : Worker.StateChanged
            The event object containing information about the worker's
            state change.
        """
        if event.state == WorkerState.SUCCESS:
            if event.worker.name == "fill_ctx_spec":
                self._cache_file_patterns()
            if event.worker.name == "cache_file_worker" and self.data_input_success is True:
                self._mount_features()
            if event.worker.name == "feature_worker":
                self._mount_file_panels()
            if event.worker.name == "file_panels_worker":
                self._mount_models()

    async def _load_from_spec(self):
        # Go to Stage 1 of the loading process
        self._fill_ctx_spec()

    @work(exclusive=True, name="fill_ctx_spec")
    async def _fill_ctx_spec(self):
        # Stage 1 of the loading process
        await fill_ctx_spec(self)

    @work(exclusive=True, name="cache_file_worker")
    async def _cache_file_patterns(self):
        # Stage 2 of the loading process
        await cache_file_patterns(self)

    @work(exclusive=True, name="feature_worker")
    async def _mount_features(self):
        # Stage 3 of the loading process
        await mount_features(self)

    @work(exclusive=True, name="file_panels_worker")
    async def _mount_file_panels(self) -> None:
        # Stage 4 of the loading process
        await mount_file_panels(self)

    @work(exclusive=True, name="models_worker")
    async def _mount_models(self) -> None:
        # Stage 5 of the loading process
        await mount_models(self)

    @on(Button.Pressed, ".-read-only")
    def on_ee_click(self):
        if sum(self.app.flags_to_show_tabs.values()) == 2:
            self.app.push_screen(
                Confirm(
                    "Input entries cannot be changes now! Restart UI to change them.",
                    title="Read-only",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    id="read_only_modal",
                    classes="confirm_error",
                )
            )
