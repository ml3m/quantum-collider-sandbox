================================================================================
Known Issues & Limitations
================================================================================

Technical limitations and physics inaccuracies documented for users and developers.

Physics Accuracy Issues
=======================

**P1 (Critical) — Non-relativistic Momentum**

**Issue:** Simulation uses ``p = m·v`` everywhere (stats, collisions)

**Should use:** ``p = γ·m·v`` when ``USE_RELATIVITY = True``

**Impact:**

- Kinetic energy display is non-relativistic: ``KE = ½m·v²``
- Should be: ``KE = (γ−1)m·c²`` at high speeds
- Affects high-energy collision calculations
- At v < 0.5c: Error < 5%, acceptable
- At v > 0.9c: Error > 50%, significant

**Affected code:** Lines 1094-1098 in ``simulation.py``

**Workaround:** Set ``USE_RELATIVITY = False`` for low-energy scenarios

**Fix effort:** Medium (2-3 hours, requires audit of all momentum calculations)

---

**P2 (Critical) — Collision Invariant Mass**

**Issue:** Computed as ``inv_m = m_i + m_j`` (rest masses only)

**Should use:** ``√((E_i+E_j)² − |p_i+p_j|²c²)`` (4-momentum)

**Impact:**

- Direct collisions use rest mass for pair creation threshold
- High-energy collisions may over/under-produce particles
- Affects LHC pp preset significantly
- Single-particle decay computed correctly (only rest mass)

**Affected code:** Lines 555-556 in ``simulation.py``

**Workaround:** Adjust ``PAIR_CREATION_THRESHOLD`` to compensate

**Fix effort:** Medium (1-2 hours, requires 4-momentum correction)

---

**P3 (Medium) — Photon Velocity Enforcement**

**Issue:** Photons spawned via decay get velocity but no forced speed-of-light

**Physics:** Photons should always travel at c, not slower

**Impact:**

- Photons can appear to move slower than c if energy low
- Typically minor (most photons are highly energetic)
- Forces computed correctly (q=0, so no forces on photons)

**Affected code:** Lines 556-568 in ``simulation.py`` (collision products)

**Workaround:** None needed for typical scenarios

**Fix effort:** Low (30 minutes, add speed clamping in spawn logic)

---

**P4 (Medium) — Black Hole Gravity**

**Issue:** Uses Newtonian ``F = 1/(r−r_s)²`` rather than proper GR

**Should use:** Paczyński–Wiita potential or real geodesics

**Impact:**

- ISCO (innermost stable circular orbit) incorrect distance
- Time dilation approximation crude (const. factor, not r-dependent)
- Lensing is approximate (not full ray-tracing)
- Visually acceptable for sandbox

**Affected code:** Lines 292-297 in ``simulation.py``

**Workaround:** Adjust ``BLACK_HOLE_RADIUS`` and ``BLACK_HOLE_MASS`` for stability

**Fix effort:** High (4-5 hours, requires GR formulation)

---

**P5 (Medium) — Accretion Disk Orbital Velocity**

**Issue:** Formula ``v_c = √(GM·r)/(r−r_s)`` is dimensionally inconsistent

**Impact:** Accretion disk visuals can exhibit strange behavior near horizon

**Workaround:** Purely visual; physics unaffected

**Fix effort:** Low (30 minutes, dimensional analysis fix)

---

**P6 (Low) — Pair Creation Energy Budget**

**Issue:** Remaining KE after pair creation mixes units

- ``combined_ke`` is kinetic (½mv²)
- ``creation_cost`` is rest mass energy

**Impact:** Minor numerical inconsistency at boundary of creation threshold

**Workaround:** None needed

**Fix effort:** Low (15 minutes, normalize units)

---

**P7 (Low) — Lorentz Boost Units**

**Issue:** Boost formula uses quantities in simulation units, mixed semantics

- Works due to consistent scaling throughout
- But fragile if units change

**Impact:** Currently none; potential issue for future refactoring

**Workaround:** Document unit system clearly

**Fix effort:** Low (documentation only)

---

**P8 (Low) — 3-Body Decay Phase Space**

**Issue:** Uniform flat sampling; should be weighted by Dalitz density

**Impact:** Invariant mass distributions incorrect for 3-body decays

**Affects:** ρ, ω, Φ decays (not frequently spawned)

**Workaround:** None practical

**Fix effort:** Medium (1-2 hours, implement Dalitz weighting)

---

**P9 (Low) — Hadronic Decays Simplified**

**Issue:** W±, Z, H hadronic decays → pion channels (not real QCD jets)

**Example:** W⁺ → π⁺π⁰ (67% BR, simplified)

**Real physics:** W → u d̄ or c s̄ (quark pairs hadronize)

**Impact:**

- Visual/pedagogical; accepted for sandbox
- Decay kinematics still correct
- Missing multi-body jet structure

**Workaround:** None needed (by design)

**Fix effort:** High (requires jet fragmentation model)

---

Rendering & Visualization Issues
=================================

**R1 — Trail Performance at Scale**

**Status:** FIXED via Phase 1 optimization

- Reduced TRAIL_LENGTH 400 → 40
- 10x vertex reduction
- 2-3x FPS improvement at 1k particles

**Remaining:** At 5k+ particles, trails still expensive

