# -*- coding: utf-8 -*-


from ..specialized_widgets.event_file_widget import SpatialMapFilePanel
from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate


class DualReg(AtlasSeedDualRegBasedTemplate):
    """
    Represents Dual Regression.

    This class defines the parameters and behavior for dual regression,
    extending the `AtlasSeedDualRegBasedTemplate`. It specifies
    the entity, filters, feature field, type, file panel class, and minimum
    coverage settings relevant to dual regression.

    Attributes
    ----------
    entity : str
        The entity used for describing the spatial maps, which is "desc" in this context.
    filters : dict[str, str]
        Filters used to identify spatial map files.
        - datatype : str
            The datatype of the spatial map files, which is "ref".
        - suffix : str
            The suffix of the spatial map files, which is "map".
    featurefield : str
        The field representing the spatial map feature set, which is "maps".
    type : str
        The type of connectivity analysis, which is "dual_regression".
    file_panel_class : Type[SpatialMapFilePanel]
        The class used for the file panel, which is `SpatialMapFilePanel`.
    minimum_coverage_label : str
        A label describing the minimum coverage of spatial map regions by individual brain masks.
    minimum_coverage_tag : str
        A tag used to identify the minimum coverage setting, which is "min_region_coverage".

    Methods
    -------
    on_mount :
        Removes the minimum coverage widget upon mounting.
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "map"}
    featurefield = "maps"
    type = "dual_regression"
    file_panel_class = SpatialMapFilePanel
    minimum_coverage_label = "Minimum spatial map region coverage by individual brain mask"
    widget_header: str = "Network template images"
    file_selection_widget_header: str = "Select network templates"

    async def on_mount(self) -> None:
        self.get_widget_by_id("minimum_coverage").remove()
