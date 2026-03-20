================================================================================
Development Guide
================================================================================

Contribute to the project and extend the simulation.

Setting Up Development Environment
===================================

.. code-block:: bash

   # Clone and setup
   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox

   # Virtual environment
   python -m venv .venv
   source .venv/bin/activate

   # Install with dev tools
   make install

   # Verify
   make test
   make lint


Project Structure
=================

.. code-block:: text

   quantum-collider-sandbox/
   ├── src/quantum_collider_sandbox/
   │   ├── __init__.py
   │   ├── __main__.py           # CLI entry, main loop
   │   ├── config.py             # Constants, presets
   │   ├── simulation.py         # GPU physics (2900 lines)
   │   ├── particles.py          # Taichi field management
   │   ├── renderer.py           # UI, visualization
   │   ├── pdg_table.py          # 40 particles catalog
   │   └── data_loader.py        # I/O (HDF5, JSONL)
   ├── tests/                    # Pytest suite
   │   ├── test_*.py             # 5 test files, ~50 assertions
   │   └── conftest.py
   ├── docs/                     # Sphinx documentation
   │   ├── source/
   │   │   ├── conf.py           # Sphinx config
   │   │   └── *.rst             # Documentation files
   │   └── build/                # Generated HTML
   ├── data/                     # Simulation data
   │   ├── exports/              # HDF5 state files
   │   └── logs/                 # JSONL physics events
   ├── Makefile                  # Build automation
   ├── pyproject.toml            # Package metadata
   ├── .pre-commit-config.yaml   # CI/CD hooks
   └── README.rst


Code Style & Linting
====================

**Automated checks (pre-commit):**

.. code-block:: bash

   # Install pre-commit hooks
   pre-commit install

   # Run checks (automatic on git commit)
   pre-commit run --all-files

**Manual checks:**

.. code-block:: bash

   # Run linter
   make lint

   # Specific tools:
   ruff check src/      # Fast linter
   black src/           # Code formatter
   pylint src/          # Detailed analysis

**Code standards:**

- **Black formatting:** Line length 88
- **Ruff rules:** Default (PEP 8 subset)
- **Pylint:** Target 9.5+ / 10.0 score
- **Imports:** Sorted, no circular dependencies
- **Docstrings:** PEP 257, triple-quote format

**Example docstring:**

.. code-block:: python

   def compute_collision_products(particle_a, particle_b):
       """Generate collision products from two particles.

       Args:
           particle_a: First particle (dict with type, mass, velocity)
           particle_b: Second particle

       Returns:
           list: Product particles (may be empty if no reaction occurs)

       Raises:
           ValueError: If particle types invalid
       """
       ...


Testing
=======

**Run all tests:**

.. code-block:: bash

   make test

**Test files:**

- ``test_config.py`` — Configuration loading
- ``test_particles.py`` — Particle data structures
- ``test_pdg_table.py`` — Particle catalog
- ``test_data_loader.py`` — I/O operations
- ``test_simulation.py`` — Physics correctness (optional)

**Example test:**

.. code-block:: python

   import pytest
   from quantum_collider_sandbox.pdg_table import PARTICLES

   def test_electron_properties():
       """Verify electron mass and charge."""
       e = PARTICLES["electron"]
       assert e["mass"] == pytest.approx(0.511, rel=0.01)
       assert e["charge"] == -1


Adding New Features
===================

**1. New particle type:**

Edit ``pdg_table.py``:

.. code-block:: python

   PARTICLES["my_particle"] = {
       "name": "My Particle",
       "pdg_id": 9999,
       "mass": 5.0,  # MeV/c²
       "lifetime": 1e-10,  # seconds
       "charge": 0,
       "color": (1.0, 0.5, 0.0),  # RGB
       "decay_channels": [
           {"products": [22, 22], "branching_ratio": 1.0},  # 100% → 2 photons
       ]
   }

**2. New force:**

Edit ``simulation.py``, in ``compute_forces()`` kernel:

.. code-block:: python

   @ti.kernel
   def compute_forces(...):
       for i in range(n):
           for j in range(i+1, n):
               # ... existing forces ...

               # Add new force
               dist = pos[j] - pos[i]
               r_mag = dist.norm()
               if r_mag > 1e-6:
                   # Custom force calculation
                   f_mag = my_custom_force(...)
                   force_a = f_mag * dist / r_mag
                   acc[i] += force_a / mass[i]
                   acc[j] -= force_a / mass[j]

Add constant to ``config.py``:

.. code-block:: python

   MY_FORCE_K = 1.0  # Tunable parameter


**3. New preset:**

Edit ``config.py``:

.. code-block:: python

   PRESETS["my_scenario"] = {
       "preset_name": "My Scenario",
       "initial_particles": 50,
       "coulomb_k": 40.0,
       "gravity_g": 6.0,
       "initial_geometry": "sphere",  # or "beam", "cluster", etc.
   }

Then in ``__main__.py``, add to preset dropdown:

