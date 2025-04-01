# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import SelectionList

from ..templates.model_template import ModelTemplate


class InterceptOnlyModel(ModelTemplate):
    """
    A model representing an intercept-only group-level model.

    This class extends `ModelTemplate` to provide a specific type of
    group-level model that only includes an intercept term. It allows
    users to select tasks to use, set aggregation levels, and define
    cutoff values.

    Attributes
    ----------
    type : str
        The type of the model, set to "me" for intercept-only model.

    Methods
    -------
    __init__(this_user_selection_dict, id, classes)
        Initializes the model with optional user selections, ID, and classes.
    compose() -> ComposeResult
        Composes the widget's components.
    _on_selection_list_changed()
        Handles changes in the selected tasks.
    """

    type = "me"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the model with optional user selections, ID, and classes.

        Parameters
        ----------
        this_user_selection_dict : dict | None, optional
            A dictionary containing user-specified selections for the model,
            by default None.
        id : str | None, optional
            An optional identifier for the model, by default None.
        classes : str | None, optional
            An optional string of classes for applying styles to the model,
            by default None.
        """
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
                yield self.aggregate_panel
            yield self.cutoff_panel

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    def _on_selection_list_changed(self):
        self.model_dict["inputs"] = self.get_widget_by_id("tasks_to_use_selection").selected
