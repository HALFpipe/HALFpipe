# -*- coding: utf-8 -*-

from copy import deepcopy

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from ...logging import logger
from ..general_widgets.custom_general_widgets import LabelWithInputBox
from ..help_functions import extract_name_part
from ..specialized_widgets.event_file_widget import AtlasFilePanel
from ..templates.feature_template import FeatureTemplate


class AtlasSeedDualRegBasedTemplate(FeatureTemplate):
    """
    AtlasSeedDualRegBasedTemplate is a superclass for managing Atlas, Seed and DualReg features.
    These three subclasses contains the tag_panel.

    Attributes
    ----------
    entity : str
        Descriptive representation of the feature.
    filters : dict
        Dictionary containing datatype and suffix filters.
    featurefield : str
        The field specifying atlases.
    type : str
        Type of the feature, in this case, "atlas_based_connectivity".
    file_panel_class : Type
        Class used for the file panel in the GUI.
    minimum_coverage_label : str
        Label text for minimum atlas region coverage by individual brain mask.
    minimum_coverage_tag : str
        Tag for minimum atlas region coverage by individual brain mask.

    Methods
    -------
    __init__(this_user_selection_dict, id=None, classes=None)
        Initializes the AtlasSeedDualRegBasedTemplate.
    compose()
        Constructs the GUI layout for atlas-based connectivity.
    on_mount()
        Handles actions to be taken when the component is mounted in the GUI.
    _on_label_with_input_box_changed(message)
        Handles changes in the LabelWithInputBox widget.
    on_file_panel_file_item_is_deleted(message)
        Handles the deletion of a file item in the file panel.
    on_file_panel_changed(message)
        Handles changes in the file panel.
    update_file_tag_selection(file_tags)
        Updates the tag selection list based on the provided tag values.
    on_file_tag_selection_changed(selection_list)
        Handles changes in the tag selection list.
    """

    entity: str = ""
    filters: dict = {}
    featurefield = ""
    type: str = ""
    file_panel_class = AtlasFilePanel
    minimum_coverage_tag: str = ""
    defaults: dict = {}

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the AtlasSeedDualRegBasedTemplate.

        Parameters
        ----------
        this_user_selection_dict : dict
            A dictionary containing user selections.
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        """
        _defaults = deepcopy(self.defaults)
        super().__init__(this_user_selection_dict=this_user_selection_dict, defaults=_defaults, id=id, classes=classes)

        self.minimum_coverage_label = _defaults["minimum_coverage_label"]
        self.widget_header = _defaults["widget_header"]
        self.file_selection_widget_header = _defaults["file_selection_widget_header"]

        self.feature_dict.setdefault(self.minimum_coverage_tag, _defaults["minimum_brain_coverage"])
        self.feature_dict.setdefault(self.featurefield, [])

        self.file_tags: list = []
        self.file_tag_init_flag = True

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            if self.images_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.file_panel_class(id="top_file_panel", classes="components file_panel")
            yield SelectionList[str](id="file_tag_selection", classes="components")
            yield LabelWithInputBox(
                label=self.minimum_coverage_label,
                value=self.feature_dict[self.minimum_coverage_tag],
                classes="switch_with_input_box components",
                id="minimum_coverage",
            )
            yield self.preprocessing_panel

    async def on_mount(self) -> None:
        try:
            self.get_widget_by_id("minimum_coverage").border_title = "Minimum brain coverage"
        except Exception:
            pass
        self.get_widget_by_id("file_tag_selection").border_title = self.file_selection_widget_header
        self.get_widget_by_id("top_file_panel").border_title = self.widget_header

    @on(LabelWithInputBox.Changed, "#minimum_coverage")
    def _on_label_with_input_box_changed(self, message: Message) -> None:
        """
        Handles changes in the LabelWithInputBox widget.

        This method is called when the value of the `LabelWithInputBox`
        widget changes. It updates the corresponding value in the
        `feature_dict`.

        Parameters
        ----------
        message : Message
            The message object containing information about the change.
        """
        self.feature_dict[self.minimum_coverage_tag] = message.value

    def _extract_file_tags(self, file_pattern, files, file_tag=None):
        """
        Extract file tags based on the given file pattern, file paths, and optional file_tag.
        Falls back to 'desc' suffix if no tags are found with the main suffix.

        Parameters
        ----------
        file_pattern : str
            The pattern used to extract tags.
        files : list[str]
            List of file paths.
        file_tag : str | None
            A provided file tag. If given, it's used directly.

        Returns
        -------
        set[str | None]
            A set of extracted file tags.
        """
        if isinstance(file_pattern, Text):
            file_pattern = file_pattern.plain

        if file_tag is None:
            tags = {extract_name_part(file_pattern, file_path, suffix=self.filters["suffix"]) for file_path in files}
            if tags == {None}:  # fallback to 'desc'
                tags = {extract_name_part(file_pattern, file_path, suffix="desc") for file_path in files}
        else:
            tags = {file_tag}

        return tags

    @on(file_panel_class.FileItemIsDeleted, "#top_file_panel")
    def on_file_panel_file_item_is_deleted(self, message: Message) -> None:
        """
        Handles the deletion of a file item in the file panel.

        This method is called when a file item is deleted in the file
        panel. It updates the tag selection list to remove any tags
        associated with the deleted file item.

        Parameters
        ----------
        message : Message
            The message object containing information about the deleted
            file item.
        """

        file_pattern = message.value["file_pattern"]
        file_tag = message.value["file_tag"]
        files = message.value["files"]

        all_file_tags_based_on_the_current_file_patterns = self._extract_file_tags(file_pattern, files, file_tag)

        logger.debug(
            f"UI->AtlasSeedDualRegBasedTemplate->on_file_panel_file_item_is_deleted->tags to remove: \
{all_file_tags_based_on_the_current_file_patterns}"
        )
        self.update_file_tag_selection(all_file_tags_based_on_the_current_file_patterns, remove=True)

    @on(file_panel_class.Changed, "#top_file_panel")
    def on_file_panel_changed(self, message: Message) -> None:
        """
        Handles changes in the file panel.

        This method is called when the file panel changes. It extracts
        tags from the file paths based on the file pattern and updates
        the file tag selection list.

        Parameters
        ----------
        message : Message
            The message object containing information about the change.
        """

        file_pattern = message.value["file_pattern"]
        file_tag = message.value["file_tag"]
        files = message.value["files"]

        all_file_tags_based_on_the_current_file_patterns = self._extract_file_tags(file_pattern, files, file_tag)

        # XOR (^) to avoid duplicate tags if the same file pattern is added twice
        file_tags = set(self.file_tags) ^ all_file_tags_based_on_the_current_file_patterns

        logger.debug(
            f"UI->AtlasSeedDualRegBasedTemplate->on_file_panel_changed->all_file_tags_based_on_the_current_file_patterns:\
{all_file_tags_based_on_the_current_file_patterns}"
        )
        self.update_file_tag_selection(file_tags)

    @work(exclusive=False, name="update_file_tag_selection")
    async def update_file_tag_selection(self, file_tags: set, remove=False) -> None:
        """
        Updates the tag selection list based on the provided tag values.

        This method updates the tag selection list with the provided tag
        values. It handles the initial selection of tags and subsequent
        updates.

        Parameters
        ----------
        file_tags : set
            A set of tag values to update the selection list with.
        """
        if not remove:
            current_options = list(self.get_widget_by_id("file_tag_selection")._values)
            for file_tag in sorted(file_tags):
                if file_tag not in current_options:
                    self.get_widget_by_id("file_tag_selection").add_option(Selection(file_tag, file_tag, initial_state=True))
            logger.debug(
                f"UI->AtlasSeedDualRegBasedTemplate->update_file_tag_selection->file_tag_selection._values->\
{self.get_widget_by_id('file_tag_selection')._values}"
            )

            # After Init the on_file_panel_changed will be automatically activated since the file panel is changed by addition
            # of the file patterns. If this is the case, we deselect all selections and select only the options selected
            # previous (either by duplication or on load from a spec file) and select only the ones in the dictionary carrying
            # previous options, (self.feature_dict[self.featurefield]). If this field is empty, this means that we are not
            # creating a new feature by duplication or from a spec file load by standardly by just adding a new feature. In
            # such case we select all choices
            if self.file_tag_init_flag:
                self.get_widget_by_id("file_tag_selection").deselect_all()
                if self.feature_dict[self.featurefield] == []:
                    self.get_widget_by_id("file_tag_selection").select_all()
                else:
                    for file_tag in self.feature_dict[self.featurefield]:
                        self.get_widget_by_id("file_tag_selection").select(file_tag)

                self.file_tag_init_flag = False
            else:
                # This is run always except from the first time on init.
                self.feature_dict[self.featurefield].append(file_tag)
        else:
            selection_widget = self.get_widget_by_id("file_tag_selection")
            for file_tag in sorted(file_tags):
                current_options = list(selection_widget._values)

                logger.debug(f"UI->update_file_tag_selection-> current_options:{current_options}")

                if file_tag in current_options:
                    self.get_widget_by_id("file_tag_selection")._remove_option(current_options.index(file_tag))

    @on(SelectionList.SelectedChanged, "#file_tag_selection")
    def on_file_tag_selection_changed(self, selection_list) -> None:
        """
        Handles changes in the tag selection list.

        This method is called when the selection in the `SelectionList`
        widget changes. It updates the corresponding value in the
        `feature_dict`.

        Parameters
        ----------
        selection_list : SelectionList
            The selection list widget.
        """
        self.feature_dict[self.featurefield] = selection_list.control.selected
