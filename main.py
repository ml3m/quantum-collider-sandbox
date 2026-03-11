#!/usr/bin/env python3
"""
Quantum Collider Sandbox - Real-Time GPU Particle Physics Simulation

Usage:
    python main.py                     Default demo (head-on collision scenario)
    python main.py --particles 100     Start with N random particles
    python main.py --data event.h5     Load particles from HDF5 file

Controls:
    SPACE       Pause / Resume
    R           Reset to demo state
    C           Spawn head-on collision (two heavy_x)
    T           Toggle trails
    F           Toggle collision flashes
    E           Export state + time series to HDF5
    G           Toggle particle gun
    TAB         Cycle inspector to next particle
    P           Pin/freeze selected particle
    1           Preset: Rutherford scattering
    2           Preset: Cyclotron (magnetic field spirals)
    3           Preset: Random gas with gravity
    4           Preset: Two-beam collision
    RMB+drag    Orbit camera
    Scroll      Zoom
    ESC         Quit
"""

import argparse
import random
import time
import taichi as ti

ti.init(arch=ti.vulkan)

from particles import load_particle_data
from simulation import init_simulation, add_particle, step, do_maintenance, refresh_stats
from renderer import Renderer
from config import PARTICLE_TYPES


def setup_demo():
    add_particle((-3.5, 0.0, 0.0), (3.0, 0.3, 0.0), 7)
    add_particle((3.5, 0.0, 0.0), (-3.0, -0.3, 0.0), 7)
    add_particle((0.0, 3.5, 0.0), (-1.2, -1.8, 0.0), 0)
    add_particle((0.0, -3.5, 0.0), (1.2, 1.8, 0.0), 0)
    add_particle((3.0, 3.0, 0.0), (-2.0, -1.0, 0.5), 2)
    add_particle((-3.0, -3.0, 0.0), (2.0, 1.0, -0.5), 3)
    add_particle((1.5, -2.0, 1.0), (-0.8, 1.5, -0.4), 4)
    add_particle((-1.5, 2.0, -1.0), (0.8, -1.5, 0.4), 5)
    add_particle((4.0, 1.0, 0.5), (-1.5, -0.5, 0.0), 1)
    add_particle((-4.0, -1.0, -0.5), (1.5, 0.5, 0.0), 9)


def spawn_random_particles(count):
    type_ids = list(PARTICLE_TYPES.keys())
    for _ in range(count):
        tid = random.choice(type_ids)
        px = random.uniform(-6, 6)
        py = random.uniform(-6, 6)
        pz = random.uniform(-3, 3)
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        vz = random.uniform(-1, 1)
        add_particle((px, py, pz), (vx, vy, vz), tid)


def main():
    parser = argparse.ArgumentParser(description="Quantum Collider Sandbox")
    parser.add_argument("--data", type=str, help="Path to HDF5 event file")
    parser.add_argument("--particles", type=int, default=0,
                        help="Spawn N random particles on startup")
    args = parser.parse_args()

    load_particle_data()
    init_simulation()

    if args.data:
        from data_loader import load_hdf5_events
        load_hdf5_events(args.data)
    elif args.particles > 0:
        spawn_random_particles(args.particles)
    else:
        setup_demo()

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
                )
            do_maintenance(scaled_dt)
            renderer.fire_gun(real_dt)

        if frame % 10 == 0:
            refresh_stats(renderer.selected_particle)
        frame += 1

        renderer.render()


if __name__ == "__main__":
    main()
