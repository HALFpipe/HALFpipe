from ..specialized_widgets.event_file_widget import SpatialMapFilePanel
from ..standards import gig_ica_defaults
from .dual_reg import DualReg


class Gigica(DualReg):
    entity = "desc"
    filters = {"datatype": "ref", "suffix": "map"}
    featurefield = "maps"
    type = "gig_ica"
    file_panel_class = SpatialMapFilePanel
    defaults = gig_ica_defaults
