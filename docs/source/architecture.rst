================================================================================
Architecture & Design
================================================================================

System architecture, data flow, and design patterns.

System Overview
===============

.. mermaid::

   graph TD
       MAIN["__main__.py<br/>CLI Entry Point"]
       CONFIG["config.py<br/>Global Constants"]
       PARTICLES["particles.py<br/>Taichi Field Mgmt"]
       SIM["simulation.py<br/>GPU Physics Kernel<br/>2900 lines"]
       RENDERER["renderer.py<br/>Taichi UI & ImGui"]
       PDG["pdg_table.py<br/>Particle Catalog"]
       DATALOADER["data_loader.py<br/>HDF5/CSV Import"]

       MAIN --> CONFIG
       MAIN --> SIM
       MAIN --> RENDERER
       MAIN --> PDG
       MAIN --> PARTICLES

       SIM --> CONFIG
       SIM --> PARTICLES
       SIM --> PDG

       RENDERER --> CONFIG
       RENDERER --> SIM
       RENDERER --> PDG

       DATALOADER --> HDF5

       classDef gpu fill:#ff6b6b
       classDef io fill:#4ecdc4
       classDef config fill:#ffe66d
       
       class SIM gpu
       class DATALOADER io
       class CONFIG config


Module Responsibilities
=======================

**__main__.py** (CLI & Main Loop)
   - Entry point and command-line argument parsing
   - Simulation loop (render each frame, step physics)
   - Input handling (keyboard, mouse, ImGui)
   - State management (pause/resume, reset)

**config.py** (Constants)
   - Physics constants (forces, integrators, relativity)
   - Rendering constants (camera, trails, colors)
   - Preset definitions
   - **Size:** ~400 lines

**simulation.py** (GPU Physics)
   - Taichi @ti.kernel GPU kernels
   - Force computation (Coulomb, gravity, Lorentz, strong)
   - Particle dynamics (integrate, boundary, collision detection)
   - Decay & pair production
   - Trail rendering (Phase 1 optimized)
   - **Size:** ~2900 lines (largest module)

**renderer.py** (Visualization)
   - Taichi GUI window management
   - 3D camera and scene setup
   - Particle rendering (points/spheres + trails)
   - ImGui control panels
   - Black hole effects (disk, photon ring, lensing)
   - Collision flashes and debug overlays

**particles.py** (Taichi Field Management)
   - Initializes Taichi fields (big arrays on GPU)
   - Position, velocity, type buffers
   - Trail ring buffers (one per particle)

**pdg_table.py** (Particle Catalog)
   - 40 particles from Particle Data Group
   - Masses, lifetimes, charges, decay channels
   - Color mappings for visualization
   - Quantum numbers (flavor, color, spin)

**data_loader.py** (I/O)
   - HDF5 state import/export
   - CSV event logging
   - JSONL physics events

Data Flow (Per Frame)
=====================

1. **Input Phase**

   .. code-block:: text

       Keyboard/Mouse Events
              ↓
       Renderer.handle_input()
              ↓
       ImGui Sliders → Update force constants in real-time
       SPACE → Toggle pause
       +/- → Spawn/remove particles
       Ctrl+S → Save state to HDF5

2. **Physics Phase** (repeated SUBSTEPS times)

   .. code-block:: text

       compute_forces()
           ↓
           Coulomb (pairwise, O(N²))
           Gravity (pairwise, O(N²))
           Strong force (baryon-baryon, O(N²))
           Lorentz E/B (O(N))
           Black hole gravity (O(N))
           ↓
       _integrate_step()
           ↓
           Leapfrog half-kick OR Euler step
           Velocity clamping (MAX_VELOCITY)
           Relativity correction (γ)
           ↓
       apply_boundaries()
           ↓
           Reflect or periodic wrapping
           ↓
       detect_collisions()
           ↓
           O(N²) pairwise radius overlap
           Dispatch: annihilation, decay, elastic scatter
           Enqueue spawn products
           ↓
       monte_carlo_decay()
           ↓
           Exponential decay law
           Time dilation (SR + GR)
           Enqueue spawn products
           ↓
       _apply_spawn_queue() + _finalize_spawn()
           ↓
           Create new particles from collisions/decays
           ↓
       record_trails()
           ↓
           Ring buffer update (latest position to head)
           ↓
       (Leapfrog only) compute_forces() + half-kick

