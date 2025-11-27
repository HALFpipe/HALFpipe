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

def test_help(capfd):
    """ Test if help output distinguishes mandatory and optional inputs. """
    Gradients.help()
    out, err = capfd.readouterr()

    assert 'Mandatory' in out

def test_inputs_string():
    """ Test if traits are checking input correctly. """
    g = Gradients()
    with pytest.raises(TraitError):
        g.inputs.n_components = 'fails'

def test_inputs_file():
    """ Test if traits are checking input correctly. """
    g = Gradients()

    g.inputs.correlation_matrix = '/halfpipe_dev/test_data/derivatives/sub-10171/func/task-rest/sub-10171_task-rest_feature-motionParametersGSR_atlas-Schaefer2018Combined_desc-correlation_matrix.tsv'

def test_inputs_union(tmp_path):
    """ Test if traits are checking input correctly. """
    os.chdir(str(tmp_path))

    g = Gradients()

    np.savetxt('rand1.txt', np.random.randn(100,100))
    np.savetxt('rand2.txt', np.random.randn(100,100))
    g.inputs.correlation_matrix = ['rand1.txt','rand2.txt']

def test_gradient_single_random_array(tmp_path):
    """ Test brainspace functions on random array & that traits are filling in default values. """
    os.chdir(str(tmp_path))

    g = Gradients()

    np.savetxt('rand.txt', np.random.randn(100,100))
    g.inputs.correlation_matrix = 'rand.txt'

    g._run_interface('fake runtime')

    assert g._gradients.shape[0] == 100
    assert g._gradients.shape[1] == 10

def test_outputs(tmp_path):
    """ Test brainspace functions on random array & that traits are filling in default values. """
    os.chdir(str(tmp_path))

    g = Gradients()

    np.savetxt('rand.txt',np.random.randn(100,100))
    g.inputs.correlation_matrix = 'rand.txt'

    g._run_interface('fake runtime')

    outputs = g._list_outputs()
    
    grads = pd.read_csv(outputs['gradients'], delimiter='\t')

    assert grads.shape[1] == 10