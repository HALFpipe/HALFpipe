# -*- coding: utf-8 -*-


from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate
from ..utils.event_file_widget import SeedMapFilePanel


class SeedBased(AtlasSeedDualRegBasedTemplate):
    """
    Inherits from AtlasSeedDualRegBasedTemplate and represents a connectivity analysis
    using seed-based approach.

    Attributes
    ----------
    entity : str
        Description of the entity being analyzed.
    filters : dict
        Dictionary specifying filters for data type and suffix.
    featurefield : str
        Field name in the feature dataset.
    type : str
        Type of connectivity being analyzed.
    file_panel_class : type
        Class used for managing file panels.
    minimum_coverage_label : str
        Label for the minimum coverage requirement of seed map regions by
        individual brain masks.
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "seed"}
    featurefield = "seeds"
    type = "seed_based_connectivity"
    file_panel_class = SeedMapFilePanel
    minimum_coverage_label = "Minimum seed map region coverage by individual brain mask"
    minimum_coverage_tag = "min_seed_coverage"
