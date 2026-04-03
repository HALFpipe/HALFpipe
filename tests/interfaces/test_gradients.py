import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from brainspace.gradient.utils import make_symmetric
from traits.trait_errors import TraitError

from halfpipe.interfaces.gradients import Gradients


def test_help(capfd: pytest.CaptureFixture[str]):
    """Test if help output distinguishes mandatory and optional inputs."""
    Gradients.help()
    out, _ = capfd.readouterr()

    assert "Mandatory" in out


def test_inputs_string():
    """Test if traits are checking input correctly."""
    g = Gradients()
    with pytest.raises(TraitError):
        g.inputs.n_components = "invalid"


def test_inputs_union(tmp_path: Path) -> None:
    """Test if traits are checking input correctly."""
    os.chdir(str(tmp_path))

    g = Gradients()

    np.savetxt("rand1.txt", np.random.randn(100, 100))
    g.inputs.correlation_matrix = "rand1.txt"


def test_gradient_single_random_array(tmp_path: Path) -> None:
    """Test brainspace functions on random array & that traits are filling in default values."""
    os.chdir(str(tmp_path))
    rng = np.random.default_rng(0)

    g = Gradients()

    correlation_matrix_path = tmp_path / "rand.txt"
    a = rng.normal(size=(1000, 100))
    c = make_symmetric(a.transpose() @ a)

    np.savetxt(correlation_matrix_path, c)
    g.inputs.correlation_matrix = correlation_matrix_path
    g.inputs.reference = rng.normal(size=(100, 10))

    cwd = tmp_path / "gradients"
    cwd.mkdir()

    result = g.run(cwd=cwd)

    grads = pd.read_csv(result.outputs.gradients, delimiter="\t", header=None)
    assert grads.shape == (100, 10)
