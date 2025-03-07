# -*- coding: utf-8 -*-


from ..specialized_widgets.event_file_widget import SpatialMapFilePanel
from ..templates.atlas_seed_dual_reg_based_template import AtlasSeedDualRegBasedTemplate


class DualReg(AtlasSeedDualRegBasedTemplate):
    """
    class DualReg(AtlasSeedDualRegBasedTemplate):
    """

    entity = "desc"
    filters = {"datatype": "ref", "suffix": "map"}
    featurefield = "maps"
    type = "dual_regression"
    file_panel_class = SpatialMapFilePanel
    minimum_coverage_label = "Minimum spatial map region coverage by individual brain mask"

    async def on_mount(self) -> None:
        self.get_widget_by_id("minimum_coverage").remove()
