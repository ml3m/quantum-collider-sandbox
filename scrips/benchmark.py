#!/usr/bin/env python3
"""
Benchmark script for Quantum Collider Sandbox performance profiling.

Runs simulation headless for a fixed number of frames and measures fps/time.
"""

import argparse
import os
import random
import time
from pathlib import Path

import taichi as ti

# Set architecture before importing anything else
_ARCH_MAP = {"vulkan": ti.vulkan, "cuda": ti.cuda, "cpu": ti.cpu, "gpu": ti.gpu}
_arch_name = os.environ.get("QUANTUM_COLLIDER_ARCH", "vulkan").lower()
ti.init(arch=_ARCH_MAP.get(_arch_name, ti.vulkan))

# Now import project modules
from src.quantum_collider_sandbox import config
from src.quantum_collider_sandbox.particles import load_particle_data
from src.quantum_collider_sandbox.pdg_table import PARTICLES as PDG_PARTICLES
from src.quantum_collider_sandbox.simulation import (
    add_particle,
    do_maintenance,
    init_simulation,
    step,
    refresh_stats,
    update_accretion_disk,
)


def spawn_random_particles(count: int) -> None:
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


def run_benchmark(particle_count: int, num_frames: int, show_output: bool = True):
    """
    Run simulation benchmark.
    
    Args:
        particle_count: Number of particles to spawn
        num_frames: Number of frames to simulate
        show_output: Whether to print progress
    """
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)
    
    load_particle_data()
    init_simulation()
    spawn_random_particles(particle_count)
    
    # Simulation parameters (from config)
    dt = config.DT
    substeps = config.SUBSTEPS
    coulomb_k = config.COULOMB_K
    gravity_g = config.GRAVITY_G
    mag_field = config.MAGNETIC_FIELD
    e_field = config.E_FIELD
    strong_k = config.STRONG_FORCE_K
    strong_range = config.STRONG_FORCE_RANGE
    use_relativity = config.USE_RELATIVITY
    c_light = config.SPEED_OF_LIGHT
    synchro = config.SYNCHROTRON_COEFF
    boundary_mode = config.BOUNDARY_MODE
    boundary_size = config.BOUNDARY_SIZE
    pair_threshold = config.PAIR_CREATION_THRESHOLD
    
    # Run warmup frames
    for _ in range(5):
        scaled_dt = dt * 1.0
        sub_dt = scaled_dt / substeps
        for _ in range(substeps):
            step(
                sub_dt,
                coulomb_k, gravity_g,
                mag_field,
                e_field,
                strong_k, strong_range,
                use_relativity, c_light,
                synchro, boundary_mode, boundary_size, pair_threshold,
                bh_on=False, bh_gm=0.0, bh_rs=0.0, bh_pos=(0.0, 0.0, 0.0),
            )
        do_maintenance(scaled_dt)
    
    # Run benchmark
    start_time = time.time()
    frame_times = []
    
    for frame in range(num_frames):
        frame_start = time.time()
        
        scaled_dt = dt * 1.0
        sub_dt = scaled_dt / substeps
        for _ in range(substeps):
            step(
                sub_dt,
                coulomb_k, gravity_g,
                mag_field,
                e_field,
                strong_k, strong_range,
                use_relativity, c_light,
                synchro, boundary_mode, boundary_size, pair_threshold,
                bh_on=False, bh_gm=0.0, bh_rs=0.0, bh_pos=(0.0, 0.0, 0.0),
            )
        do_maintenance(scaled_dt)
        
        # Refresh stats every 10 frames
        if frame % 10 == 0:
            refresh_stats(-1, use_rel=use_relativity, c_light=c_light)
        
        frame_time = time.time() - frame_start
        frame_times.append(frame_time)
        
        if show_output and frame % 10 == 0:
            fps = 1.0 / frame_time if frame_time > 0 else 0
            print(f"  Frame {frame:3d}: {frame_time*1000:6.2f}ms ({fps:6.1f} FPS)")
    
    total_time = time.time() - start_time
    avg_time = total_time / num_frames
    avg_fps = num_frames / total_time if total_time > 0 else 0
    
    return {
        "particle_count": particle_count,
        "num_frames": num_frames,
        "total_time_s": total_time,
        "avg_frame_time_ms": avg_time * 1000.0,
        "avg_fps": avg_fps,
        "min_frame_time_ms": min(frame_times) * 1000.0,
        "max_frame_time_ms": max(frame_times) * 1000.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark Quantum Collider Sandbox")
    parser.add_argument(
        "--particles",
        type=int,
        nargs="+",
        default=[100, 500, 1000, 2000],
        help="Particle counts to benchmark (default: 100 500 1000 2000)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=100,
        help="Number of frames per benchmark (default: 100)",
    )
    
    args = parser.parse_args()
    
    print(f"Quantum Collider Sandbox Benchmark")
    print(f"Frames per test: {args.frames}")
    print(f"SUBSTEPS={config.SUBSTEPS}, TRAIL_LENGTH={config.TRAIL_LENGTH}, SOFTENING={config.SOFTENING}")
    print(f"INTEGRATOR={config.INTEGRATOR}")
    print()
    
    results = []
    for n in sorted(args.particles):
        print(f"Benchmarking N={n}...")
        result = run_benchmark(n, args.frames)
        results.append(result)
        print(f"  Average: {result['avg_frame_time_ms']:.2f} ms ({result['avg_fps']:.1f} FPS)")
        print(f"  Min/Max: {result['min_frame_time_ms']:.2f} / {result['max_frame_time_ms']:.2f} ms")
        print()
    
    # Summary table
    print("Summary:")
    print(f"{'Particles':<12} {'Avg Time (ms)':<15} {'FPS':<10} {'Min/Max (ms)':<20}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['particle_count']:<12} "
            f"{r['avg_frame_time_ms']:<15.2f} "
            f"{r['avg_fps']:<10.1f} "
            f"{r['min_frame_time_ms']:.2f} / {r['max_frame_time_ms']:.2f}"
        )


if __name__ == "__main__":
    main()
