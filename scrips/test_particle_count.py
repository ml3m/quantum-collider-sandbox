#!/usr/bin/env python3
"""Quick test of particle count control feature."""

import os
os.environ["QUANTUM_COLLIDER_ARCH"] = "cpu"  # Use CPU for headless testing

import taichi as ti
ti.init(arch=ti.cpu)

from src.quantum_collider_sandbox.particles import load_particle_data
from src.quantum_collider_sandbox.simulation import init_simulation, add_particle, set_particle_count, num_active
from src.quantum_collider_sandbox.pdg_table import PROTON

print("Testing particle count control...")

load_particle_data()
init_simulation()

# Test 1: Start with demo particles
for i in range(5):
    add_particle((float(i), 0.0, 0.0), (0.0, 0.0, 0.0), PROTON)

print(f"Initial particle count: {num_active[None]}")
assert num_active[None] == 5, "Should start with 5 particles"

# Test 2: Spawn more particles
print("\nSpawning to 20...")
set_particle_count(20)
print(f"After spawning: {num_active[None]}")
assert num_active[None] == 20, "Should have 20 particles"

# Test 3: Despawn particles
print("\nDespawning to 10...")
set_particle_count(10)
print(f"After despawning: {num_active[None]}")
assert num_active[None] == 10, "Should have 10 particles"

# Test 4: Spawn a lot
print("\nSpawning to 500...")
set_particle_count(500)
print(f"After spawning to 500: {num_active[None]}")
assert num_active[None] == 500, "Should have 500 particles"

print("\n✓ All tests passed!")
