import os
import pytest
import numpy as np
#import pandas as pd

from halfpipe.model.feature import Feature #, GradientsFeatureSchema, FeatureSchema
from halfpipe.workflows.memory import MemoryCalculator

from halfpipe.workflows.downstream_features.gradients import init_gradients_wf
from halfpipe.utils.nipype import run_workflow
#from traits.trait_errors import TraitError

# TODO
# test I/O through features/nodes/workflow
# how do you define a feature to then pass elsewhere?

def test_gradients_wf_connect(tmp_path):
    """Test to check connection of gradients wf with previous atlas based connectivity wf."""

    # define inputs somehow

    # create an atlas based connectivity wf

    # create a gradients wf

    # connect them lol how