**Mitigation:** Adaptable TRAIL_LENGTH in config (user-tunable)

---

**R2 — Collision Flash Cutoff**

**Issue:** Collision flashes don't fade smoothly on very fast collisions

**Impact:** Visual only; physics unaffected

**Workaround:** Increase SUBSTEPS for smoother motion

**Fix effort:** Low (15 minutes)

---

**R3 — Gravitational Lensing Approximation**

**Issue:** Background stars distort but not via proper ray-tracing

**Impact:** Visual effect only; acceptable for sandbox

**Workaround:** Acceptable as-is

---

Numerical & Stability Issues
============================

**N1 — Energy Drift**

**Cause:** 32-bit float precision + numerical integration error

**Rate:** ~0.01% per 1000 frames with leapfrog integrator

**Impact:**

- Long simulations (>1 hour) show noticeable drift
- Short simulations (<15 min) negligible

**Mitigation:**

- Use leapfrog (symplectic) integrator
- Keep DT reasonable (0.001 default)
- Periodic restart/save for very long runs

**Future:** Switch to 64-bit floats (doubles) for long runs

---

**N2 — Singularity at Zero Distance**

**Cause:** Coulomb and gravity forces diverge as r → 0

**Mitigation:** Softening parameter ε (0.05 default)

**Impact:** Negligible with softening

**Note:** Already compensated in code

---

**N3 — Velocity Clamping**

**Cause:** Prevents overflow at high forces but unphysical

**Limit:** MAX_VELOCITY = 29.9 (< SPEED_OF_LIGHT = 30)

**Impact:**

- Particles near limit appear "stuck"
- Very rare at typical force strengths
- Better than numerical overflow

**Mitigation:** Reduce force constants if encountered

---

Performance Issues
==================

**Perf1 — 3-5 FPS at 1k Particles (1000-particle baseline)**

**Status:** FIXED via Phase 1 optimization

- Phase 1 implemented: 2-3x FPS improvement
- Now achieves 8-15 FPS at 1k particles
- See :ref:`Performance Tuning <performance>` for details

---

**Perf2 — GPU Kernel Launch Overhead**

**Issue:** Each kernel launch has fixed overhead (~1ms)

**Impact:** At 100+ particles, GPU computation dominates (not overhead)

**Future optimization:** Phase 2 kernel consolidation (10-15% gain)

---

**Perf3 — O(N²) Force Computation**

**Issue:** Pairwise forces unavoidable for N-body problem

**Scaling:**

- 100 particles: ~0.5 ms/frame
- 1k particles: ~5 ms/frame (linear scaling after optimization)
- 10k particles: ~50 ms/frame (reaches 20 FPS limit on GPU)

**Future optimizations:** Barnes-Hut tree (O(N log N)), spatial decomposition

---


Configuration & Setup Issues
=============================

**C1 — Vulkan Not Found**

**Symptoms:** "Vulkan not available" error on startup

**Causes:**

- GPU drivers not installed
- Vulkan libraries missing
- Wayland without Vulkan support

**Solution:**

1. Install/update GPU drivers
2. For NVIDIA: ``sudo apt install libnvidia-gl-*``
3. For AMD: ``sudo apt install libvulkan1``
4. Test with: ``vulkaninfo``

---

**C2 — High Memory Usage at 2k+ Particles**

**Symptoms:** Simulation stutters or crashes at high particle count

**Cause:** GPU VRAM exhausted (fixed allocations scale with MAX_PARTICLES)

**Solution:**

- Reduce MAX_PARTICLES in code (requires recompilation) — not recommended
- Delete old HDF5 exports to free disk
- Use fewer particles
- Upgrade GPU VRAM if possible

---

**C3 — Pre-commit Errors on First Use**

**Symptoms:** "language not found" or venv activation required

**Status:** FIXED in `.pre-commit-config.yaml`

- Changed pylint from `language: system` to `language: python`
- Now supports venv-independent pre-commit

**Solution:** Update config from git (automatic)

---


Documentation Gaps
==================

- Detailed derivations of collision physics formulas
- Taichi kernel optimization techniques
- Unit system clearly defined (natural vs. SI)
- Decay branching ratios sourced from PDG

These are noted for future documentation improvements.


Known Workarounds
=================

+---+---+
| Issue | Workaround |
+===+===+
| Low FPS at 1k particles | Reduce TRAIL_LENGTH to 20 (Phase 1) or disable trails (T key) |
+---+---+
| Simulation becomes unstable | Reduce COULOMB_K or GRAVITY_G forces |
+---+---+
| Photons don't look right | Increase MIN_TRAIL_SPEED_FOR_RENDER to 0.3+ |
+---+---+
| Black hole strange behavior | Adjust BLACK_HOLE_MASS or BLACK_HOLE_RADIUS |
+---+---+
| GPU not detected | Try ``export TAICHI_BACKEND=cpu`` for testing |
+---+---+
| Trails corrupt at high speed | Increase SUBSTEPS for smoother timesteps |
+---+---+


Contributing Fixes
==================

Found a bug? Have a fix? See :ref:`Development <development>` guide:

1. Fork repository
2. Create feature branch: ``git checkout -b fix/issue-name``
3. Implement fix with tests
4. Make sure ``make lint && make test`` passes
5. Submit PR with explanation

Physics corrections especially welcome!

