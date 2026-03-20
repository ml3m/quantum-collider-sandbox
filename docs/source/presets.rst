================================================================================
Built-in Presets
================================================================================

Detailed explanation of all 10 simulation presets.

Overview
========

Each preset is a pre-configured scenario demonstrating different physics phenomena.
Load via ImGui "Presets" dropdown or set ``PRESET`` in config.py:

.. code-block:: python

   PRESET = "lhc_pp"  # or "default", "rutherford", etc.


Preset Listing
==============

1. Default Preset
-----------------

**Purpose:** Exploration mode with random particles

**Configuration:**
   - Particles: 20 random types
   - Forces: Coulomb (K=40), Gravity (G=6)
   - Fields: None
   - Boundary: Reflection
   - Initial region: Sphere ±5 units

**Use case:**
   - Getting familiar with the UI
   - Free experimentation
   - Sandbox for custom parameter tuning

**Initial appearance:**
   - Random cloud of colored spheres
   - Gentle Coulomb repulsion spreads them
   - Some may be attracted by gravity


2. Rutherford Preset
---------------------

**Purpose:** Coulomb scattering (Rutherford scattering experiment)

**Configuration:**
   - Particles: 1 stationary target (nucleus, high mass/charge)
   - Incoming beam: 30 alpha particles (helium nuclei) from edge
   - Forces: Coulomb repulsion (K=80, very strong)
   - Boundary: Reflection
   - Initial geometry: Beam aimed horizontally at center

**Physics demonstrated:**
   - Coulomb repulsion at short range
   - Scattering angle vs impact parameter
   - Hyperbolic trajectories in inverse-square potential

**Observation:**
   - Direct hits scatter backward (large angle)
   - Grazing hits scatter slightly forward
   - Distribution follows Rutherford formula


3. Cyclotron Preset
--------------------

**Purpose:** Charged particle motion in magnetic field

**Configuration:**
   - Particles: 15 random charged particles
   - Magnetic field: B = (0, 0, 3) [strong uniform field in z-direction]
   - Forces: Lorentz force only
   - Boundary: Reflection
   - Initial velocity: in xy-plane

**Physics demonstrated:**
   - Circular motion (cyclotron radius)
   - Frequency independent of velocity (cyclotron frequency ω = qB/m)
   - Different masses → different orbit radii at same speed

**Observation:**
   - Particles spiral and circle
   - Heavy particles (protons) have larger orbits than light (electrons)
   - Synchrotron radiation (if enabled) causes spiral decay


4. LHC pp Preset
-----------------

**Purpose:** Proton-proton high-energy collisions (LHC-style physics)

**Configuration:**
   - Particles: Two beams of 25 protons each
   - Beams: Counter-rotating at high speed (v ≈ 0.9c in simulation units)
   - Forces: Strong nuclear force (K_s=50), Coulomb (K=40)
   - Collision energy: ~high-mass pair creation possible
   - Decay products: Pions, kaons, muons

**Physics demonstrated:**
   - Head-on and glancing collisions
   - High-energy annihilation → meson/hadron production
   - Pair creation (e.g., e⁺ + e⁻ from initial energy)
   - Color-charge (QCD) interactions

**Observation:**
   - Violent particle showers on collision
   - Trail explosions when protons meet
   - Short-lived decay products

**Warning:** Very CPU-intensive; 60+ particles may cause FPS drop


5. e⁺e⁻ Annihilation Preset
-----------------------------

**Purpose:** Electron-positron pair annihilation (LEP/ILC physics)

**Configuration:**
   - Particles: 20 electrons + 20 positrons
   - Beams: Head-on approach at high speed
   - Forces: Coulomb attraction/repulsion, no gravity
   - Pair creation: Enabled (high energy)
   - Decay products: Photons, muon pairs, hadron jets

**Physics demonstrated:**
   - Annihilation of matter + antimatter
   - Conversion to energy (via photons, bosons)
   - Creation of new particle pairs from energy
   - CP-violation signatures (if any)

**Observation:**
   - Electrons and positrons spiral toward each other
   - On collision, massive energy release → photons/muons
   - Fireworks-like particle cascade


6. Black Hole Preset
---------------------

**Purpose:** Particle dynamics around a black hole

**Configuration:**
   - Central mass: Supermassive black hole (M ≈ 1e9 solar masses in sim units)
   - Schwarzschild radius: r_s ≈ 0.7
   - Accretion disk: Visible orange ring
   - Photon ring: Glowing halo (gravitational lensing)
   - Particles: 15 escaping and in-falling orbits
   - Forces: BH pseudo-Schwarzschild gravity, no other forces

**Physics demonstrated:**
   - Orbital mechanics near massive object
   - Time dilation near event horizon
   - Gravitational lensing (stars distort behind BH)
   - Accretion dynamics

**Observation:**
   - Some particles escape parabolically
   - Others settle into elliptical orbits
   - Few plunge into Black Hole (removed from sim)
   - Lensing causes starfield distortion


