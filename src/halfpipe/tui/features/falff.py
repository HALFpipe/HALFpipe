# -*- coding: utf-8 -*-


from ..standards import falff_defaults
from .reho import ReHo


class Falff(ReHo):
    """
    Represents the fALFF (fractional Amplitude of Low-Frequency Fluctuations) feature.

    This class extends the `ReHo` class to implement the fALFF feature. It
    inherits the basic structure and functionality from `ReHo` and adds
    specific settings for unfiltered data, i.e., the field unfilteredSettings.

    Attributes
    ----------
    type : str
        The type of the feature, which is "falff".
    unfiltered_settings_dict : dict
        A dictionary containing settings specific to the unfiltered data,
        derived from the user's selection dictionary.

    Methods
    -------
    __init__(this_user_selection_dict, **kwargs)
        Initializes the Falff instance.
    """

    type = "falff"
    defaults = falff_defaults

    def __init__(self, this_user_selection_dict, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

        self.feature_dict["unfiltered_setting"] = self.feature_dict["name"] + "UnfilteredSetting"
        this_user_selection_dict["unfiltered_setting"]["name"] = self.feature_dict["name"] + "UnfilteredSetting"
        self.unfiltered_settings_dict = this_user_selection_dict["unfiltered_setting"]
