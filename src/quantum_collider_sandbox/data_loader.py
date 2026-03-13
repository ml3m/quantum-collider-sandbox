"""HDF5 and CSV loader for CMS/ATLAS-style event data."""

import h5py
import numpy as np

from . import simulation as sim
from .particles import get_type_id_by_name

# PDG Monte Carlo particle numbering (signed: negative = antiparticle).
# Maps PDG codes to internal type names from pdg_table.
# See https://pdg.lbl.gov/2024/mcdata/mc_particle_id_contents.html
PDG_TO_TYPE = {
    # Leptons
    11: "electron",
    -11: "positron",
    13: "muon",
    -13: "anti-muon",
    15: "tau",
    -15: "anti-tau",
    12: "nu_e",
    -12: "nu_e_bar",
    14: "nu_mu",
    -14: "nu_mu_bar",
    16: "nu_tau",
    -16: "nu_tau_bar",
    # Gauge bosons + Higgs
    22: "photon",
    24: "W+",
    -24: "W-",
    23: "Z0",
    21: "gluon",
    25: "Higgs",
    # Mesons
    111: "pion0",
    211: "pion+",
    -211: "pion-",
    321: "kaon+",
    -321: "kaon-",
    311: "K-short",  # K0
    -311: "K-short",  # K0bar → K-short (no K-long in catalog)
    310: "K-short",
    130: "K-short",
    221: "eta",
    113: "rho0",
    # Baryons
    2212: "proton",
    -2212: "anti-proton",
    2112: "neutron",
    -2112: "anti-neutron",
    3122: "Lambda",
    3222: "Sigma+",
    3112: "Sigma-",
    3212: "Lambda",  # Sigma0 → Lambda (no Sigma0 in catalog)
    3312: "Xi-",
    3322: "Xi-",  # Xi0 → Xi- (no Xi0 in catalog)
    3334: "Omega-",
    -3334: "Omega-",  # Omega+ → Omega- (no Omega+ in catalog)
    2224: "Delta++",
    2214: "Delta++",  # Delta+ → Delta++ (no Delta+ in catalog)
    2114: "Delta++",  # Delta0 → Delta++
    1114: "Delta++",  # Delta- → Delta++
    # Heavy flavour
    443: "J/psi",
    421: "D0",
    -421: "D0",
    411: "D0",  # D+ → D0 (no D+ in catalog)
    -411: "D0",
    521: "B+",
    -521: "B+",  # B- → B+
    511: "B0",
    -511: "B0",
}


def _pdg_to_type_name(pdg: int) -> str:
    """Map PDG code to internal type name. Uses signed lookup for particle/antiparticle."""
    return PDG_TO_TYPE.get(pdg, PDG_TO_TYPE.get(abs(pdg), "proton"))


def load_hdf5_events(
    filepath,
    max_particles=100,
    energy_scale=0.01,
    position_scale=1.0,
):
    """
    Load particle data from an HDF5 file (CMS/ATLAS open data format).

    Expected dataset keys: 'px', 'py', 'pz', 'E', 'pdgId'
    Optional position keys: 'x', 'y', 'z' or 'vx', 'vy', 'vz' (vertex).
    Each array has shape (N,) for N particles in the event.
    """
    with h5py.File(filepath, "r") as f:
        available_keys = list(f.keys())
        print(f"HDF5 keys: {available_keys}")

        if "px" in f and "py" in f and "pz" in f:
            px = np.array(f["px"][:max_particles], dtype=np.float32)
            py = np.array(f["py"][:max_particles], dtype=np.float32)
            pz = np.array(f["pz"][:max_particles], dtype=np.float32)
        else:
            print("Required momentum keys (px, py, pz) not found.")
            return 0

        # Optional per-particle positions
        has_xyz = "x" in f and "y" in f and "z" in f
        has_vertex = "vx" in f and "vy" in f and "vz" in f
        if has_xyz:
            rx = np.array(f["x"][:max_particles], dtype=np.float32)
            ry = np.array(f["y"][:max_particles], dtype=np.float32)
            rz = np.array(f["z"][:max_particles], dtype=np.float32)
        elif has_vertex:
            rx = np.array(f["vx"][:max_particles], dtype=np.float32)
            ry = np.array(f["vy"][:max_particles], dtype=np.float32)
            rz = np.array(f["vz"][:max_particles], dtype=np.float32)
        else:
            rx = ry = rz = None

        pdg_ids = None
        if "pdgId" in f:
            pdg_ids = np.array(f["pdgId"][:max_particles], dtype=np.int32)
        elif "pid" in f:
            pdg_ids = np.array(f["pid"][:max_particles], dtype=np.int32)

        count = 0
        for i in range(len(px)):
            type_name = "proton"
            if pdg_ids is not None:
                pdg = int(pdg_ids[i])
                type_name = _pdg_to_type_name(pdg)

            tid = get_type_id_by_name(type_name)
            if tid < 0:
                tid = 0

            if rx is not None:
                position = (
                    float(rx[i]) * position_scale,
                    float(ry[i]) * position_scale,
                    float(rz[i]) * position_scale,
                )
            else:
                position = (0.0, 0.0, 0.0)

            velocity = (
                float(px[i]) * energy_scale,
                float(py[i]) * energy_scale,
                float(pz[i]) * energy_scale,
            )
            sim.add_particle(position, velocity, tid)
            count += 1

        print(f"Loaded {count} particles from {filepath}")
        return count


def load_csv_events(
    filepath,
    max_particles=100,
    energy_scale=0.01,
    position_scale=1.0,
):
    """
    Load particle data from a CSV file.

    Required columns: px, py, pz
    Optional columns: pdgId, x, y, z (or vx, vy, vz for vertex)
    """
    data = np.genfromtxt(filepath, delimiter=",", names=True, max_rows=max_particles)
    data = np.atleast_1d(data)  # single row yields 0-d array, ensure iterable

    dtype_names = list(data.dtype.names) if data.dtype.names else []
    has_xyz = "x" in dtype_names and "y" in dtype_names and "z" in dtype_names
    has_vertex = "vx" in dtype_names and "vy" in dtype_names and "vz" in dtype_names

    count = 0
    for row in data:
        pdg = int(row["pdgId"]) if "pdgId" in dtype_names else 2212
        type_name = _pdg_to_type_name(pdg)
        tid = get_type_id_by_name(type_name)
        if tid < 0:
            tid = 0

        if has_xyz:
            position = (
                float(row["x"]) * position_scale,
                float(row["y"]) * position_scale,
                float(row["z"]) * position_scale,
            )
        elif has_vertex:
            position = (
                float(row["vx"]) * position_scale,
                float(row["vy"]) * position_scale,
                float(row["vz"]) * position_scale,
            )
        else:
            position = (0.0, 0.0, 0.0)

        velocity = (
            float(row["px"]) * energy_scale,
            float(row["py"]) * energy_scale,
            float(row["pz"]) * energy_scale,
        )
        sim.add_particle(position, velocity, tid)
        count += 1

    print(f"Loaded {count} particles from {filepath}")
    return count
