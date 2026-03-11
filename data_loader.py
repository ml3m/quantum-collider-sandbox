import numpy as np
import h5py
import simulation as sim
from particles import get_type_id_by_name

PDG_TO_TYPE = {
    2212: "proton",
    -2212: "anti-proton",
    11: "electron",
    -11: "positron",
    211: "pion+",
    -211: "pion-",
    111: "pion0",
    321: "kaon+",
    -321: "kaon-",
    13: "muon",
    -13: "anti-muon",
    22: "photon",
    2112: "neutron",
    -2112: "anti-neutron",
    3122: "Lambda",
}


def load_hdf5_events(filepath, max_particles=100, energy_scale=0.01):
    """
    Load particle data from an HDF5 file (CMS/ATLAS open data format).

    Expected dataset keys: 'px', 'py', 'pz', 'E', 'pdgId'
    Each array has shape (N,) for N particles in the event.
    """
    with h5py.File(filepath, 'r') as f:
        available_keys = list(f.keys())
        print(f"HDF5 keys: {available_keys}")

        if 'px' in f and 'py' in f and 'pz' in f:
            px = np.array(f['px'][:max_particles], dtype=np.float32)
            py = np.array(f['py'][:max_particles], dtype=np.float32)
            pz = np.array(f['pz'][:max_particles], dtype=np.float32)
        else:
            print("Required momentum keys (px, py, pz) not found.")
            return 0

        pdg_ids = None
        if 'pdgId' in f:
            pdg_ids = np.array(f['pdgId'][:max_particles], dtype=np.int32)
        elif 'pid' in f:
            pdg_ids = np.array(f['pid'][:max_particles], dtype=np.int32)

        count = 0
        for i in range(len(px)):
            type_name = "proton"
            if pdg_ids is not None:
                pdg = int(pdg_ids[i])
                type_name = PDG_TO_TYPE.get(abs(pdg), "proton")

            tid = get_type_id_by_name(type_name)
            if tid < 0:
                tid = 0

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


def load_csv_events(filepath, max_particles=100, energy_scale=0.01):
    """
    Load particle data from a CSV file with columns: px, py, pz, pdgId
    """
    data = np.genfromtxt(filepath, delimiter=',', names=True, max_rows=max_particles)

    count = 0
    for row in data:
        pdg = int(row['pdgId']) if 'pdgId' in data.dtype.names else 2212
        type_name = PDG_TO_TYPE.get(abs(pdg), "proton")
        tid = get_type_id_by_name(type_name)
        if tid < 0:
            tid = 0

        velocity = (
            float(row['px']) * energy_scale,
            float(row['py']) * energy_scale,
            float(row['pz']) * energy_scale,
        )
        sim.add_particle((0.0, 0.0, 0.0), velocity, tid)
        count += 1

    print(f"Loaded {count} particles from {filepath}")
    return count
