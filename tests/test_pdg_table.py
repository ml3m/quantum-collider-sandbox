"""Tests for PDG particle table."""

from quantum_collider_sandbox.pdg_table import (
    ELECTRON,
    PARTICLES,
    PROTON,
)


def test_particles_has_proton() -> None:
    """Proton should be in PARTICLES."""
    assert PROTON in PARTICLES


def test_particles_has_electron() -> None:
    """Electron should be in PARTICLES."""
    assert ELECTRON in PARTICLES


def test_proton_properties() -> None:
    """Proton should have expected properties."""
    proton = PARTICLES[PROTON]
    assert proton["name"] == "proton"
    assert proton["charge_e"] == 1
    assert proton["mass_mev"] > 900
