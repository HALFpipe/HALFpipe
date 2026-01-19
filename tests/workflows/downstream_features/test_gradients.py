import os

import numpy as np

# import pandas as pd
from halfpipe.model.downstream_feature import DownstreamFeature
from halfpipe.utils.nipype import run_workflow
from halfpipe.workflows.downstream_features.gradients import init_gradients_wf
from halfpipe.workflows.memory import MemoryCalculator

# from traits.trait_errors import TraitError


def test_gradients_wf_input(tmp_path):
    """Test to check if input is accepted."""
    workdir = tmp_path

    # random matrix connectome for now
    correlation_matrix = np.random.randn(50, 50)

    # unclear how to load a feature to be made like this but I want all these fields to be default None and will then be filled by the input spec
    # I have many questions about how features are created and validated
    feat = DownstreamFeature(
        "gradients",  # name
        "gradients",  # type
        # kwargs
        **{
            "n_components": None,
            "approach": None,
            "kernel": None,
            "random_state": None,
            "alignment": None,
            "gamma": None,
            "sparsity": None,
            "n_iter": None,
            "reference": None,
        },
    )

    init_gradients_wf(
        workdir,
        correlation_matrix,
        feat,
    )


def test_gradients_wf_run(tmp_path):
    """Test to check if wf runs."""
    os.chdir(str(tmp_path))

    workdir = tmp_path

    # random matrix connectome for now
    np.savetxt("rand1.txt", np.random.randn(100, 100))
    correlation_matrix = os.path.join(tmp_path, "rand1.txt")

    # unclear how to load a feature to be made like this but I want all these fields to be default None and will then be filled by the input spec
    # I have many questions about how features are created and validated
    feat = DownstreamFeature(
        "gradients",  # name
        "gradients",  # type
        # Traits complains for none
        # When trait is checked/feature created need to fill defaults w appropriate values
        # kwargs
        **{
            "n_components": 10,
            "approach": "dm",
            "kernel": None,
            "random_state": None,
            "alignment": None,
            "gamma": None,
            "sparsity": 0.9,
            "n_iter": 10,
            "reference": None,
        },
    )

    memcalc = MemoryCalculator.default()

    wf = init_gradients_wf(workdir, correlation_matrix, feat, memcalc)

    # I dont understand why this would be defined here and not in the init_wf but im following halfpipe (atlas_based_connectivity)
    # bc of nested workflows w/ different base_dir
    wf.base_dir = workdir

    graph = run_workflow(wf)
