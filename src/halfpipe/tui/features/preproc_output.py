# -*- coding: utf-8 -*-


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

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    async def mount_tasks(self):
        self.get_widget_by_id("model_conditions_and_constrasts").remove()  # .styles.visibility = "hidden"
        if self.images_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Tasks to use"
