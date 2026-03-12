#!/usr/bin/env python3
"""
Quantum Collider Sandbox - Real-Time GPU Particle Physics Simulation.

PDG-accurate particle catalog with 40 observable particles, real masses,
lifetimes, decay channels with proper relativistic kinematics.

Usage:
    python -m quantum_collider_sandbox                        Default demo
    python -m quantum_collider_sandbox --particles 100        Start with N random
    python -m quantum_collider_sandbox --data      event.h5   Load from HDF5 file

Controls:
    SPACE       Pause / Resume
    R           Reset to demo state
    C           Spawn p + p-bar collision
    T           Toggle trails
    F           Toggle collision flashes
    E           Export state + time series to HDF5
    B           Toggle black hole
    G           Toggle particle gun
    TAB         Cycle inspector to next particle
    P           Pin/freeze selected particle
    1           Preset: Rutherford scattering
    2           Preset: Cyclotron (magnetic field spirals)
    3           Preset: Random gas with gravity
    4           Preset: Two-beam collision
    5           Preset: Black hole orbits
    6           Preset: LHC pp collision
    7           Preset: e+e- annihilation
    RMB+drag    Orbit camera
    Scroll      Zoom
    ESC         Quit
"""

import argparse
import random
import time

import taichi as ti

ti.init(arch=ti.vulkan)

from .particles import load_particle_data
from .pdg_table import (
    ANTIPROTON,
    ELECTRON,
    K_PLUS,
    MUON_MINUS,
    NEUTRON,
    PARTICLES as PDG_PARTICLES,
    PI_MINUS,
    PI_PLUS,
    POSITRON,
    PROTON,
)
from .renderer import Renderer
from .simulation import (
    add_particle,
    do_maintenance,
    init_simulation,
    refresh_stats,
    step,
    update_accretion_disk,
)


def _setup_demo() -> None:
    """Create initial demo particle configuration."""
    add_particle((-3.5, 0.0, 0.0), (3.0, 0.3, 0.0), PROTON)
    add_particle((3.5, 0.0, 0.0), (-3.0, -0.3, 0.0), ANTIPROTON)
    add_particle((0.0, 3.5, 0.0), (-1.2, -1.8, 0.0), PROTON)
    add_particle((0.0, -3.5, 0.0), (1.2, 1.8, 0.0), NEUTRON)
    add_particle((3.0, 3.0, 0.0), (-2.0, -1.0, 0.5), PI_PLUS)
    add_particle((-3.0, -3.0, 0.0), (2.0, 1.0, -0.5), PI_MINUS)
    add_particle((1.5, -2.0, 1.0), (-0.8, 1.5, -0.4), K_PLUS)
    add_particle((-1.5, 2.0, -1.0), (0.8, -1.5, 0.4), MUON_MINUS)
    add_particle((4.0, 1.0, 0.5), (-1.5, -0.5, 0.0), ELECTRON)
    add_particle((-4.0, -1.0, -0.5), (1.5, 0.5, 0.0), POSITRON)


def _spawn_random_particles(count: int) -> None:
    """Spawn N random particles from the PDG catalog."""
    type_ids = list(PDG_PARTICLES.keys())
    for _ in range(count):
        tid = random.choice(type_ids)
        px = random.uniform(-6, 6)
        py = random.uniform(-6, 6)
        pz = random.uniform(-3, 3)
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        vz = random.uniform(-1, 1)
        add_particle((px, py, pz), (vx, vy, vz), tid)


def main() -> None:
    """Run the main simulation loop."""
    parser = argparse.ArgumentParser(description="Quantum Collider Sandbox")
    parser.add_argument("--data", type=str, help="Path to HDF5 event file")
    parser.add_argument(
        "--particles",
        type=int,
        default=0,
        help="Spawn N random particles on startup",
    )
    args = parser.parse_args()

    load_particle_data()
    init_simulation()

    if args.data:
        from .data_loader import load_hdf5_events

        load_hdf5_events(args.data)
    elif args.particles > 0:
        _spawn_random_particles(args.particles)
    else:
        _setup_demo()

    renderer = Renderer()
    frame = 0
    last_frame_time = time.time()

    while renderer.running:
        now = time.time()
        real_dt = now - last_frame_time
        last_frame_time = now

        renderer.handle_input()

        if not renderer.paused:
            scaled_dt = renderer.dt * renderer.time_scale
            sub_dt = scaled_dt / renderer.substeps
            for _ in range(renderer.substeps):
                step(
                    sub_dt,
                    renderer.coulomb_k,
                    renderer.gravity_g,
                    renderer.mag_field,
                    renderer.e_field,
                    renderer.strong_k,
                    renderer.strong_range,
                    renderer.use_relativity,
                    renderer.c_light,
                    renderer.synchro,
                    renderer.boundary_mode,
                    renderer.boundary_size,
                    renderer.pair_threshold,
                    bh_on=renderer.bh_enabled,
                    bh_gm=renderer.bh_gm,
                    bh_rs=renderer.bh_rs,
                    bh_pos=renderer.bh_pos,
                )
            do_maintenance(scaled_dt)
            renderer.fire_gun(real_dt)
            if renderer.bh_enabled:
                update_accretion_disk(
                    scaled_dt,
                    renderer.bh_gm,
                    renderer.bh_rs,
                    renderer.bh_x,
                    renderer.bh_y,
                    renderer.bh_z,
                )

        if frame % 10 == 0:
            refresh_stats(renderer.selected_particle)
        frame += 1

        renderer.render()


if __name__ == "__main__":
    main()
