================================================================================
Configuration Guide
================================================================================

Comprehensive guide to configuring the simulation via config.py.

Configuration Overview
======================

All simulation parameters are defined in ``config.py`` and can be customized by:

1. **Editing config.py directly** (permanent changes)
2. **ImGui sliders** (real-time, per session)
3. **Python API config_override** (programmatic)

For detailed parameter reference, see :ref:`Parameters <parameters>`.

File Structure
==============

.. code-block:: python

   # config.py is organized into sections:
   
   # 1. Integration & Timestep
   DT = 0.001
   SUBSTEPS = 4
   INTEGRATOR = "leapfrog"
   
   # 2. Physics Constants
   COULOMB_K = 40.0
   GRAVITY_G = 6.0
   SPEED_OF_LIGHT = 30.0
   USE_RELATIVITY = True
   
   # 3. Forces & Fields
   MAGNETIC_FIELD = (0.0, 0.0, 2.0)
   E_FIELD = (0.0, 1.0, 0.0)
   
   # 4. Rendering & Visualization
   WINDOW_WIDTH = 2560
   WINDOW_HEIGHT = 1600
   TRAIL_LENGTH = 40
   
   # 5. Presets
   PRESETS = { "default": {...}, ... }


Common Configuration Scenarios
===============================

**Scenario 1: Smooth motion at 1k particles**

.. code-block:: python

   DT = 0.001                           # Keep physics accurate
   SUBSTEPS = 4                         # More steps per frame
   TRAIL_LENGTH = 40                    # Full trails (Phase 1 optimized)
   COULOMB_K = 40.0                     # Normal Coulomb
   GRAVITY_G = 6.0                      # Gentle gravity
   MIN_TRAIL_SPEED_FOR_RENDER = 0.1     # All trails shown

   # Expected: 8-15 FPS


**Scenario 2: Very smooth motion, fewer particles (100)**

.. code-block:: python

   DT = 0.0005                          # Very fine timestep
   SUBSTEPS = 8                         # Many substeps
   TRAIL_LENGTH = 80                    # Extra-long trails
   COULOMB_K = 40.0
   GRAVITY_G = 6.0

   # Expected: 30-60 FPS


**Scenario 3: Fast and loose, 2k particles**

.. code-block:: python

   DT = 0.002                           # Faster timestep (less accurate)
   SUBSTEPS = 2                         # Fewer steps
   TRAIL_LENGTH = 20                    # Shorter trails (Phase 1 optimization)
   COULOMB_K = 20.0                     # Reduce forces for stability
   GRAVITY_G = 3.0
   MIN_TRAIL_SPEED_FOR_RENDER = 0.2     # Skip slower particles

   # Expected: 20-30 FPS


**Scenario 4: High-energy collisions (LHC)**

.. code-block:: python

   DT = 0.0005                          # Fine for accuracy
   SUBSTEPS = 6
   STRONG_FORCE_K = 50.0                # Strong force enabled
   COULOMB_K = 40.0
   USE_RELATIVITY = True                # Relativistic kinematics
   PAIR_CREATION_THRESHOLD = 15.0       # High-energy pairs

   # Expected: 5-15 FPS (many particles after collisions)


**Scenario 5: Real-time exploration, GPU-limited**

.. code-block:: python

   WINDOW_WIDTH = 1280                  # Cut resolution 40%
   WINDOW_HEIGHT = 720
   TRAIL_LENGTH = 10                    # Minimal trails
   TRAILS_ENABLED_DEFAULT = False       # Start with trails off
   SUBSTEPS = 2                         # Lower physics cost
   BASE_PARTICLE_RADIUS = 0.1           # Smaller particles to render faster

   # Expected: 30+ FPS even at 2k particles


Phase 1 Trail Optimization Guide
=================================

The TRAIL_LENGTH parameter is critical for performance. It controls:

- Vertex count per particle (4 segments/particle/frame → vertices-rendered)
- GPU memory for trail ring buffers
- Trail "smoothness" and visual quality

**Quick presets:**

.. list-table::
   :header-rows: 1

   * - Use Case
     - TRAIL_LENGTH
     - Particles
     - Expected FPS
     - Notes

   * - Smooth visualization
     - 40
     - 500
     - 30+
     - Default; good for exploration

   * - Moderate scaling
     - 40
     - 1k
     - 10-15
     - Phase 1 baseline

   * - Dense scenario
     - 20
     - 1k
     - 20-30
     - Half trails, still smooth

   * - Heavy scaling
     - 10
     - 1k
     - 30-60
     - Sparse trails, acceptable

   * - Extreme scaling
     - 5
     - 2k
     - 20-30
     - Minimal trails, dense particles

   * - Points only
     - 1
     - 5k
     - 60
     - No trails; just particles


