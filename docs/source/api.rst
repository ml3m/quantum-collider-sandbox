================================================================================
Python API Reference
================================================================================

Public Python API for scripting and extending the simulation.

Simulation Class
================

Main simulation interface:

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation

   sim = Simulation(preset="default", particles=20)

**Constructor Parameters:**

- ``preset`` (str) — Name of preset ("default", "lhc_pp", "black_hole", etc.)
- ``particles`` (int) — Initial particle count (0-100)
- ``config_override`` (dict) — Override config parameters as key-value pairs

**Methods:**

.. code-block:: python

   # Main simulation loop
   sim.step()  # Advance by one timestep
   sim.reset()  # Reinitialize with current preset

   # Particle management
   sim.add_particle(x, y, z, vx, vy, vz, particle_type="electron")
   sim.remove_particle(index)
   sim.get_particle_count()
   sim.get_particle_positions()  # Returns Nx3 numpy array
   sim.get_particle_velocities()  # Returns Nx3 numpy array
   sim.get_particle_types()  # Returns N integers (PDG IDs)

   # Physics queries
   sim.compute_kinetic_energy()  # Total KE (float)
   sim.compute_momentum()  # Total momentum magnitude (float)
   sim.get_forces()  # Current force vector per particle (Nx3)

   # State I/O
   sim.save_state(filename)  # Export to HDF5
   sim.load_state(filename)  # Import from HDF5
   sim.export_events(filename)  # Save physics log to JSONL

**Example:**

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation
   import numpy as np

   # Create sim
   sim = Simulation(preset="lhc_pp", particles=40)

   # Run 100 steps
   energies = []
   for step in range(100):
       sim.step()
       energies.append(sim.compute_kinetic_energy())

   # Plot results
   import matplotlib.pyplot as plt
   plt.plot(energies)
   plt.ylabel("Kinetic Energy (au)")
   plt.xlabel("Timestep")
   plt.show()


Configuration Module
====================

Access and override configuration at runtime:

.. code-block:: python

   from quantum_collider_sandbox import config

   # Read current values
   print(config.COULOMB_K)  # 40.0
   print(config.GRAVITY_G)  # 6.0
   print(config.TRAIL_LENGTH)  # 40

   # Override before creating Simulation
   config.TRAIL_LENGTH = 20
   config.COULOMB_K = 80.0
   sim = Simulation(preset="default")  # Uses overridden values

**Key configuration constants:**

- Physics: ``DT, SUBSTEPS, INTEGRATOR, USE_RELATIVITY``
- Forces: ``COULOMB_K, GRAVITY_G, STRONG_FORCE_K, MAGNETIC_FIELD, E_FIELD``
- Rendering: ``WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_POS, BASE_PARTICLE_RADIUS``
- Trails (Phase 1): ``TRAIL_LENGTH, MIN_TRAIL_SPEED_FOR_RENDER, MIN_TRAIL_LENGTH_FOR_RENDER``
- Presets: ``PRESETS`` dict


Particle Data Group (PDG) Table
===============================

Access particle properties:

.. code-block:: python

   from quantum_collider_sandbox.pdg_table import (
       PARTICLES,
       PDG_PARTICLES,
       get_particle_mass,
       get_particle_lifetime,
       get_particle_color,
   )

   # Get particle by name
   electron = PARTICLES["electron"]
   print(electron["mass"])  # Rest mass (MeV/c²)
   print(electron["lifetime"])  # Proper lifetime (seconds)
   print(electron["charge"])  # Electric charge (units of e)
   print(electron["decay_channels"])  # List of decay modes

   # Get by PDG ID
   pdg = 11  # electron
   props = PDG_PARTICLES.get(pdg)

   # Global functions
   mass = get_particle_mass("muon")
   lifetime = get_particle_lifetime("pion")
   color = get_particle_color("electron")  # RGB tuple


Data Loader Module
==================

Import/export simulation state and events:

.. code-block:: python

   from quantum_collider_sandbox.data_loader import DataLoader

   loader = DataLoader()

   # Export state to HDF5
   loader.export_state(
       particles=sim.get_particles(),
       filename="state.h5"
   )

   # Import state from HDF5
   particles = loader.import_state("state.h5")
   sim.load_particles(particles)

   # Log physics events
   loader.log_collision(
       particle_a_type=11,  # electron (PDG ID)
       particle_b_type=-11,  # positron
       products=[22, 22],  # two photons
       position=(0, 0, 0),
       timestamp=0.001
   )


Renderer Interface
==================

Advanced rendering control (for extensions):

.. code-block:: python

   from quantum_collider_sandbox.renderer import Renderer
   from quantum_collider_sandbox.simulation import Simulation

   sim = Simulation(preset="default")
   renderer = Renderer(sim)

   # Main render loop
   while not renderer.should_close():
       renderer.handle_input()
       sim.step()
       renderer.render()

   renderer.close()