.. code-block:: python

   preset_name = ui.label("Presets", choices=["default", "my_scenario", ...])


**4. New UI control:**

Edit ``renderer.py``, in the ImGui panel building:

.. code-block:: python

   my_slider = ui.slider("My Control", min=0.0, max=100.0, value=50.0)
   if my_slider:
       config.MY_FORCE_K = my_slider


Documentation
==============

**Build Sphinx docs locally:**

.. code-block:: bash

   make docs
   # Open docs/build/index.html in browser

**Edit documentation:**

- Docs source in ``docs/source/*.rst`` (reStructuredText format)
- Edit, rebuild with ``make docs``
- Test links and formatting

**Add new page:**

1. Create ``docs/source/mypage.rst``
2. Add to toctree in ``docs/source/index.rst``
3. Run ``make docs`` to verify


Debugging Physics
=================

**Print particle state:**

.. code-block:: python

   @ti.kernel
   def debug_particle(i: ti.i32):
       pos_i = pos[i]
       vel_i = vel[i]
       ti.print(f"Particle {i}: pos={pos_i}, vel={vel_i}")

   debug_particle(0)  # Print first particle

**Check energy conservation:**

.. code-block:: python

   # Before/after step
   ke_before = sim.compute_kinetic_energy()
   sim.step()
   ke_after = sim.compute_kinetic_energy()
   print(f"ΔKE = {ke_after - ke_before:.6f}")

**Verify force magnitudes:**

.. code-block:: python

   forces = sim.get_forces()  # Nx3 array
   print(f"Max force: {np.max(np.linalg.norm(forces, axis=1)):.2f}")
   print(f"Median force: {np.median(np.linalg.norm(forces, axis=1)):.4f}")


Profiling & Performance
=======================

**Profile a simulation:**

.. code-block:: python

   import cProfile
   import pstats
   from quantum_collider_sandbox.simulation import Simulation

   sim = Simulation(preset="default", particles=100)

   profiler = cProfile.Profile()
   profiler.enable()

   for _ in range(100):
       sim.step()

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats("cumulative").print_stats(20)  # Top 20

**GPU profiling:**

.. code-block:: bash

   # NVIDIA
   nvidia-smi dmon -s pucvmet

   # AMD
   rocm-smi --showuse


Continuous Integration
======================

Pre-commit checks (automatic on commit):

1. **ruff** — Fast linting
2. **black** — Code formatting
3. **pylint** — Detailed analysis (9.5+ score minimum)
4. **pytest** — Run all tests (27 must pass)

All checks must pass before commit is accepted.


Contributing Guidelines
=======================

**Before submitting a PR:**

1. Fork the repository
2. Create a feature branch: ``git checkout -b feature/my-feature``
3. Make changes
4. Run ``make lint && make test`` locally
5. Commit with descriptive message:
   ``perf: improve trail rendering (Phase 1 optimization)``
6. Push and open PR

**Commit message format:**

- ``feat:`` New feature
- ``fix:`` Bug fix
- ``perf:`` Performance improvement
- ``docs:`` Documentation update
- ``refactor:`` Code restructuring
- ``test:`` Test additions
- ``chore:`` Maintenance

**Keep commits atomic:**

- One logical change per commit
- Run tests after each commit
- Clean git history (rebase if needed)


Phase 1 Optimization Development
================================

(The recent optimization implemented)

**Changes made:**

1. Reduced ``TRAIL_LENGTH`` 400 → 40 in ``config.py``
2. Added skip logic to ``build_trail_lines()`` kernel in ``simulation.py``
3. Extracted duplicate spawn code into ``_spawn_random_particles_internal()`` helper
4. Updated ``__main__.py`` to use helper function
5. Fixed `.pre-commit-config.yaml` for venv independence

**Impact:**

- 10x vertex reduction (80ok → 80k vertices/frame)
- 2-3x FPS improvement (3-5 → 8-15 FPS at 1k particles)
- All 27 tests passing, 10.0/10 pylint score

**Next phases (planned):**

- Phase 2: GPU kernel consolidation (reduce launch overhead)
- Phase 3: Adaptive trail density (motion-based sampling)
- Phase 4: GPU LOD rendering (distance-based culling)


Troubleshooting Development
============================

**Import errors after editing:**

.. code-block:: bash

   # Reinstall package
   pip install -e ".[dev]"

**Tests fail after changes:**

.. code-block:: bash

   # Run single test file
   pytest tests/test_physics.py -v

**Linting errors:**

.. code-block:: bash

   # Auto-fix with black
   black src/

   # Fix some ruff issues
   ruff check --fix src/


Release Process
===============

*(For maintainers)*

1. Update version in ``pyproject.toml``
2. Update ``CHANGELOG.rst``
3. Ensure all tests pass: ``make test``
   4. Ensure all lints pass: ``make lint``
5. Tag commit: ``git tag v1.0.5``
6. Push: ``git push origin v1.0.5``

