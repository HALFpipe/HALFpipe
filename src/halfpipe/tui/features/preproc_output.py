# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.message import Message
from textual.widgets import Select, Static

from ..standards import preproc_output_defaults
from .task_based import TaskBased


class PreprocessedOutputOptions(TaskBased):
    """
    Manages options for outputting preprocessed images.

    This class extends the `TaskBased` class to handle options related to
    outputting preprocessed images. It inherits the basic structure and
    functionality from `TaskBased` but removes the model conditions and
    contrasts widget, as it is not relevant for preprocessed image output.

    Attributes
    ----------
    type : str
        The type of the feature, which is "preprocessed_image".

    Methods
    -------
    __init__(this_user_selection_dict, **kwargs)
        Initializes the PreprocessedOutputOptions instance.
    mount_tasks()
        Removes the model conditions and contrasts widget and sets the
        border title for the tasks to use selection.
    """

    type = "preprocessed_image"
    defaults = preproc_output_defaults

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    async def mount_tasks(self):
        pass

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            if self.images_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.preprocessing_panel

    async def on_mount(self):
        space_selection = Horizontal(
            Static("Specify space", id="space_label"),
            Select(
                options=[("Standard space (MNI ICBM 2009c Nonlinear Asymmetric)", "standard"), ("Native space", "native")],
                value=self.setting_dict["space"],
                allow_blank=False,
                id="space_selection",
            ),
            id="space_selection_panel",
        )
        preproc_widget = self.get_widget_by_id("preprocessing")
        await preproc_widget.mount(space_selection, before=preproc_widget.get_widget_by_id("smoothing"))

    @on(Select.Changed, "#space_selection")
    def on_keep_selection_changed(self, message: Message):
        self.setting_dict["space"] = message.value
