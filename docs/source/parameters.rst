.. _parameters:

================================================================================
Configuration Parameters Reference
================================================================================

This document describes all configuration parameters used by the Quantum Collider
Sandbox simulation and visualization. Parameters are defined in
``quantum_collider_sandbox.config`` and can be adjusted for different use cases.

--------------------------------------------------------------------------------
Physics Integration
--------------------------------------------------------------------------------

.. py:data:: DT

   **Type:** float  
   **Default:** 0.001  
   **Range:** 0.00001 – 0.02 (via GUI)

   Base simulation timestep in arbitrary units. Smaller values yield smoother,
   more accurate motion but increase CPU/GPU load. Use 0.001 for realistic
   visualization; 0.002 for faster but slightly less smooth playback.

.. py:data:: SUBSTEPS

   **Type:** int  
   **Default:** 4  
   **Range:** 1 – 10 (via GUI)

   Number of physics integration steps per frame. Higher values improve numerical
   stability and reduce jitter, especially for fast particles or strong forces.
   Recommended: 4–5 for smooth visualization.

.. py:data:: INTEGRATOR

   **Type:** str  
   **Default:** ``"leapfrog"``  
   **Options:** ``"euler"``, ``"leapfrog"``

   Integration scheme for particle motion.

   - **euler** — Simple first-order Euler; faster but less accurate, energy drift.
   - **leapfrog** — Symplectic integrator; preserves energy better, recommended
     for realistic long-running simulations.

--------------------------------------------------------------------------------
Forces and Fields
--------------------------------------------------------------------------------

.. py:data:: COULOMB_K

   **Type:** float  
   **Default:** 40.0  
   **Range:** 0.0 – 200.0 (via GUI)

   Coulomb constant scaling for electromagnetic repulsion/attraction between
   charged particles. Set to 0 to disable Coulomb force.

.. py:data:: GRAVITY_G

   **Type:** float  
   **Default:** 6.0  
   **Range:** 0.0 – 80.0 (via GUI)

   Gravitational constant scaling. Affects all massive particles. Set to 0 for
   collision-only or beam experiments without gravity.

.. py:data:: SOFTENING

   **Type:** float  
   **Default:** 0.05

   Softening length for force calculations. Prevents singularities when particles
   get very close; larger values smooth forces but reduce accuracy at short range.

.. py:data:: CUTOFF_RADIUS

   **Type:** float  
   **Default:** 15.0

   Maximum distance for force computations. Particles beyond this distance do
   not interact. Reduces computational cost for large systems.

.. py:data:: MAGNETIC_FIELD

   **Type:** tuple of (float, float, float)  
   **Default:** (0.0, 0.0, 2.0)

   Uniform magnetic field (B_x, B_y, B_z). Charged particles follow curved
   trajectories (Lorentz force). Used in cyclotron and synchrotron presets.

.. py:data:: E_FIELD

   **Type:** tuple of (float, float, float)  
   **Default:** (0.0, 1.0, 0.0)

   Uniform electric field (E_x, E_y, E_z). Accelerates charged particles along
   the field direction.

.. py:data:: STRONG_FORCE_K

   **Type:** float  
   **Default:** 0.0  
   **Range:** 0.0 – 100.0 (via GUI)

   Strong nuclear force strength. Attractive at short range; used for LHC-style
   proton-proton collisions. Set to 0 for electromagnetic-only physics.

.. py:data:: STRONG_FORCE_RANGE

   **Type:** float  
   **Default:** 0.5  
   **Range:** 0.1 – 3.0 (via GUI)

   Effective range of the strong force. Particles within this distance feel the
   strong interaction.

--------------------------------------------------------------------------------
Relativity and Speed Limits
--------------------------------------------------------------------------------

.. py:data:: SPEED_OF_LIGHT

   **Type:** float  
   **Default:** 30.0

   Speed of light in simulation units. Used for relativistic kinematics when
   :py:data:`USE_RELATIVITY` is enabled. Particles are capped below this speed.

.. py:data:: USE_RELATIVITY

   **Type:** bool  
   **Default:** True

   Enable relativistic dynamics (Lorentz factor, mass increase at high speed).
   Recommended for high-energy collision presets (LHC, e⁺e⁻ annihilation).

.. py:data:: SYNCHROTRON_COEFF

   **Type:** float  
   **Default:** 0.0  
   **Range:** 0.0 – 1.0 (via GUI)

   Synchrotron radiation coefficient. Simulates energy loss when charged
   particles accelerate in magnetic fields. Nonzero values add radiative
   damping for more realistic cyclotron/synchrotron behavior.

.. py:data:: MAX_VELOCITY

   **Type:** float  
   **Default:** 29.9

   Hard cap on particle speed (must be < SPEED_OF_LIGHT). Prevents numerical
   overflow.

.. py:data:: MIN_VELOCITY

   **Type:** float  
   **Default:** 0.01

   Minimum velocity floor. Avoids numerical traps when particles come to rest
   (e.g., at boundaries).

--------------------------------------------------------------------------------
Collisions and Pair Creation
--------------------------------------------------------------------------------

.. py:data:: COLLISION_RESTITUTION

   **Type:** float  
   **Default:** 0.85

   Coefficient of restitution for elastic collisions (0 = fully inelastic,
   1 = fully elastic). Affects bounce behavior when particles collide.

