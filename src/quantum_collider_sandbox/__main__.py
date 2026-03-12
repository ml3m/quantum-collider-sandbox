#!/usr/bin/env python3
"""
Quantum Collider Sandbox - Real-Time GPU Particle Physics Simulation.

PDG-accurate particle catalog with 40 observable particles, real masses,
lifetimes, decay channels with proper relativistic kinematics.

Usage:
    python -m quantum_collider_sandbox                        Default demo
    python -m quantum_collider_sandbox --particles 100        Start with N random
    python -m quantum_collider_sandbox --data      event.h5   Load from HDF5 file
    python -m quantum_collider_sandbox --log-physics          Log physics to data/logs/ for validation

Controls:
    SPACE       Pause / Resume
    R           Reset to demo state
    C           Spawn p + p-bar collision
    T           Toggle trails
    F           Toggle collision flashes
    Y           Toggle photon visibility
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
    8           Preset: Physics playground (gravity + E + B + relativity)
    9           Preset: N-body virial cluster (gravitational bound sphere)
    RMB+drag    Orbit camera
    Scroll      Zoom
    ESC         Quit
"""

import argparse
import json
import os
import random
import time
from pathlib import Path

import taichi as ti

ti.init(arch=ti.vulkan)

from . import config
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
    cached_stats,
    do_maintenance,
    init_simulation,
    refresh_stats,
    step,
    step_counter,
    update_accretion_disk,
)


def _setup_demo() -> None:
    """Create initial demo: projectiles under gravity, particles in E/B fields."""
    add_particle((-4.0, -2.0, 0.0), (3.0, 5.0, 0.2), PROTON)
    add_particle((4.0, -2.0, 0.0), (-3.0, 5.0, -0.2), ANTIPROTON)
    add_particle((-2.0, -3.0, 1.0), (2.0, 4.0, 0.0), PROTON)
    add_particle((2.0, -3.0, -1.0), (-2.0, 4.0, 0.0), NEUTRON)
    add_particle((0.0, 2.0, 0.0), (2.0, 0.0, 1.0), PI_PLUS)
    add_particle((0.0, -2.0, 0.0), (-2.0, 0.0, -1.0), PI_MINUS)
    add_particle((-3.0, 0.0, 2.0), (1.0, 3.0, -0.5), K_PLUS)
    add_particle((3.0, 0.0, -2.0), (-1.0, -3.0, 0.5), MUON_MINUS)
    add_particle((-1.0, 1.0, 0.0), (4.0, 2.0, 0.0), ELECTRON)
    add_particle((1.0, -1.0, 0.0), (-4.0, -2.0, 0.0), POSITRON)


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
    parser.add_argument(
        "--log-physics",
        action="store_true",
        help="Log physics metrics to data/logs/ for validation analysis",
    )
    args = parser.parse_args()

    # ImGui loads imgui.ini from cwd; ensure we run from project root
    project_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(project_root)
    # Delete imgui.ini so Taichi uses our normalized positions (panels stay on edges when resizing)
    (project_root / "imgui.ini").unlink(missing_ok=True)

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

    log_file = None
    if args.log_physics:
        log_dir = config.EXPORT_DIR.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"physics_{int(time.time())}.jsonl"
        log_file = open(log_path, "w", encoding="utf-8")
        print(f"Physics logging to {log_path}")

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
            if log_file:
                sub_dt = (
                    renderer.dt * renderer.time_scale / renderer.substeps
                )
                sim_time = step_counter[None] * sub_dt
                entry = {
                    "step": cached_stats.get("step", 0),
                    "sim_time": sim_time,
                    "ke": cached_stats.get("ke", 0),
                    "mom": cached_stats.get("mom", 0),
                    "mom_x": cached_stats.get("mom_x", 0),
                    "mom_y": cached_stats.get("mom_y", 0),
                    "mom_z": cached_stats.get("mom_z", 0),
                    "particles": cached_stats.get("particles", 0),
                    "collisions": cached_stats.get("collisions", 0),
                    "decays": cached_stats.get("decays", 0),
                    "annihilations": cached_stats.get("annihilations", 0),
                    "gravity_g": renderer.gravity_g,
                    "coulomb_k": renderer.coulomb_k,
                    "use_relativity": renderer.use_relativity,
                    "fps": renderer.fps,
                }
                log_file.write(json.dumps(entry) + "\n")
                log_file.flush()
        frame += 1

        renderer.render()

    if log_file:
        log_file.close()


if __name__ == "__main__":
    main()
