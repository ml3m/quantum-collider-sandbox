"""Tests for data_loader module. Requires Taichi CPU init (see conftest.py)."""

import tempfile
from pathlib import Path

import h5py
import numpy as np

from quantum_collider_sandbox import data_loader
from quantum_collider_sandbox.particles import get_type_id_by_name, load_particle_data
from quantum_collider_sandbox.pdg_table import ELECTRON, PHOTON, PROTON
from quantum_collider_sandbox.simulation import init_simulation, num_active, pos, ptype, vel


def test_pdg_to_type_proton() -> None:
    """PDG 2212 should map to proton."""
    assert data_loader.pdg_to_type_name(2212) == "proton"


def test_pdg_to_type_antiproton() -> None:
    """PDG -2212 should map to anti-proton."""
    assert data_loader.pdg_to_type_name(-2212) == "anti-proton"


def test_pdg_to_type_electron() -> None:
    """PDG 11 should map to electron."""
    assert data_loader.pdg_to_type_name(11) == "electron"


def test_pdg_to_type_photon() -> None:
    """PDG 22 should map to photon."""
    assert data_loader.pdg_to_type_name(22) == "photon"


def test_pdg_to_type_unknown_fallback() -> None:
    """Unknown PDG should fallback to proton."""
    assert data_loader.pdg_to_type_name(99999) == "proton"


def test_load_hdf5_events_momentum_only() -> None:
    """load_hdf5_events should load particles from HDF5 with px,py,pz,pdgId."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        path = tmp.name
    try:
        with h5py.File(path, "w") as f:
            f.create_dataset("px", data=np.array([1.0, -2.0, 0.5], dtype=np.float32))
            f.create_dataset("py", data=np.array([0.0, 1.0, -0.5], dtype=np.float32))
            f.create_dataset("pz", data=np.array([0.0, 0.0, 0.0], dtype=np.float32))
            f.create_dataset("pdgId", data=np.array([2212, -11, 22], dtype=np.int32))

        count = data_loader.load_hdf5_events(path, max_particles=10, energy_scale=1.0)
        assert count == 3
        assert num_active[None] == 3
        assert ptype[0] == PROTON
        assert ptype[1] == get_type_id_by_name("positron")
        assert ptype[2] == PHOTON
        # Positions default to (0,0,0)
        assert pos[0][0] == 0.0 and pos[0][1] == 0.0 and pos[0][2] == 0.0
        # Velocities scaled by energy_scale
        assert vel[0][0] == 1.0 and vel[0][1] == 0.0 and vel[0][2] == 0.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_hdf5_events_with_positions() -> None:
    """load_hdf5_events should use x,y,z when present."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        path = tmp.name
    try:
        with h5py.File(path, "w") as f:
            f.create_dataset("px", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("py", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("pz", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("x", data=np.array([2.0], dtype=np.float32))
            f.create_dataset("y", data=np.array([3.0], dtype=np.float32))
            f.create_dataset("z", data=np.array([4.0], dtype=np.float32))
            f.create_dataset("pdgId", data=np.array([11], dtype=np.int32))

        count = data_loader.load_hdf5_events(
            path, max_particles=10, energy_scale=1.0, position_scale=0.5
        )
        assert count == 1
        assert num_active[None] == 1
        assert ptype[0] == ELECTRON
        assert pos[0][0] == 1.0  # 2.0 * 0.5
        assert pos[0][1] == 1.5  # 3.0 * 0.5
        assert pos[0][2] == 2.0  # 4.0 * 0.5
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_hdf5_events_with_vertex() -> None:
    """load_hdf5_events should use vx,vy,vz (vertex) when x,y,z absent."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        path = tmp.name
    try:
        with h5py.File(path, "w") as f:
            f.create_dataset("px", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("py", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("pz", data=np.array([0.0], dtype=np.float32))
            f.create_dataset("vx", data=np.array([1.0], dtype=np.float32))
            f.create_dataset("vy", data=np.array([2.0], dtype=np.float32))
            f.create_dataset("vz", data=np.array([3.0], dtype=np.float32))

        count = data_loader.load_hdf5_events(path, max_particles=10, position_scale=1.0)
        assert count == 1
        assert pos[0][0] == 1.0 and pos[0][1] == 2.0 and pos[0][2] == 3.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_csv_events_basic() -> None:
    """load_csv_events should load particles from CSV with px,py,pz,pdgId."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp:
        tmp.write("px,py,pz,pdgId\n")
        tmp.write("1.0,0.0,0.0,2212\n")
        tmp.write("-1.0,0.0,0.0,-2212\n")
        path = tmp.name
    try:
        count = data_loader.load_csv_events(path, max_particles=10, energy_scale=1.0)
        assert count == 2
        assert num_active[None] == 2
        assert ptype[0] == PROTON
        assert ptype[1] == get_type_id_by_name("anti-proton")
        assert vel[0][0] == 1.0
        assert vel[1][0] == -1.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_csv_events_with_positions() -> None:
    """load_csv_events should use x,y,z when present."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp:
        tmp.write("px,py,pz,pdgId,x,y,z\n")
        tmp.write("0.0,0.0,0.0,22,5.0,6.0,7.0\n")
        path = tmp.name
    try:
        count = data_loader.load_csv_events(path, max_particles=10, position_scale=2.0)
        assert count == 1
        assert ptype[0] == PHOTON
        assert pos[0][0] == 10.0  # 5.0 * 2.0
        assert pos[0][1] == 12.0
        assert pos[0][2] == 14.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_csv_events_default_pdg() -> None:
    """load_csv_events should default pdgId to 2212 when column absent."""
    load_particle_data()
    init_simulation()

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp:
        tmp.write("px,py,pz\n")
        tmp.write("0.0,0.0,0.0\n")
        path = tmp.name
    try:
        count = data_loader.load_csv_events(path, max_particles=10)
        assert count == 1
        assert ptype[0] == PROTON
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_hdf5_no_momentum_returns_zero() -> None:
    """load_hdf5_events should return 0 when px,py,pz missing."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        path = tmp.name
    try:
        with h5py.File(path, "w") as f:
            f.create_dataset("other", data=np.array([1.0]))
        load_particle_data()
        init_simulation()
        count = data_loader.load_hdf5_events(path, max_particles=10)
        assert count == 0
    finally:
        Path(path).unlink(missing_ok=True)
