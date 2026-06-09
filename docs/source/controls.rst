================================================================================
Controls & User Interface
================================================================================

Complete keyboard, mouse, and UI controls reference.

Keyboard Controls
=================

+---+---+---+
| Key | Action | Notes |
+===+===+===+
| ``SPACE`` | Play / Pause | Toggle simulation stepping |
+---+---+---+
| ``R`` | Reset | Spawn fresh particles (preset-dependent) |
+---+---+---+
| ``+`` / ``=`` | Spawn one particle | Random type from catalog |
+---+---+---+
| ``-`` / ``_`` | Remove particle | Removes last alive particle |
+---+---+---+
| ``T`` | Toggle trails | On/off; Press again to restore |
+---+---+---+
| ``H`` | Show help | Display keyboard shortcuts |
+---+---+---+
| ``?`` | Show help | Alias for H |
+---+---+---+
| ``Ctrl+S`` | Save state | Export to ``data/exports/state_*.h5`` |
+---+---+---+
| ``Ctrl+Shift+J`` | Export PhysicsLog | JSONL events to ``data/logs/physics_*.jsonl`` |
+---+---+---+
| ``Ctrl+L`` | Load state file | Import from HDF5 |
+---+---+---+
| ``Escape`` | Toggle ImGui | Show/hide left control panel |
+---+---+---+
| ``Ctrl+Q`` | Quit | Exit simulation |
+---+---+---+

Mouse & Camera Controls
=======================

+---+---+
| Action | Control |
+===+===+
| **Zoom** | Mouse wheel scroll ``Up`` / ``Down`` |
+---+---+
| **Rotate** | Right-mouse drag (while holding button) |
+---+---+
| **Pan** | Middle-mouse drag (or ``Shift`` + right-drag) |
+---+---+
| **Reset view** | Press ``R`` key |
+---+---+

ImGui Control Panel (Left Side)
================================

The left panel contains interactive sliders and dropdowns for real-time tuning:

**Simulation Control**

- **# Particles** — Slider (0-100) to spawn/remove particles
- **Presets** — Dropdown: select preset configuration
- **Play/Pause** — Button version of SPACE key
- **Reset** — Button version of R key

**Physics Constants** (real-time sliders)

- **Coulomb K** — Electrostatic force strength (0-200)
- **Gravity G** — Gravitational force strength (0-80)
- **Mag B** — Magnetic field strength (0-20)
- **E-Field** — Electric field strength (0-10)
- **Strong Force** — Nuclear force strength (0-100)

**Timestep Control**

- **DT** — Base timestep (0.0001-0.02)
- **Substeps** — Physics steps per frame (1-10)

**Rendering Tuning** (Phase 1 Optimization)

- **P.Size** — Particle radius scale (0.02-0.3)
- **Trail W** (Trail Width) — Trail line thickness (0.5-5.0)
- **Trails** — Checkbox to toggle all trails
- **Trail LEN** — Trail segment count (Phase 1: 40, tunable 5-100)

**Camera**

- **FOV** — Field of view angle (20-120 degrees)
- **BG** — Background brightness adjustment

**Simulation State**

- Live statistics:
  - Particle count breakdown by type
  - Kinetic energy (summed)
  - Momentum magnitude
  - Average velocity
  - Frame time (ms)
  - FPS

**Particle Inspector**

When you click on a particle in the scene, the inspector shows:
  - Type (name, PDG ID)
  - Position (x, y, z)
  - Velocity (vx, vy, vz, |v|)
  - Mass, charge, lifetime
  - Color
  - Trail history


Presets Dropdown
================

From the ImGui panel, select "Presets" to load a configuration:

1. **Default** — 20 random particles, no fields (exploration mode)
2. **Rutherford** — Scattered beam hitting target (Coulomb scattering demo)
3. **Cyclotron** — Charged particles in magnetic field loop
4. **LHC pp** — High-energy proton-proton collisions (strong force)
5. **e⁺e⁻** — Electron-positron annihilation (pair creation)
6. **Black Hole** — Particles orbiting/accreting onto black hole
7. **Gas** — Low-energy thermal gas (Brownian motion test)
8. **Two-Beam** — Two counter-rotating beams (collision demo)
9. **Playground** — Sandbox with tunable parameters
10. **N-Body Virial** — Self-gravitating cluster (gravitational dynamics)

See :ref:`Presets Explained <presets>` for detailed descriptions.


Display Overlays
================

**Collision Flashes**
   - When particles collide, a yellow flash appears briefly
   - Indicates collision detection is working

**Particle Trails**
   - Colored lines following each particle
   - Color matches particle type (electron = blue, photon = yellow, etc.)
   - Fade with age (brighter = recent, dimmer = old)
   - See :ref:`Phase 1 Optimization <performance-phase1>` for trail tuning

**Black Hole Effects** (when enabled)
   - **Accretion Disk** — Thin orange ring around black hole
   - **Photon Ring** — Glowing halo (light bending around BH)
   - **Gravitational Lensing** — Stars behind BH appear distorted

**Starfield Background**
   - Static 3D stars for spatial reference
   - Set via ``BACKGROUND_STARS`` in config


ImGui Workflow Tips
===================

**Profile FPS while adjusting:**

1. Open left panel (default)
2. Note current FPS in status
3. Drag a physics slider (e.g., Coulomb K)
4. Watch FPS—if it drops significantly, culprit found

**Optimize for target particle count:**

1. Set # Particles slider to your target (e.g., 1000)
2. If FPS < 30 fps, try:
   - Reduce Trail LEN (40 → 20)
   - Disable Trails (T key)
   - Reduce WINDOW_WIDTH/HEIGHT in config

**Export a scene for later:**

1. Set up particles and forces as desired
2. Press ``Ctrl+S`` to save state
3. Filename: ``data/exports/state_<timestamp>.h5``
4. Later: ``Ctrl+L`` to reload


UI Customization
================

See :ref:`Configuration <configuration>` for:

- **WINDOW_WIDTH, WINDOW_HEIGHT** — Change resolution
- **CAMERA_POS, CAMERA_LOOKAT** — Default camera placement
- **CAMERA_FOV** — Field of view
- **BACKGROUND_COLOR** — Change background from dark blue to custom

See :ref:`Performance Tuning <performance>` for:

- **BASE_PARTICLE_RADIUS, PARTICLE_RADIUS_SCALE** — Particle size
- **TRAIL_LENGTH** — Number of trail segments (Phase 1: critical for FPS)
- **TRAIL_WIDTH** — Line thickness
- **TRAILS_ENABLED_DEFAULT** — Start with trails on/off