Tuning for Different GPU Capabilities
======================================

**High-End GPU (RTX 3080+ or RX 6800+, 12GB+ VRAM)**

.. code-block:: python

   WINDOW_WIDTH = 3840        # 4K rendering
   WINDOW_HEIGHT = 2160
   TRAIL_LENGTH = 100         # Very long trails
   PARTICLE_RADIUS_SCALE = 1.0  # Show mass differences clearly
   CAMERA_FOV = 45            # Narrower for detail
   # Target: 2k-3k particles @ 60 FPS


**Mid-Range GPU (RTX 2080 / RX 5700, 6-8GB VRAM)**

.. code-block:: python

   WINDOW_WIDTH = 2560
   WINDOW_HEIGHT = 1600
   TRAIL_LENGTH = 40          # Phase 1 default
   PARTICLE_RADIUS_SCALE = 0.45
   CAMERA_FOV = 55            # Typical
   # Target: 1k-1.5k particles @ 30 FPS


**Entry-Level GPU (GTX 1660 / RX 6600, 2-4GB VRAM)**

.. code-block:: python

   WINDOW_WIDTH = 1920
   WINDOW_HEIGHT = 1080
   TRAIL_LENGTH = 20          # Reduced
   BASE_PARTICLE_RADIUS = 0.1
   PARTICLE_RADIUS_SCALE = 0.3
   # Target: 500-1k particles @ 30 FPS


**Integrated GPU (Intel iGPU, 0.5-1.5GB shared VRAM)**

.. code-block:: python

   WINDOW_WIDTH = 1280
   WINDOW_HEIGHT = 720
   TRAIL_LENGTH = 5           # Minimal
   TRAILS_ENABLED_DEFAULT = False  # Start with trails off
   SUBSTEPS = 1               # Single step per frame
   # Target: 100-300 particles @ 30 FPS


Force Configuration Examples
=============================

**Rutherford Scattering (strong Coulomb)**

.. code-block:: python

   COULOMB_K = 80.0           # Strong repulsion
   GRAVITY_G = 0.0            # NO gravity
   STRONG_FORCE_K = 0.0       # NO strong force
   # Interaction: Pure Coulomb only


**Stable Orbital System**

.. code-block:: python

   COULOMB_K = 0.0            # NO Coulomb (uncharged)
   GRAVITY_G = 8.0            # Strong gravity
   STRONG_FORCE_K = 0.0
   # Kinematics: Pure gravitational


**Magnetic Confinement (Cyclotron)**

.. code-block:: python

   COULOMB_K = 0.0
   GRAVITY_G = 0.0
   MAGNETIC_FIELD = (0, 0, 5.0)  # Strong B-field in z
   SYNCHROTRON_COEFF = 0.5    # Add damping
   # Interaction: Lorentz force only


**Balanced (Default)**

.. code-block:: python

   COULOMB_K = 40.0           # Moderate
   GRAVITY_G = 6.0            # Moderate
   STRONG_FORCE_K = 0.0       # Off by default
   # Interaction: Both EM and gravity


Physics Accuracy vs. Performance
=================================

Trade performance against accuracy:

**For maximum accuracy:**

.. code-block:: python

   DT = 0.0001                # Very small timestep
   SUBSTEPS = 10              # Many steps per frame
   INTEGRATOR = "leapfrog"    # Symplectic
   USE_RELATIVITY = True      # Full relativity
   # Trade-off: 2-3 FPS; scientific-grade

**For interactive exploration:**

.. code-block:: python

   DT = 0.001                 # Moderate
   SUBSTEPS = 4
   INTEGRATOR = "leapfrog"    # Still symplectic
   USE_RELATIVITY = True
   # Trade-off: 10-15 FPS; good balance

**For speed (less accurate):**

.. code-block:: python

   DT = 0.002                 # Larger timestep
   SUBSTEPS = 1               # Single step
   INTEGRATOR = "euler"       # Faster but drifts energy
   USE_RELATIVITY = False     # Skip gamma correction
   # Trade-off: 30+ FPS; visualization-grade


