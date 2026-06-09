================================================================================
Physics Model Documentation
================================================================================

Physics models, forces, kinematics, and decay processes.

Force Models
============

All forces are computed in ``simulation.py`` in the ``compute_forces()`` kernel.

**1. Coulomb Force (Electrostatics)**

.. math::

   \vec{F} = -k \frac{q_1 q_2}{r^2 + \epsilon^2} \hat{r}

- **Constant:** ``COULOMB_K`` (tunable 0-200)
- **Softening:** ``SOFTENING`` (0.05) prevents singularities
- **Type:** Pairwise, all particles
- **Interaction:** Only between charged particles (q ≠ 0)

**2. Newtonian Gravity**

.. math::

   \vec{F} = +G \frac{m_1 m_2}{r^2 + \epsilon^2} \hat{r}

- **Constant:** ``GRAVITY_G`` (tunable 0-80)
- **Softening:** Same as Coulomb
- **Type:** Pairwise, all particles with mass > 0
- **Note:** Non-relativistic; does not use relativistic mass

**3. Lorentz Force (E + B fields)**

.. math::

   \vec{F} = q(\vec{E} + \vec{v} \times \vec{B})

- **Electric field:** ``E_FIELD`` = (Ex, Ey, Ez) in config
- **Magnetic field:** ``MAGNETIC_FIELD`` = (Bx, By, Bz) in config
- **Type:** Per-particle, applied to all q ≠ 0
- **Usage:** Cyclotron, synchrotron presets

**4. Yukawa Strong Force (QCD approximation)**

.. math::

   \vec{F} = -k_s \frac{\exp(-r/\lambda)}{r + 0.01} \hat{r}, \quad r < r_{max}

- **Constant:** ``STRONG_FORCE_K`` (tunable 0-100)
- **Range:** ``STRONG_FORCE_RANGE`` (0.1-3.0)
- **Type:** Pairwise baryon-baryon only
- **Cutoff:** Beyond r_max, no force

**5. Black Hole Pseudo-Schwarzschild Gravity**

.. math::

   \vec{F} = -\frac{GM m}{(r - r_s)^2} \hat{r}, \quad r > r_s

- **BH mass:** ``BLACK_HOLE_MASS``
- **Schwarzschild radius:** ``BLACK_HOLE_RADIUS``
- **Type:** Per-particle from fixed central mass
- **Note:** Simplified form; not general relativity

**6. Synchrotron Radiation Damping (Optional)**

.. math::

   \vec{F}_{damp} = -\alpha \frac{q^2 a^2}{m_{eff} v^2} \vec{v}

- **Coefficient:** ``SYNCHROTRON_COEFF`` (0-1)
- **Type:** Velocity damping for accelerating charged particles
- **Physics:** Energy loss in magnetic fields


Kinematic Models
================

**Special Relativity** (when ``USE_RELATIVITY = True``)

Lorentz factor:

.. math::

   \gamma = \frac{1}{\sqrt{1 - v^2/c^2}}

- **Speed of light:** ``SPEED_OF_LIGHT`` (sim units, default 30)
- **Applied to:**
  - Effective mass in force calculation
  - Decay width (lifetime dilation)
  - Decay kinematics (4-momentum conservation)

**General Relativity** (Black Hole only)

- **Time dilation factor:** Depends on position near black hole
- Used in decay rate computation when near BH
- Approximated (not full GR geodesics)


Integration Methods
===================

See :ref:`Architecture <architecture>` section for integrator equations.

**Leapfrog (Recommended):**
   - Symplectic (preserves phase space)
   - Good energy conservation
   - Used by default

**Euler (Fast but less accurate):**
   - First-order
   - Energy drifts
   - Faster for quick tests


Collision Physics
=================

Detected in ``detect_collisions()`` kernel when particles overlap (r < R1 + R2):

**1. Annihilation (matter + antimatter)**

Example: e⁺ + e⁻ → γ + γ

.. math::

   \text{CM energy} = \sqrt{2} m_e c^2 + KE_{cm}

- Creates 2 photons ina Lorentz-boosted frame
- Energies split based on angular distribution
- Boosts to lab frame

**2. Inelastic Collision (hadrons)**

Example: p + p → π⁻ + π⁺ + π⁰

.. math::

   \text{Invariant mass} = \sqrt{(E_1 + E_2)^2 - (\vec{p}_1 + \vec{p}_2)^2}

- If above pair creation threshold → products spawned
- Decay mode randomly selected from available channels
- Products share kinetic energy

**3. Elastic Scatter**

Example: e⁻ + e⁻ → e⁻ + e⁻

- Coulomb repulsion if charged
- Conservation of momentum + energy
- Scattering angle depends on impact parameter

**4. Pair Creation**

Photon (or high-energy particle) → e⁺ + e⁻

- **Threshold:** ``PAIR_CREATION_THRESHOLD`` (energyin simulation units)
- Kinetic energy partitioned between pair
- Angular distribution isotropic in CM frame


Decay Processes
===============

Particles decay via ``monte_carlo_decay()`` kernel using exponential law:

.. math::

   P(decay) = 1 - \exp(-t/\tau \cdot \gamma) \quad \text{(with SR time dilation)}

**Modes implemented:**

