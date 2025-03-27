# -*- coding: utf-8 -*-


from ..specialized_widgets.event_file_widget import SeedMapFilePanel
from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate


class SeedBased(AtlasSeedDualRegBasedTemplate):
    """
    Represents Seed-based connectivity analysis.

    This class implements seed-based connectivity analysis by extending
    the `AtlasSeedDualRegBasedTemplate`.

    Attributes
    ----------
    entity : str
        The entity used for describing the seed maps. In this case, it is
        set to "desc", indicating that the seed maps are described by a
        description (e.g., `desc-mySeedMap`).
    filters : dict[str, str]
        Filters used to identify seed map files based on their data type
        and suffix.
        - datatype : str
            The datatype of the seed map files, which is "ref".
        - suffix : str
            The suffix of the seed map files, which is "seed".
    featurefield : str
        The name of the field in the features dictionary that holds the seed
        map information. In this case, it is "seeds".
    type : str
        A string indicating the type of connectivity analysis performed by
        this class, which is "seed_based_connectivity".
    file_panel_class : type[SeedMapFilePanel]
        The class used to manage the file selection panel for seed map files.
        It is set to `SeedMapFilePanel`.
    minimum_coverage_label : str
        A descriptive label for the minimum coverage setting, which is displayed
        to the user. In this case, it is "Minimum seed map region coverage
        by individual brain mask".
    minimum_coverage_tag : str
        A tag used to identify the minimum coverage setting in the data. It is
        set to "min_seed_coverage". This tag is used for internal
        representation and data handling.
    """

    entity: str = "desc"
    filters: dict[str, str] = {"datatype": "ref", "suffix": "seed"}
    featurefield: str = "seeds"
    type: str = "seed_based_connectivity"
    file_panel_class = SeedMapFilePanel
    minimum_coverage_label: str = "Minimum fMRI brain coverage by seed"
    minimum_coverage_tag: str = "min_seed_coverage"