7. Gas Preset
--------------

**Purpose:** Low-energy thermal gas (Brownian motion, kinetic theory)

**Configuration:**
   - Particles: 40 random types at low speed (thermal velocity)
   - Forces: Coulomb (K=0.1, weak), Gravity (G=1)
   - Temperature-like: Uniform velocity distribution, ~1 unit/s
   - Boundary: Periodic (toroidal wrapping)

**Physics demonstrated:**
   - Particle collisions in dense medium
   - Equipartition of energy
   - Diffusion and mixing
   - No long-range order (unlike plasma)

**Observation:**
   - Particles move slowly, colliding frequently
   - Temperature/energy bars show energy distribution
   - Steady kinetic energy over time


8. Two-Beam Preset
-------------------

**Purpose:** Counter-rotating beam collision (asymmetric)

**Configuration:**
   - Particles: Beam 1 (15 electrons), Beam 2 (15 positrons)
   - Geometry: Beams approach from opposite sides
   - Speed: ~0.8c (moderate relativistic)
   - Forces: Coulomb only
   - Collision zone: Center of domain

**Physics demonstrated:**
   - Asymmetric vs symmetric collisions
   - Beam dynamics and focusing
   - Electrostatic repulsion between like-charges

**Observation:**
   - Two organized streams approach
   - Repulsion near center (same-sign charges in region)
   - Some scatter, some pass through


9. Playground Preset
---------------------

**Purpose:** Interactive sandbox with wide parameter ranges

**Configuration:**
   - Particles: Empty initially (use +/- to spawn)
   - All forces: Enabled and accessible via ImGui sliders
   - Boundary: Reflection
   - No pre-set velocities: Particles spawn at rest

**Use case:**
   - Custom experiments
   - Parameter sensitivity studies
   - Building custom scenarios

**Workflow:**
   1. Spawn particles: +/+ keys or ImGui slider
   2. Adjust forces in real-time
   3. Observe effects immediately


10. N-Body Virial Preset
------------------------

**Purpose:** Self-gravitating particle cluster (cosmology simulation)

**Configuration:**
   - Particles: 50 random particles (various masses)
   - Forces: Gravity only (G=8), no Coulomb
   - Initial condition: Kinetic energy = 0.5 × |Potential energy| (virial balance)
   - Boundary: None (open space)
   - Geometry: Random sphere, velocity-dispersion model

**Physics demonstrated:**
   - N-body gravity simulation
   - Virial theorem (E_kin + E_pot = constant... approximately)
   - Dynamic equilibrium and orbit crossing
   - Particle escapers vs bound core

**Observation:**
   - Cluster oscillates and reforms
   - Some particles escape to infinity
   - Core particles form tighter, bound orbits
   - Long relaxation timescales


Preset Comparison Table
=======================

.. list-table::
   :header-rows: 1
   :widths: 15 12 12 12 12 12 12

   * - Preset
     - Particles
     - Coulomb
     - Gravity
     - Magnetic
     - Strong
     - Best for

   * - Default
     - 20
     - Yes (K=40)
     - Yes (G=6)
     - No
     - No
     - Exploration

   * - Rutherford
     - 30+1
     - Yes (K=80)
     - No
     - No
     - No
     - Scattering demo

   * - Cyclotron
     - 15
     - No
     - No
     - Yes (B=3)
     - No
     - Magnetism demo

   * - LHC pp
     - 50+
     - Yes (K=40)
     - No
     - No
     - Yes (K=50)
     - High-energy collisions

   * - e⁺e⁻
     - 40+
     - Yes (K=20)
     - No
     - No
     - No
     - Annihilation demo

   * - Black Hole
     - 15
     - No
     - Yes (BH only)
     - No
     - No
     - GR effects

   * - Gas
     - 40
     - Yes (K=0.1)
     - Yes (G=1)
     - No
     - No
     - Kinetic theory

   * - Two-Beam
     - 30
     - Yes (K=40)
     - No
     - No
     - No
     - Beam dynamics

   * - Playground
     - 0
     - Yes (tunable)
     - Yes (tunable)
     - Yes (tunable)
     - Yes (tunable)
     - Custom scenarios

   * - N-Body Virial
     - 50
     - No
     - Yes (G=8)
     - No
     - No
     - Cosmology


Creating Custom Presets
=======================

To add a custom preset, edit ``config.py``:

.. code-block:: python

   # In config.py, add a new preset dict:
   PRESETS = {
       "my_preset": {
           "preset_name": "My Custom Experiment",
           "initial_particles": 25,
           "coulomb_k": 50.0,
           "gravity_g": 1.0,
           "magnetic_field": (0, 0, 2),
           # ... other parameters
       }
   }

Then in ``__main__.py``, list your preset in the dropdown, and the UI will load it automatically.

See :ref:`Development <development>` for more details on extending the simulation.