3. **Maintenance Phase**

   .. code-block:: text

       do_maintenance()
           ↓
           Fade collision flashes
           Compact dead particles
           Update active particle count

4. **Stats Phase** (every 10 frames)

   .. code-block:: text

       refresh_stats()
           ↓
           Compute KE, momentum, census
           Update ImGui display

5. **Render Phase**

   .. code-block:: text

       prepare_render()
           ↓
           build_render_data() kernel → GPU buffer
           build_trail_lines() kernel → GPU vertices (Phase 1 optimized)
           GPU → CPU (vertex/color uploads)
           ↓
       Renderer.render()
           ↓
           Draw particles (colored spheres)
           Draw trails (line segments with fade)
           Draw black hole effects
           Draw collision flashes
           Draw starfield
           Draw ImGui panels (CPU-side)
           ↓
       taichi.ui.show()
           ↓
           Display to screen

Taichi GPU Kernels
==================

**@ti.kernel decorator:** JIT-compiled GPU code

**compute_forces()** [O(N²)]

   - Nested loop over all particles
   - Pairwise distance & force calculation
   - Accumulate force vector per particle
   - GPU: Each thread processes one particle

**_integrate_step()** [O(N)]

   - Loop over all particles
   - Update velocity (force/mass acceleration)
   - Update position (velocity × dt)
   - Clamp to MAX_VELOCITY
   - Apply SR gamma correction

**detect_collisions()** [O(N²)]

   - Nested loop over particle pairs
   - Sphere-sphere overlap test
   - If collision → spawn products (enqueued)
   - Dispatch collision type (annihilation, decay, scatter)

**monte_carlo_decay()** [O(N)]

   - Loop over particles
   - Compute decay probability (exponential law)
   - If decay occurs → randomly select channel, spawn products

**build_trail_lines()** [O(N)]

   - Per-particle: extract ring buffer positions
   - **Phase 1 skip logic:**
     - Skip if type == PHOTON
     - Skip if frozen
     - Skip if speed < MIN_TRAIL_SPEED_FOR_RENDER
     - Skip if trail too short
   - Generate line segment vertices for rendering
   - Write to GPU arrays (trail_vertices, trail_colors)

All kernels are memory-coalesced (sequential GPU thread access to arrays).


State Management
================

**Active Particle List:**

- ``num_active[None]`` — Count of live particles (compacted list)
- Particles are indexed [0, num_active)
- Dead particles moved to end, count decremented
- Avoids fragmentation

**Ring Buffer Trails:**

- Per-particle: ``trail_pos[i, :]`` = ring buffer of 40/20/5 positions
- ``trail_head[i]`` = index of newest position (wraps 0 to TRAIL_LENGTH-1)
- ``trail_count[i]`` = number of valid positions (starts at 1, fills up to TRAIL_LENGTH)

**Spawn Queue:**

- Temporary list of particles to create (from collisions/decays)
- Processed end-of-step (after collision detection)
- New particles inserted into main structure

**Force State:**

- Current force constants (read from config each frame)
- Derived fields (magnetic field magnitude, velocity-dependent damping)


Integrators
===========

**Euler (first-order):**

.. math::

   \vec{v}_{n+1} &= \vec{v}_n + \frac{\vec{F}}{m} \cdot dt \\
   \vec{r}_{n+1} &= \vec{r}_n + \vec{v}_{n+1} \cdot dt

- Simple, fast
- Poor energy conservation
- Energy drifts monotonically

**Leapfrog (symplectic, second-order):**