**Methods:**

- ``handle_input()`` — Process keyboard/mouse
- ``render()`` — Draw current frame
- ``update_camera(pos, lookat, fov)`` — Change view
- ``set_overlay_text(text)`` — Display debug info
- ``should_close()`` — Check window close button


Example: Custom Simulation Loop
================================

.. code-block:: python

   import numpy as np
   from quantum_collider_sandbox.simulation import Simulation
   from quantum_collider_sandbox import config

   # Custom configuration
   config.COULOMB_K = 100.0
   config.GRAVITY_G = 0.0  # Disable gravity
   config.TRAIL_LENGTH = 20  # Phase 1 optimization
   config.MIN_TRAIL_SPEED_FOR_RENDER = 0.1

   # Create and run
   sim = Simulation(preset="playground", particles=50)

   results = {
       "time": [],
       "energy": [],
       "momentum": [],
       "particle_count": [],
   }

   for t in range(1000):
       sim.step()

       if t % 10 == 0:
           results["time"].append(t * config.DT)
           results["energy"].append(sim.compute_kinetic_energy())
           results["momentum"].append(sim.compute_momentum())
           results["particle_count"].append(sim.get_particle_count())

   # Save and analyze
   sim.export_events("events.jsonl")
   sim.save_state("final_state.h5")

   # Plot
   import matplotlib.pyplot as plt
   plt.figure(figsize=(12, 4))

   plt.subplot(1, 3, 1)
   plt.plot(results["time"], results["energy"])
   plt.ylabel("Energy (au)")
   plt.xlabel("Time (sim units)")

   plt.subplot(1, 3, 2)
   plt.plot(results["time"], results["momentum"])
   plt.ylabel("Momentum (au)")

   plt.subplot(1, 3, 3)
   plt.plot(results["time"], results["particle_count"])
   plt.ylabel("N particles")

   plt.tight_layout()
   plt.savefig("results.png", dpi=150)
   print("Saved results.png")


Example: Batch Parameter Sweep
===============================

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation
   from quantum_collider_sandbox import config
   import json

   # Sweep Coulomb strength
   results = []

   for k in [10, 20, 40, 80, 160]:
       config.COULOMB_K = k
       sim = Simulation(preset="rutherford", particles=30)

       energies = []
       for step in range(500):
           sim.step()
           if step % 10 == 0:
               energies.append(sim.compute_kinetic_energy())

       results.append({
           "coulomb_k": k,
           "avg_energy": np.mean(energies),
           "final_particles": sim.get_particle_count(),
       })

   # Save and display
   with open("coulomb_sweep.json", "w") as f:
       json.dump(results, f, indent=2)

   for r in results:
       print(f"K={r['coulomb_k']}: Energy={r['avg_energy']:.2f}, "
             f"Particles={r['final_particles']}")


Extending the Simulation
========================

**Add custom force:**

1. Edit ``simulation.py``
2. Add kernel to ``compute_forces()``
3. Update config with new constant

**Add custom preset:**

1. Edit ``config.py``
2. Add entry to ``PRESETS`` dict:

   .. code-block:: python

      PRESETS["my_preset"] = {
          "preset_name": "My Custom Experiment",
          "initial_particles": 25,
          "coulomb_k": 50.0,
          # ... other params
      }

3. Reference in UI dropdown

**Add new particle type:**

1. Edit ``pdg_table.py``
2. Add entry to ``PARTICLES`` dict with mass, lifetime, decay channels
3. Assign unique PDG ID and color

See :ref:`Development <development>` guide for more extending details.


Thread Safety Notes
===================

**NOT thread-safe:**

- Taichi kernels automatically parallelize on GPU (internal)
- Python API is single-threaded
- Don't call ``sim.step()`` from multiple threads

**Safe patterns:**

- Single main loop calling ``sim.step()`` sequentially
- Multiple simulations in separate processes (not threads)
- Parallel parameter sweeps via separate Python processes


Performance Tips
================

**Efficient data access:**

- Call ``get_particle_positions()`` once per frame, not per particle
- Batch multiple steps before exporting state

**Minimize config changes:**

- Set config before creating Simulation
- Changing config at runtime has minimal cost but is not recommended

**For GPU operations:**

- Taichi kernels are JIT-compiled on first call (slow)
- Subsequent calls are fast
- Use reasonable timestep (DT) to avoid numerical issues


Debugging
=========

**Enable internal logging:**

.. code-block:: bash

   export TAICHI_LOG_LEVEL=debug
   python -m quantum_collider_sandbox

**Print simulation state:**

.. code-block:: python

   print(f"Particles: {sim.get_particle_count()}")
   print(f"Energy: {sim.compute_kinetic_energy():.4f}")
   print(f"Momentum: {sim.compute_momentum():.4f}")

   # First 10 particles
   pos = sim.get_particle_positions()
   print(pos[:10])

