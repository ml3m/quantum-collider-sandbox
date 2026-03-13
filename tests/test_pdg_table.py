"""Tests for PDG particle table."""

from quantum_collider_sandbox.pdg_table import (
    ELECTRON,
    NUM_PARTICLES,
    NUM_TYPES,
    PARTICLES,
    PHOTON,
    PROTON,
    PROTON_MASS_MEV,
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


def test_num_particles() -> None:
    """NUM_PARTICLES should match PARTICLES size."""
    assert NUM_PARTICLES == 40
    assert len(PARTICLES) == NUM_PARTICLES


def test_num_types() -> None:
    """NUM_TYPES should allow for user-defined particles."""
    assert NUM_TYPES >= NUM_PARTICLES


def test_photon_in_particles() -> None:
    """Photon should be in PARTICLES."""
    assert PHOTON in PARTICLES
    assert PARTICLES[PHOTON]["name"] == "photon"
    assert PARTICLES[PHOTON]["mass_mev"] < 0.01  # massless (stored as small value)


def test_proton_mass_constant() -> None:
    """PROTON_MASS_MEV should match proton entry."""
    assert PARTICLES[PROTON]["mass_mev"] == PROTON_MASS_MEV


def test_all_particles_have_required_fields() -> None:
    """Each particle entry should have required keys."""
    required = {"name", "mass_mev", "charge_e", "lifetime_s", "radius", "color"}
    for tid, props in PARTICLES.items():
        for key in required:
            assert key in props, f"Particle {tid} missing {key}"
