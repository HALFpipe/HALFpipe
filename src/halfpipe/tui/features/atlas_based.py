# -*- coding: utf-8 -*-


from ..specialized_widgets.event_file_widget import AtlasFilePanel
from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate


class AtlasBased(AtlasSeedDualRegBasedTemplate):
    """
    A class used to represent Atlas-based connectivity analysis

    Attributes
    ----------
    entity : str
        A description of the entity, which in this context is "desc"
    filters : dict
        A dictionary containing filters for datatype and suffix
            - datatype: "ref"
            - suffix: "atlas"
    featurefield : str
        A field representing the atlas feature set, in this case "atlases"
    type : str
        The type of connectivity analysis, denoted as "atlas_based_connectivity"
    file_panel_class : class
        A reference to the class used for file panel, here it is AtlasFilePanel
    minimum_coverage_label : str
        A label describing the minimum coverage of atlas regions by individual brain mask
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "atlas"}
    featurefield = "atlases"
    type = "atlas_based_connectivity"
    file_panel_class = AtlasFilePanel
    minimum_coverage_label = "Minimum atlas region coverage by individual brain mask"
    minimum_coverage_tag = "min_region_coverage"
