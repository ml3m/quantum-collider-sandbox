#!/usr/bin/env python3
"""
FPS Benchmark for Quantum Collider Sandbox
Measures rendering performance across different particle counts and configurations.
"""

import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from quantum_collider_sandbox import simulation as sim
from quantum_collider_sandbox import renderer
from quantum_collider_sandbox.config import (
    PROTON, ELECTRON, NEUTRON, PI_PLUS, PHOTON, ANTIPROTON
)


def run_fps_benchmark(particle_counts=(100, 500, 1000, 2000), duration_secs=10):
    """
    Run FPS benchmark across different particle counts.
    
    Args:
        particle_counts: Tuple of particle counts to test
        duration_secs: Duration (in seconds) to measure FPS for each count
    
    Returns:
        Dictionary with benchmark results
    """
    results = {}
    
    for count in particle_counts:
        print(f"\n{'='*60}")
        print(f"Benchmarking with {count} particles...")
        print(f"{'='*60}")
        
        # Initialize simulation with specific particle count
        sim.init_simulation()
        sim.set_particle_count(count)
        
        # Spawn particles (balanced mix)
        types = [PROTON, ELECTRON, NEUTRON, PI_PLUS, ANTIPROTON]
        for i in range(count):
            ptype = types[i % len(types)]
            x = (i % 20 - 10) * 0.8
            y = ((i // 20) % 20 - 10) * 0.8
            z = ((i // 400) % 5 - 2) * 0.8
            vx = (i % 3 - 1) * 2.0
            vy = ((i // 3) % 3 - 1) * 2.0
            vz = ((i // 9) % 3 - 1) * 1.0
            sim.add_particle((x, y, z), (vx, vy, vz), ptype)
        
        # Create renderer
        r = renderer.Renderer()
        
        # Warm up: 20 frames to stabilize
        print(f"Warming up (20 frames)...", end="", flush=True)
        for _ in range(20):
            if not sim.paused:
                for _ in range(r.substeps):
                    sim.do_step(
                        r.dt * r.time_scale,
                        r.coulomb_k,
                        r.gravity_g,
                        r.mag_field,
                        r.e_field,
                        r.strong_k,
                        r.strong_range,
                        r.use_relativity,
                        r.c_light,
                        r.synchro,
                        r.pair_threshold,
                    )
            r.handle_input()
            r.render()
        print(" done!")
        
        # Measure FPS over duration
        print(f"Measuring FPS ({duration_secs}s)...", end="", flush=True)
        fps_samples = []
        elapsed = 0.0
        frame_count = 0
        start_time = time.time()
        
        while elapsed < duration_secs:
            frame_start = time.time()
            
            # Physics step
            if not sim.paused:
                for _ in range(r.substeps):
                    sim.do_step(
                        r.dt * r.time_scale,
                        r.coulomb_k,
                        r.gravity_g,
                        r.mag_field,
                        r.e_field,
                        r.strong_k,
                        r.strong_range,
                        r.use_relativity,
                        r.c_light,
                        r.synchro,
                        r.pair_threshold,
                    )
            
            # Rendering
            r.handle_input()
            r.render()
            
            frame_time = time.time() - frame_start
            if frame_time > 0:
                fps = 1.0 / frame_time
                fps_samples.append(fps)
            
            elapsed = time.time() - start_time
            frame_count += 1
        
        print(" done!")
        
        # Close window
        r.window.running = False
        r.window.destroy()
        
        # Calculate statistics
        if fps_samples:
            avg_fps = sum(fps_samples) / len(fps_samples)
            min_fps = min(fps_samples)
            max_fps = max(fps_samples)
            median_fps = sorted(fps_samples)[len(fps_samples) // 2]
            
            results[count] = {
                "avg_fps": round(avg_fps, 2),
                "min_fps": round(min_fps, 2),
                "max_fps": round(max_fps, 2),
                "median_fps": round(median_fps, 2),
                "frame_count": frame_count,
                "duration_secs": round(elapsed, 2),
            }
            
            print(f"\nResults for {count} particles:")
            print(f"  Average FPS:  {avg_fps:.2f}")
            print(f"  Median FPS:   {median_fps:.2f}")
            print(f"  Min FPS:      {min_fps:.2f}")
            print(f"  Max FPS:      {max_fps:.2f}")
            print(f"  Frames:       {frame_count} in {elapsed:.2f}s")
    
    return results


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Quantum Collider Sandbox — FPS Benchmark (Phase 1)       ║")
    print("║  Optimized Trail Rendering (TRAIL_LENGTH=40)             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Run benchmark
    results = run_fps_benchmark(particle_counts=(500, 1000, 2000), duration_secs=10)
    
    # Save results
    results_file = Path(__file__).parent / "benchmark_results_phase1.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {results_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for count, stats in sorted(results.items()):
        print(f"{count:4d} particles: {stats['avg_fps']:6.2f} FPS (median: {stats['median_fps']:.2f})")
