# -*- coding: utf-8 -*-


from .reho import ReHo


class Falff(ReHo):
    """
    Falff(this_user_selection_dict, **kwargs)

    A class that represents the falff feature inheriting from ReHo and initializes
    specific unfiltered settings based on the user's selection dictionary.

    Parameters
    ----------
    this_user_selection_dict : dict
        Dictionary containing the user's selection.
    **kwargs : dict
        Additional keyword arguments passed to the ReHo initializer.

    Attributes
    ----------
    unfiltered_settings_dict : dict
        Dictionary containing settings specific to the unfiltered data derived
        from the user's selection dictionary.
    """

    type = "falff"

    def __init__(self, this_user_selection_dict, **kwargs) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, **kwargs)
        self.feature_dict["unfiltered_setting"] = self.feature_dict["name"] + "UnfilteredSetting"
        this_user_selection_dict["unfiltered_setting"]["name"] = self.feature_dict["name"] + "UnfilteredSetting"
        self.unfiltered_settings_dict = this_user_selection_dict["unfiltered_setting"]
