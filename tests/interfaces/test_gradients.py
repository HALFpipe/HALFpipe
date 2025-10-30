import pytest
import numpy as np

from halfpipe.interfaces.gradients import Gradients
from traits.trait_errors import TraitError

def test_brainspace_install():
    """ Test if brainspace is installed."""
    try:
        import brainspace
    except ImportError:
        raise ImportError(f'Install "brainspace".')

def test_inputs_string():
    g = Gradients()
    with pytest.raises(TraitError):
        g.inputs.n_components = 'fails'

def test_inputs_array():
    g = Gradients()

    g.inputs.x = np.random.randn(5,5)

def test_inputs_union():
    g = Gradients()

    g.inputs.x = [np.random.randn(5,5),np.random.randn(5,5)]


# FAILING
# traits is not applying default values??
# needs to be run by called by nipype somehow?

    # Investigate! known to nipype:
    """
    The functions that pop-up the Traits GUIs, edit_traits and
configure_traits, were failing because all of our inputs default to
Undefined deep and down in traits/ui/wx/list_editor.py it checks for
the len() of the elements of the list.  The _Undefined class in traits
does not define the __len__ method and would error.  I tried defining
our own Undefined and even subclassing Undefined, but both of those
failed with a TraitError in our initializer when we assign the
Undefined to the inputs because of an incompatible type:"""
def test_gradient_single_random_array():
    g = Gradients()

    g.inputs.x = np.random.randn(100,100)

    # TRAITS NOT PUTTING IN DEFAULTS
    g.inputs.n_components = 10
    g.inputs.approach = 'dm'

    g.inputs.kernel = None
    g.inputs.random_state = None
    g.inputs.alignment = None

    g.inputs.gamma = None
    g.inputs.sparsity = 0.9
    g.inputs.n_iter = 10
    g.inputs.reference = None

    g._run_interface('fake runtime')

    assert g._gradients.shape[0] == 100
    assert g._gradients.shape[1] == 10