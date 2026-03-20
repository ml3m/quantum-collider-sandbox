================================================================================
Usage Guide
================================================================================

How to use Quantum Collider Sandbox for simulation, exploration, and analysis.

Starting the Simulation
=======================

**Basic startup:**

.. code-block:: bash

   make run

Or directly:

.. code-block:: bash

   python -m quantum_collider_sandbox

**With command-line options:**

.. code-block:: bash

   python -m quantum_collider_sandbox \
      --preset lhc_pp \
      --particles 50 \
      --width 1920 \
      --height 1200

**Available CLI options:**

- ``--preset NAME`` — Load preset ("default", "lhc_pp", "black_hole", etc.)
- ``--particles N`` — Spawn N particles on startup
- ``--width W`` — Window width (pixels)
- ``--height H`` — Window height (pixels)
- ``--fullscreen`` — Launch in fullscreen mode
- ``--backend BACKEND`` — GPU backend ("vulkan", "cuda", "cpu", "metal")


Basic Workflow
==============

**1. Explore a preset:**

1. Launch with ``make run``
2. From ImGui left panel, select "Presets" dropdown
3. Pick one (e.g., "Cyclotron")
4. Watch simulation play (SPACE to pause/resume)
5. Rotate camera with right-mouse drag
6. Zoom with mouse scroll

**2. Adjust parameters in real-time:**

1. Find slider in ImGui (e.g., "Coulomb K")
2. Drag to new value
3. See effect immediately (forces recalculate each frame)
4. Adjust Substeps if motion looks jerky

**3. Export results:**

.. code-block:: bash

   # Save current state to HDF5
   Ctrl+S

   # Export physics events to JSONL
   Ctrl+Shift+J

   # Files go to data/exports/ and data/logs/

**4. Analyze output:**

.. code-block:: python

   import h5py
   import json

   # Load state
   with h5py.File("data/exports/state_1234567.h5", "r") as f:
       particles = f["particles"][:]
       positions = f["positions"][:]

   # Read physics log
   with open("data/logs/physics_1234567.jsonl") as f:
       for line in f:
           event = json.loads(line)
           if event["type"] == "collision":
               print(f"Collision: {event['particle_a']} + {event['particle_b']}")


Common Tasks
============

**Spawn specific particle type:**

1. Press ``+`` to spawn random particle
2. Use Python API directly (see below)

**Create high-energy collision:**

1. Select "LHC pp" or "e⁺e⁻" preset
2. Watch beams collide
3. Adjust forces if desired

**Study gravitational dynamics:**

1. Select "N-Body Virial" preset
2. Watch self-gravitating cluster
3. Adjust G slider to change strength

**Test Coulomb scattering:**

1. Select "Rutherford" preset
2. Observe scattering angles vs impact parameter
3. Adjust K to strengthen/weaken repulsion

**Record trajectory data:**

1. Run simulation
2. Press ``Ctrl+S`` periodically to snapshot states
3. Load and analyze in Python (see examples below)


Python API Usage
================

You can script simulations and analysis in Python:

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation
   from quantum_collider_sandbox.config import Config
   import numpy as np

   # Initialize simulation
   sim = Simulation(preset="default")

   # Run for N timesteps
   for step in range(1000):
       sim.step()
       if step % 100 == 0:
           ke = sim.compute_kinetic_energy()
           print(f"Step {step}: KE = {ke:.2f}")

   # Get particle data
   positions = sim.get_particle_positions()
   velocities = sim.get_particle_velocities()
   types = sim.get_particle_types()

   print(f"Total particles: {len(types)}")
   print(f"Avg velocity: {np.mean(np.linalg.norm(velocities, axis=1)):.2f}")


Data Export & Import
====================

**Export current state:**

ImGui panel → "Save State" button, or press ``Ctrl+S``

This creates an HDF5 file with:
   - Particle positions, velocities, types
   - Force parameters at export time
   - Timestamp metadata

**Import previous state:**

Press ``Ctrl+L`` and select an HDF5 file from ``data/exports/``

Simulation will resume from that configuration.

**Export physics events:**

Press ``Ctrl+Shift+J`` to log all physics events to JSONL

Logged events include:
   - Collisions (type A + type B → products)
   - Decays (X → Y + Z + ...)
   - Pair creations
   - Boundary interactions

**Analyze events in Python:**

.. code-block:: python

   import json

   with open("data/logs/physics_events.jsonl") as f:
       collisions = []
       for line in f:
           event = json.loads(line)
           if event["type"] == "collision":
               collisions.append(event)

   print(f"Total collisions: {len(collisions)}")
   for coll in collisions[:5]:
       print(f"  {coll['particle_a']} + {coll['particle_b']} → {coll['products']}")


Performance Monitoring
======================

**In-window stats:**

The ImGui left panel shows real-time statistics:

- **FPS** — Frames per second (target ≥ 30)
- **Frame Time** — Milliseconds per frame
- **Particle Count** — Active particles (update per step)
- **Kinetic Energy** — Total KE summed over particles
- **Momentum** — Total momentum magnitude |**p**|
- **Avg Velocity** — Mean speed across particles

**If FPS drops:**

1. See :ref:`Performance Tuning <performance>` section
2. Common fixes:
   - Reduce TRAIL_LENGTH (Press T to bypass trails)
   - Reduce particle count
   - Lower rendered resolution


Advanced: Batch Scripting
=========================

Run multiple simulations automatically:

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation
   import json

   results = []

   # Sweep over Coulomb strength
   for k in [10, 20, 40, 80]:
       config = {"coulomb_k": k}
       sim = Simulation(preset="rutherford", config_override=config)

       for step in range(500):
           sim.step()

       # Record final state
       results.append({
           "coulomb_k": k,
           "final_particles": sim.num_particles,
           "final_ke": sim.compute_kinetic_energy(),
       })

   # Save results
   with open("sweep_results.json", "w") as f:
       json.dump(results, f, indent=2)


Tips & Tricks
=============

**Faster frame rate:**

- Reduce window resolution (WINDOW_WIDTH, WINDOW_HEIGHT in config)
- Disable trails (T key)
- Reduce trail length (TRAIL_LENGTH in config; Phase 1: try 5-20)
- Fewer particles (use +/- keys or IMGui slider)

**Better camera angles:**

- Right-mouse drag to rotate
- Scroll wheel to zoom
- Pan with middle-mouse (or Shift+right-drag)
- Reset to default: R key (but particles reset too!)

**Inspect a specific particle:**

- Hover over particle in 3D view
- Click to select (if implemented)
- Inspector panel shows type, mass, lifetime, trajectory

**Slow-motion analysis:**

- Pause (SPACE)
- Advance frame-by-frame with arrow keys (if implemented)
- Or reduce DT and SUBSTEPS in config for slower speed

**Record for video:**

1. Pause simulation (SPACE)
2. Set up desired initial state
3. Press Ctrl+S to snapshot
4. Use FFmpeg or OBS to capture screen:
   
   .. code-block:: bash

      ffmpeg -f x11grab -i :0 -vcodec libx264 -crf 0 recording.mp4

