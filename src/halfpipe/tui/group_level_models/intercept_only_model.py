# -*- coding: utf-8 -*-


from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import SelectionList

from ..templates.model_template import ModelTemplate

aggregate_order = ["dir", "run", "ses", "task"]


class InterceptOnlyModel(ModelTemplate):
    type = "me"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.cutoff_panel

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    def _on_selection_list_changed(self):
        self.model_dict["inputs"] = self.get_widget_by_id("tasks_to_use_selection").selected
