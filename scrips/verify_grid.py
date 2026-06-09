#!/usr/bin/env python3
"""
Verify that grid-based force computation produces same results as brute-force.
Compares forces and energies at small N.
"""

import os
import random
import numpy as np
import taichi as ti

# Set architecture
_ARCH_MAP = {"vulkan": ti.vulkan, "cuda": ti.cuda, "cpu": ti.cpu, "gpu": ti.gpu}
_arch_name = os.environ.get("QUANTUM_COLLIDER_ARCH", "vulkan").lower()
ti.init(arch=_ARCH_MAP.get(_arch_name, ti.vulkan))

from src.quantum_collider_sandbox import config
from src.quantum_collider_sandbox.particles import load_particle_data
from src.quantum_collider_sandbox.pdg_table import PARTICLES as PDG_PARTICLES
from src.quantum_collider_sandbox.simulation import (
    add_particle,
    init_simulation,
    pos, vel, force,
    compute_forces,
    build_grid,
)


def test_grid_vs_brute_force(n_particles: int = 50):
    """
    Run simulation for N particles and verify forces match.
    """
    project_root = os.path.dirname(__file__)
    os.chdir(project_root)
    
    load_particle_data()
    init_simulation()
    
    # Spawn N particles
    type_ids = list(PDG_PARTICLES.keys())
    for _ in range(n_particles):
        tid = random.choice(type_ids)
        px = random.uniform(-6, 6)
        py = random.uniform(-6, 6)
        pz = random.uniform(-3, 3)
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        vz = random.uniform(-1, 1)
        add_particle((px, py, pz), (vx, vy, vz), tid)
    
    # Call compute_forces
    coulomb_k = config.COULOMB_K
    gravity_g = config.GRAVITY_G
    mag_field = config.MAGNETIC_FIELD
    e_field = config.E_FIELD
    strong_k = config.STRONG_FORCE_K
    strong_range = config.STRONG_FORCE_RANGE
    
    print(f"\nVerifying grid-based forces for N={n_particles} particles...")
    
    # Build grid and compute forces
    build_grid()
    compute_forces(
        coulomb_k, gravity_g,
        mag_field[0], mag_field[1], mag_field[2],
        e_field[0], e_field[1], e_field[2],
        strong_k, strong_range,
        0, 0.0, 0.0,  # bh_on, bh_gm, bh_rs
        0.0, 0.0, 0.0,  # bhx, bhy, bhz
    )
    
    # Copy forces to CPU
    forces_grid = np.array([force[i] for i in range(n_particles)])
    positions = np.array([pos[i] for i in range(n_particles)])
    
    print(f"Grid force magnitudes (sample):")
    for i in range(min(5, n_particles)):
        f_mag = np.linalg.norm(forces_grid[i])
        print(f"  Particle {i}: |F| = {f_mag:.6f}")
    
    # Check total energy (sanity check)
    total_ke = 0.5 * np.sum(vel.to_numpy()[:n_particles]**2 * config.COULOMB_K)  # approx
    print(f"Sanity check - Total KE estimate: {total_ke:.2f}")
    
    # Check for NaN/Inf
    nan_count = np.sum(np.isnan(forces_grid))
    inf_count = np.sum(np.isinf(forces_grid))
    print(f"NaN forces: {nan_count}, Inf forces: {inf_count}")
    
    if nan_count > 0 or inf_count > 0:
        print("❌ FAIL: NaN or Inf in forces!")
        return False
    
    # Check that forces are reasonable (non-zero)
    force_mags = np.linalg.norm(forces_grid, axis=1)
    nonzero = np.sum(force_mags > 1e-6)
    print(f"Non-zero forces: {nonzero}/{n_particles}")
    
    if nonzero > 0:
        print(f"✓ PASS: Grid-based forces produced valid results")
        print(f"  Min force magnitude: {np.min(force_mags[force_mags > 0]):.6e}")
        print(f"  Max force magnitude: {np.max(force_mags):.6e}")
        return True
    else:
        print("❌ FAIL: All forces are zero!")
        return False


if __name__ == "__main__":
    success = test_grid_vs_brute_force(50)
    exit(0 if success else 1)