.. py:data:: PAIR_CREATION_THRESHOLD

   **Type:** float  
   **Default:** 15.0  
   **Range:** 1.0 – 50.0 (via GUI)

   Kinetic energy threshold (in simulation units) above which high-energy
   collisions can create particle-antiparticle pairs (e.g., e⁺e⁻ from photons).

.. py:data:: SPAWN_VELOCITY_SPREAD

   **Type:** float  
   **Default:** 2.5

   Velocity spread when spawning random particles. Used for preset setups.

--------------------------------------------------------------------------------
Boundary Conditions
--------------------------------------------------------------------------------

.. py:data:: BOUNDARY_MODE

   **Type:** str  
   **Default:** ``"reflect"``  
   **Options:** ``"reflect"``, ``"periodic"``, ``"none"``

   - **reflect** — Particles bounce off boundaries (elastic reflection).
   - **periodic** — Particles wrap around (toroidal space).
   - **none** — No boundary; particles can leave the simulation volume.

.. py:data:: BOUNDARY_SIZE

   **Type:** float  
   **Default:** 12.0  
   **Range:** 3.0 – 30.0 (via GUI)

   Half-extent of the simulation box. The domain is a cube from
   (-BOUNDARY_SIZE, -BOUNDARY_SIZE, -BOUNDARY_SIZE) to
   (BOUNDARY_SIZE, BOUNDARY_SIZE, BOUNDARY_SIZE).

--------------------------------------------------------------------------------
Visualization
--------------------------------------------------------------------------------

.. py:data:: WINDOW_WIDTH

   **Type:** int  
   **Default:** 2560

   Window width in pixels. Adjust for your display; smaller values improve
   performance on low-end GPUs.

.. py:data:: WINDOW_HEIGHT

   **Type:** int  
   **Default:** 1600

   Window height in pixels.

.. py:data:: WINDOW_TITLE

   **Type:** str  
   **Default:** ``"Quantum Collider Sandbox"``

   Title of the application window.

.. py:data:: CAMERA_POS

   **Type:** tuple of (float, float, float)  
   **Default:** (0.0, 2.0, 22.0)

   Initial camera position (x, y, z). Use RMB+drag to orbit, scroll to zoom.

.. py:data:: CAMERA_LOOKAT

   **Type:** tuple of (float, float, float)  
   **Default:** (0.0, 0.0, 0.0)

   Point the camera looks at (usually the simulation center).

.. py:data:: CAMERA_FOV

   **Type:** float  
   **Default:** 55

   Camera field of view in degrees. Larger values = wider view, more distortion.

.. py:data:: BACKGROUND_COLOR

   **Type:** tuple of (float, float, float)  
   **Default:** (0.01, 0.01, 0.03)

   Background color (R, G, B) in [0, 1]. Dark blue-black for space-like feel.

.. py:data:: BASE_PARTICLE_RADIUS

   **Type:** float  
   **Default:** 0.12  
   **Range:** 0.02 – 0.3 (via GUI "P.Size")

   Base radius for rendering particles. Combined with per-type radius from the
   PDG table for final size.

.. py:data:: PARTICLE_RADIUS_SCALE

   **Type:** float  
   **Default:** 0.45

   Scale factor applied to particle radii from the PDG table. Tunes relative
   sizes of different particle types.

.. py:data:: TRAIL_LENGTH

   **Type:** int  
   **Default:** 1000

   Maximum number of trail segments per particle. Longer trails show more
   history but use more memory and GPU.

.. py:data:: TRAIL_WIDTH

   **Type:** float  
   **Default:** 2.0  
   **Range:** 0.5 – 5.0 (via GUI "Trail W")

   Line width for particle trails in pixels.

.. py:data:: FLASH_OPACITY

   **Type:** float  
   **Default:** 0.1

   Alpha (0–1) for collision flash particles. Lower = more transparent;
   particles remain visible through flashes.

--------------------------------------------------------------------------------
Black Hole
--------------------------------------------------------------------------------

.. py:data:: BH_MASS

   **Type:** float  
   **Default:** 200.0  
   **Range:** 10.0 – 2000.0 (via GUI)

   Black hole mass in simulation units. Schwarzschild radius
   r_s = 2·M/c². Affects gravitational pull and accretion disk.

--------------------------------------------------------------------------------
Internal / Limits
--------------------------------------------------------------------------------

.. py:data:: MAX_PARTICLES

   **Type:** int  
   **Default:** 100

   Maximum number of particles in the simulation. Decays and collisions can
   create new particles; excess are culled.

.. py:data:: NUM_TYPES

   **Type:** int  
   **Default:** 48

   Number of particle type slots (40 PDG + 8 reserved for user-defined).

--------------------------------------------------------------------------------
Recommended Defaults for Realistic & Smooth Visualization
--------------------------------------------------------------------------------

For a balance of **realistic physics** and **smooth motion**:

- **DT** = 0.001 — Smaller timestep reduces numerical jitter
- **SUBSTEPS** = 4 — More integration steps per frame
- **INTEGRATOR** = ``"leapfrog"`` — Energy-conserving integration
- **USE_RELATIVITY** = True — Correct high-energy behavior
- **TRAIL_LENGTH** = 1000 — Sufficient history for trajectory visibility
- **TRAIL_WIDTH** = 2.0 — Readable trails without clutter

These are the defaults in ``config.py``. Adjust via the in-app GUI sliders
or by modifying ``config.py`` before launch.