- **2-body decay** (e.g., π⁰ → γ + γ) — Relativistic 2-body kinematics
- **3-body decay** (e.g., ρ⁰ → π⁺ + π⁻ + e.t.c.) — Flat phase-space sampling
- **4-body decay** — Nested 2-body + 2-body (virtual intermediate)
- **5-body decay** — Nested as 2-body + 3-body

**Lorentz boost applied to each decay product:**

- Decay computed in particle's rest frame (CM)
- Products boosted to lab frame using 4-momentum
- Preserves relativistic kinematics

**Time dilation effects:**

- Fast particles live longer (dilated lifetime)
- Near black holes, decay slows (gravitational time dilation)


Particle Catalog
================

40 PDG particles in ``pdg_table.py``:

**Leptons (12)**

- Electrons (e⁻/e⁺ pair), Muons (μ⁻/μ⁺), Tau (τ⁻/τ⁺)
- Associated neutrinos (νₑ, νμ, ντ and antiparticles)

**Gauge Bosons (4)**

- Photon (γ), W±, Z, Gluon (g)

**Higgs (1)**

- Higgs boson (H)

**Mesons (12)**

- Pions (π±, π⁰), Kaons (K±, K⁰), eta (η), phi (φ), rho (ρ), D, B, etc.

**Baryons (8)**

- Nucleons (p, n), Hyperons (Λ, Σ, Ξ, Ω), etc.

**Antibaryons (8)**

- Antiparticles of baryons

Each particle includes:

- **PDG ID** — International particle classifier
- **Mass** — Rest mass in MeV/c²
- **Lifetime** — Proper lifetime (lab frame: dilated by γ)
- **Charge** — Electric charge in units of e
- **Color charge** — For strong interactions (QCD)
- **Decay modes** — List of allowed decay channels with branching ratios


Known Physics Limitations
=========================

See :ref:`Known Issues <known_issues>` for detailed discussion. Summary:

1. **Non-relativistic momentum** — Uses p = m·v instead of p = γ·m·v
2. **Non-relativistic CM energy** — Collision uses rest mass only
3. **Photon kinematics** — Not enforced to v=c
4. **BH gravity simplified** — Not full GR geodesics
5. **3-body phase space flat** — Should be weighted by Dalitz density
6. **Hadronic decays approximated** — W/Z use pion channels, not real jets

These are acceptable for sandbox-level visualization but noted for future improvement.


Example: Proton-Proton Collision
==================================

Sequence of physics in LHC pp preset:

1. **Beams approach:** Two protons at high velocity (v ≈ 0.8c lab frame)
2. **Coulomb repulsion:** Bends trajectories slightly, most collide head-on
3. **Collision detection:** Overlap detected, collision flag set
4. **Invariant mass calc:** E_cm = √((γ₁m₁c² + γ₂m₂c²)² -(\vec{p}_1 + \vec{p}_2)²c²)
5. **Pair creation decision:** If E_cm > threshold → can create e⁺ + e⁻
6. **Product generation:** Decay mode selected randomly
   - E.g., p + p → π⁺ + π⁻ + π⁰ + n + p̄ (multiple pions + neutron + antiproton)
7. **Lorentz boost:** Products boosted to lab frame (preserving relativistic 4-momentum)
8. **Trail spawning:** Each product gets new trail buffer (starts at 1 segment)
9. **Decay queued:** Products will decay via exponential lifetimes


Example: Electron-Positron Annihilation
========================================

1. **Approach:** e⁻ and e⁺ spiral toward each other (opposite charges attract)
2. **Overlap detection:** Collision flagged
3. **Annihilation mode:** Select from available e⁺ + e⁻ → X
   - 63% → 2 photons (γ + γ)
   - 20% → 3 photons (γ + γ + γ)
   - 17% → muon + antimuon (μ⁺ + μ⁻)
4. **Product kinematics:** Photons/muons created with energy split based on original energies
5. **Boosts applied:** Energy and momentum conserved in boost to lab frame
6. **Optical representation:** Flash at collision center, trails for products


Quantum Numbers
===============

Tracked for each particle (for collision/decay consistency checks):

- **Flavor:** Up, down, charm, strange, top, bottom (carried by quarks/baryons)
- **Q-number (color):** r, g, b (quarks/gluons only)
- **Spin:** 0 (scalar), 1/2 (Dirac fermion), 1 (vector meson), 2+ (rare)
- **Lepton number:** +1 (lepton), -1 (antilepton), 0 (other)
- **Baryon number:** +1 (baryon), -1 (antibaryon), 0 (other)

Checked during:
- Decay mode validation (e.g., lepton number conserved)
- Collision partner matching (e.g., q-neutrality after annihilation)

Current implementation tracks but doesn't enforce (sandboxmode allows some unphysical events).


Numerical Precision
===================

- **Float precision:** 32-bit (f32) throughout GPU kernel
- **Accuracy loss:** Accumulated over thousands of steps
- **Energy drift:** ~0.01% per 1000 frames with leapfrog
- **Recommendation:** For long runs (>30k frames), use lower DT or export/restart


Performance Physics Notes
=========================

- Pairwise O(N²) forces dominate at N > 100
- Collision detection O(N²) but early-exit (nearby pairs only)
- Decay probability O(N) loop
- Trail rendering O(N) with Phase 1 filtering
- At 1k particles: Force computation ≈ 50% GPU time, rendering ≈ 30%

See :ref:`Performance <performance>` for optimization strategies.

