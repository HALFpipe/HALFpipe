# -*- coding: utf-8 -*-


from ..specialized_widgets.event_file_widget import AtlasFilePanel
from ..standards import atlas_based_connectivity_defaults
from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate


class AtlasBased(AtlasSeedDualRegBasedTemplate):
    """
    Represents Atlas-based connectivity.

    This class defines the parameters and behavior for atlas-based
    connectivity feature, extending the `AtlasSeedDualRegBasedTemplate`.
    It specifies the entity, filters, feature field, type, file panel class,
    and minimum coverage settings relevant to atlas-based. It needs at atlas.

    Attributes
    ----------
    entity : str
        The entity used for describing the atlas, which is "desc" in this context.
    filters : dict[str, str]
        Filters used to identify atlas files.
        - datatype : str
            The datatype of the atlas files, which is "ref".
        - suffix : str
            The suffix of the atlas files, which is "atlas".
    featurefield : str
        The field representing the atlas feature set, which is "atlases".
    type : str
        The type of connectivity analysis, which is "atlas_based_connectivity".
    file_panel_class : Type[AtlasFilePanel]
        The class used for the file panel, which is `AtlasFilePanel`.
    minimum_coverage_label : str
        A label describing the minimum coverage of atlas regions by individual brain masks.
    minimum_coverage_tag : str
        A tag used to identify the minimum coverage setting, which is "min_region_coverage".
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "atlas"}
    featurefield = "atlases"
    type = "atlas_based_connectivity"
    file_panel_class = AtlasFilePanel
    minimum_coverage_tag = "min_region_coverage"
    defaults = atlas_based_connectivity_defaults
