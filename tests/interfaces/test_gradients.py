import os
import pytest
import numpy as np
import pandas as pd

from halfpipe.interfaces.gradients import Gradients
from traits.trait_errors import TraitError

def test_brainspace_install():
    """ Test if brainspace is installed. """
    try:
        import brainspace
    except ImportError:
        raise ImportError(f'Install "brainspace".')

def test_inputs_string():
    """ Test if traits are checking input correctly. """
    g = Gradients()
    with pytest.raises(TraitError):
        g.inputs.n_components = 'fails'

def test_inputs_array():
    """ Test if traits are checking input correctly. """
    g = Gradients()

    g.inputs.x = np.random.randn(5,5)

def test_inputs_union():
    """ Test if traits are checking input correctly. """
    g = Gradients()

    g.inputs.x = [np.random.randn(5,5),np.random.randn(5,5)]

def test_gradient_single_random_array(tmp_path):
    """ Test brainspace functions on random array & that traits are filling in default values. """
    os.chdir(str(tmp_path))

    g = Gradients()

    g.inputs.x = np.random.randn(100,100)

    g._run_interface('fake runtime')

    assert g._gradients.shape[0] == 100
    assert g._gradients.shape[1] == 10

def test_outputs(tmp_path):
    """ Test brainspace functions on random array & that traits are filling in default values. """
    os.chdir(str(tmp_path))

    g = Gradients()

    g.inputs.x = np.random.randn(100,100)

    g._run_interface('fake runtime')

    outputs = g._list_outputs()
    
    grads = pd.read_csv(outputs['gradients'], delimiter='\t')

    assert grads.shape[1] == 10