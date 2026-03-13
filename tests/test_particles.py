"""Tests for particles module. Requires Taichi CPU init for imports."""

import taichi as ti

ti.init(arch=ti.cpu)

from quantum_collider_sandbox.particles import (
    get_type_id_by_name,
    get_type_name,
    load_particle_data,
)


def test_get_type_name_proton() -> None:
    """get_type_name should return 'proton' for PROTON id."""
    from quantum_collider_sandbox.pdg_table import PROTON

    assert get_type_name(PROTON) == "proton"


def test_get_type_name_electron() -> None:
    """get_type_name should return 'electron' for ELECTRON id."""
    from quantum_collider_sandbox.pdg_table import ELECTRON

    assert get_type_name(ELECTRON) == "electron"


def test_get_type_name_unknown() -> None:
    """get_type_name should return type_N for unknown id."""
    assert get_type_name(999) == "type_999"


def test_get_type_id_by_name_proton() -> None:
    """get_type_id_by_name should find proton."""
    from quantum_collider_sandbox.pdg_table import PROTON

    assert get_type_id_by_name("proton") == PROTON


def test_get_type_id_by_name_unknown() -> None:
    """get_type_id_by_name should return -1 for unknown name."""
    assert get_type_id_by_name("nonexistent") == -1


def test_load_particle_data_no_error() -> None:
    """load_particle_data should run without raising."""
    load_particle_data()
