# -*- coding: utf-8 -*-


from copy import deepcopy

from textual.app import ComposeResult
from textual.containers import ScrollableContainer

from ..standards import reho_defaults
from ..templates.feature_template import FeatureTemplate


class ReHo(FeatureTemplate):
    """
    Initializes the ReHo instance.

    This method initializes the ReHo object by calling the constructor
    of the parent class (`FeatureTemplate`) and setting up the
    smoothing in features dictionary and popping it out from the settings dictionary.
    Furthermore, the default bandpass filter changes to frequency based.

    Parameters
    ----------
    this_user_selection_dict : dict
        A dictionary containing the user's selection for this feature.
    **kwargs : dict
        Additional keyword arguments passed to the FeatureTemplate initializer.
    """

    type = "reho"
    defaults = reho_defaults

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        _defaults = deepcopy(self.defaults)
        super().__init__(this_user_selection_dict=this_user_selection_dict, defaults=_defaults, id=id, classes=classes)
        # in this case, smoothing is in features!!!
        self.feature_dict.setdefault("smoothing", _defaults["smoothing"])
        self.setting_dict.pop("smoothing", None)
        # recreate preprocessing panel to reflect smoothing migration from setting to features (in the spec file).
        self.create_preprocessing_panel(self.feature_dict["smoothing"]["fwhm"])

    def on_mount(self):
        """
        On the widget mount the default option for the bandpass filter type is set
        to "frequency_based".
        """
        self.get_widget_by_id("bandpass_filter_type").default_option = "frequency_based"

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_task_based"):
            yield self.tasks_to_use_selection_panel
            yield self.preprocessing_panel

    def _update_smoothing_setting(self, switch_value: bool, value: str | None) -> None:
        """
        Shared logic for updating smoothing settings.

        Parameters
        ----------
        switch_value : bool
            The state of the smoothing switch (True = enabled, False = disabled).
        value : str | None
            The current smoothing value from the input box.
        """
        if switch_value:
            # Switch is ON → set value
            self.feature_dict["smoothing"]["fwhm"] = value if value != "" else None
        else:
            # Switch is OFF → clear value
            self.feature_dict["smoothing"]["fwhm"] = None