Camera & Rendering Configuration
=================================

**Wide-angle view (cinematic):**

.. code-block:: python

   CAMERA_FOV = 75            # Wide view
   CAMERA_POS = (-10, 5, 25)  # Stand back
   CAMERA_LOOKAT = (0, 0, 0)


**Detailed inspection:**

.. code-block:: python

   CAMERA_FOV = 30            # Narrow, zoom-like
   CAMERA_POS = (2, 2, 8)     # Close-up
   CAMERA_LOOKAT = (0, 0, 0)


**Overview (teaching mode):**

.. code-block:: python

   CAMERA_FOV = 60
   CAMERA_POS = (0, 5, 20)    # Top view from distance


Color & Appearance
==================

**Dark mode (default):**

.. code-block:: python

   BACKGROUND_COLOR = (0.01, 0.01, 0.03)  # Deep blue-black


**Light mode:**

.. code-block:: python

   BACKGROUND_COLOR = (0.9, 0.9, 0.95)    # Off-white


**Custom theme:**

.. code-block:: python

   BACKGROUND_COLOR = (0.1, 0.2, 0.3)     # Custom blue-green


Particle Appearance
===================

**Emphasis particle differences (by mass):**

.. code-block:: python

   PARTICLE_RADIUS_SCALE = 1.0            # Show mass width
   BASE_PARTICLE_RADIUS = 0.15            # Larger base

# Result: Protons 3x larger than electrons


**Uniform appearance:**

.. code-block:: python

   PARTICLE_RADIUS_SCALE = 0.0            # All same size
   BASE_PARTICLE_RADIUS = 0.15


**Minimal (fast):**

.. code-block:: python

   BASE_PARTICLE_RADIUS = 0.05            # Tiny dots


Programmatic Configuration
===========================

**Override config in Python:**

.. code-block:: python

   from quantum_collider_sandbox.simulation import Simulation
   from quantum_collider_sandbox import config

   # Before creating sim, override
   config.TRAIL_LENGTH = 20
   config.COULOMB_K = 80.0
   
   sim = Simulation(preset="lhc_pp", particles=50)
   # Sim uses overridden values


**Or use config_override parameter:**

.. code-block:: python

   sim = Simulation(
       preset="lhc_pp",
       particles=50,
       config_override={
           "TRAIL_LENGTH": 20,
           "COULOMB_K": 80.0,
       }
   )


Preset-Based Configuration
==========================

Presets are pre-packaged configurations for common scenarios. Edit in config.py:

.. code-block:: python

   PRESETS = {
       "my_custom": {
           "preset_name": "My Custom Setup",
           "initial_particles": 30,
           "coulomb_k": 50.0,
           "gravity_g": 2.0,
           "magnetic_field": (0, 0, 1.0),
           "dt": 0.001,
           "substeps": 4,
           "trail_length": 30,
       }
   }

Then selectfrom ImGui "Presets" dropdown.


Testing Configuration Changes
==============================

**Before running long simulations, test:**

1. **Check energy conservation:**

   .. code-block:: bash

      make test

2. **Monitor FPS:**

   - Run simulation with new config
   - Watch ImGui FPS display (left panel)
   - If < 20 FPS, reduce particles or TRAIL_LENGTH

3. **Check particle stability:**

   - Watch for erratic motion (means forces too strong)
   - Check kinetic energy display (should stay roughly constant)

4. **Validation:**

   - Run 100 timesteps
   - Export final state: ``Ctrl+S``
   - Verify file created in ``data/exports/``


Configuration Checklist
=======================

Before deep simulation work:

- [ ] GPU drivers installed and working
- [ ] Simulation target FPS chosen (20, 30, or 60)
- [ ] Target particle count set (100, 1k, 2k)
- [ ] TRAIL_LENGTH configured appropriately
- [ ] Timestep (DT) and substeps (SUBSTEPS) chosen
- [ ] Integrator (leapfrog recommended) selected
- [ ] Forces configured (Coulomb, gravity, strong)
- [ ] Relativity enabled/disabled appropriately
- [ ] Window resolution appropriate for GPU
- [ ] Data export directory exists (``data/exports/``, ``data/logs/``)
- [ ] Tests pass: ``make test``
- [ ] Linting clean: ``make lint``

See :ref:`Performance <performance>` for detailed performance tuning.
See :ref:`Parameters <parameters>` for complete parameter reference.