.. math::

   \vec{v}_{n+1/2} &= \vec{v}_n + \frac{\vec{F}}{m} \cdot \frac{dt}{2} \\
   \vec{r}_{n+1} &= \vec{r}_n + \vec{v}_{n+1/2} \cdot dt \\
   \vec{v}_{n+1} &= \vec{v}_{n+1/2} + \frac{\vec{F}}{m} \cdot \frac{dt}{2}

- Symplectic → preserves phase-space volume
- Better energy conservation
- Slightly higher computational cost
- **Recommended** for long simulations


Particle Lifecycle
==================

1. **Spawn** — Random position/velocity or from decay/collision
2. **Alive** — Part of main particle pool, physics applied
3. **Collision** → New particles spawned (or annihilation)
4. **Decay** → New particles spawned, original removed
5. **Dead** — Removed from active pool (compacted)

Removal causes:
- Natural decay (exponential lifetime)
- Boundary escape (if BOUNDARY_MODE="none")
- Annihilation in collision


GPU Memory Layout
=================

Taichi allocates large fixed arrays on GPU at startup:

.. list-table::
   :header-rows: 1

   * - Field
     - Size
     - Purpose

   * - ``pos[MAX_PARTICLES]``
     - 100 particles × 3 floats = 1.2 KB
     - Current positions

   * - ``vel[MAX_PARTICLES]``
     - 100 particles × 3 floats = 1.2 KB
     - Current velocities

   * - ``ptype[MAX_PARTICLES]``
     - 100 particles × 1 int = 400 B
     - Particle type (PDG ID)

   * - ``trail_pos[MAX_PARTICLES, TRAIL_LENGTH]``
     - 100 × 40 × 3 floats = 48 KB
     - Trail history (ring buffer)

   * - ``trail_vertices[MAX_PARTICLES * TRAIL_LENGTH * 2]``
     - 100 × 40 × 2 × 3 floats = 96 KB
     - Trail geometry (GPU-side only)

   * - ``trail_colors[MAX_PARTICLES * TRAIL_LENGTH * 2]``
     - 100 × 40 × 2 × 3 floats = 96 KB
     - Trail colors (GPU-side only)

**Total:** ~250 KB (negligible on modern GPUs)

Phase 1 optimization reduces trail vertex buffer by 10x (same field size, fewer rendered vertices).


Design Patterns
===============

**Kernel + Taichi Fields:**

- All heavy computation in @ti.kernel functions
- Fields auto-parallelized across GPU threads
- No explicit parallelism in Python code

**Configuration as Constants:**

- All tunable parameters in config.py
- Imported at module load time
- Changes require restart

**Event-Driven Physics:**

- Collisions and decays detected at step
- Products enqueued, applied end-of-step
- Prevents iterator invalidation in nested loops

**Compacted Active List:**

- Dead particles not physically removed
- Active count decremented, dead moved to end
- Prevents fragmentation and repeated allocation


Error Handling
==============

**Physics assertions (disabled in release):**

- Energy bounds checking
- NaN/Inf detection in forces
- Particle count sanity checks

**Boundary checks:**

- Velocity clamping (prevent overflow)
- Force magnitude clamping in collider
- Array index bounds (in Taichi kernel)

**Graceful degradation:**

- If GPU out of memory → fallback to CPU (if Taichi supports)
- If particle spawn fails → log warning, continue
- If export fails → user gets error box, sim continues


Performance Considerations
==========================

**GPU Memory Coalescing:**

- Kernel loops iterate particles sequentially
- Threads access same field sequentially
- GPU caches efficiently (coalesced memory access)

**Reduced Branching:**

- Hardcoded trail skip conditions (photons, frozen) for perf
- No runtime config branches in inner loops

**Phase 1 Optimization:**

- 10x vertex reduction (400 → 40 segments)
- Skip logic pre-filters particles before rendering
- Result: 2-3x FPS improvement at 1k particles

See :ref:`Performance Tuning <performance>` for more optimization details.

