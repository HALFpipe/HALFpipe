# -*- coding: utf-8 -*-


from .task_based import TaskBased


class PreprocessedOutputOptions(TaskBased):
    """
    PreprocessedOutputOptions(this_user_selection_dict, **kwargs)

    Class for managing preprocessed image output options.

    Parameters
    ----------
    this_user_selection_dict : dict
        Dictionary containing user selections.
    **kwargs
        Additional keyword arguments passed to the superclass.

    Methods
    -------
    on_mount()
        Async method to handle actions when the widget is mounted.
    """

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # no features for preprocessed image output!
        this_user_selection_dict["features"] = {}

    async def mount_tasks(self):
        self.get_widget_by_id("model_conditions_and_constrasts").remove()  # .styles.visibility = "hidden"
        if self.images_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Tasks to use"
