#import os
#import pytest
#import numpy as np
#import pandas as pd

from halfpipe.model.feature import GradientsFeatureSchema, FeatureSchema, Feature

from halfpipe.workflows.features.gradients import init_gradients_wf
#from traits.trait_errors import TraitError

# TODO
# test I/O through features/nodes/workflow
# how do you define a feature to then pass elsewhere?
# do I need to pass inputs directly to Gradiens()? or does it come automatically from node connections?

def test_gradients_feature():
    feat = Feature("gradients", "gradients", bing_bong = 10)
    #feat = FeatureSchema().load(dict(type="gradients", name="gradients"))
    schema = GradientsFeatureSchema()
    schema.load(feat)
    #assert data['type'] is "gradients"
    # assert data['n_components'] == 10
    # assert data['approach'] is None
    #assert data['bing_bong'] == 10
    # this fails but no message e.g. its not in the schema

    # Failing
    # schemas only create keys in the dictionary when the dump_default is not None
    # schemas are not doing clear type checking like traits in fact I dont know what they do
    # seems like Features are defined however you please by just passing anything to constructor odd

