# -*- coding: utf-8 -*-


from textual.app import ComposeResult
from textual.containers import ScrollableContainer

from ..templates.feature_template import FeatureTemplate


class ReHo(FeatureTemplate):
    """
    ReHo

    A class that represents the Regional Homogeneity (ReHo) feature, which is a Measure of the similarity or coherence of the
    time series of a given voxel with its nearest neighbors.

    Attributes
    ----------
    type : str
        A string representing the type of the feature.

    Methods
    -------
    __init__(self, this_user_selection_dict, **kwargs)
        Initializes the ReHo feature with given user selection dictionary and keyword arguments.

    compose(self) -> ComposeResult
        Composes the user interface elements required for the ReHo feature.

    on_mount(self)
        Async method that is called when the ReHo feature is mounted in the application.
    """

    type = "reho"

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        # in this case, smoothing is in features!!!
        self.feature_dict.setdefault("smoothing", {"fwhm": "6"})
        self.setting_dict.pop("smoothing", None)
        # recreate preprocessing panel to reflect smoothing migration from setting to features (in the spec file).
        self.create_preprocessing_panel(self.feature_dict["smoothing"]["fwhm"])

    def on_mount(self):
        self.get_widget_by_id("bandpass_filter_type").default_option = "frequency_based"

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            yield self.tasks_to_use_selection_panel
            yield self.preprocessing_panel

    def set_smoothing_value(self, value):
        self.feature_dict["smoothing"]["fwhm"] = value if value != "" else None

    def set_smoothing_switch_value(self, switch_value):
        # in ReHo the smoothing is in features
        if switch_value is True:
            self.feature_dict["smoothing"] = {"fwhm": "6"}
        elif switch_value is False:
            self.feature_dict["smoothing"]["fwhm"] = None
