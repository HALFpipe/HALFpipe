# -*- coding: utf-8 -*-

from copy import deepcopy

from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message

from ..general_widgets.custom_general_widgets import LabelWithInputBox
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
            yield self.file_panel_class(
                default_file_tags=self.feature_dict[self.featurefield],
                file_tagging=True,
                id="top_file_panel",
                classes="components file_panel",
            )
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

    # @on(FilePanelTemplate.FileTagsChanged)
    # def on_file_tag_selection_changed(self, message) -> None:
    #     """
    #     Handles changes in the tag selection list.
    #
    #     This method is called when the selection in the `SelectionList`
    #     widget changes. It updates the corresponding value in the
    #     `feature_dict`.
    #
    #     Parameters
    #     ----------
    #     selection_list : SelectionList
    #         The selection list widget.
    #     """
    #     self.feature_dict[self.featurefield] = message.value
