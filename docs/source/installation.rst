================================================================================
Installation & Setup
================================================================================

Detailed installation instructions and troubleshooting.

System Requirements
===================

**Hardware**

- **GPU:** NVIDIA, AMD, or Intel with Vulkan support (4GB+ VRAM recommended)
- **CPU:** Multi-core processor (4+ cores)
- **RAM:** 8GB+ (16GB+ for 2k+ particles)
- **Disk:** 500MB for installation

**Software**

- **Python:** 3.10, 3.11, or 3.12 (3.12.2 recommended)
- **OS:** Linux, Windows 10/11, macOS 12+
- **Vulkan drivers:** Must be installed and working


Step-by-Step Installation
==========================

**1. Clone the repository**

.. code-block:: bash

   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox


**2. Create virtual environment**

*Linux / macOS:*

.. code-block:: bash

   python3.12 -m venv .venv
   source .venv/bin/activate

*Windows:*

.. code-block:: bash

   py -3.12 -m venv .venv
   .venv\Scripts\activate

**3. Install dependencies**

.. code-block:: bash

   make install

Or manually:

.. code-block:: bash

   pip install --upgrade pip setuptools wheel
   pip install -e ".[dev]"

This installs:
   - taichi ≥ 1.7.0 (GPU framework)
   - numpy, scipy (numerical computing)
   - h5py (HDF5 I/O)
   - pygame (events, optional)
   - pre-commit (CI/CD hooks)


**4. Verify installation**

.. code-block:: bash

   make test

Expected output:
   - 27 tests pass
   - Execution time ~0.6s
   - No errors


**5. Run**

.. code-block:: bash

   make run

Or directly:

.. code-block:: bash

   python -m quantum_collider_sandbox


Development Setup
=================

For contributing to the codebase:

.. code-block:: bash

   # Install with dev tools
   pip install -e ".[dev]"

   # Install pre-commit hooks
   pre-commit install

   # Run linting
   make lint

   # Run tests
   make test

   # Build docs
   make docs


Taichi Backend Configuration
=============================

By default, the app starts with Vulkan. To use a different backend, set
``QUANTUM_COLLIDER_ARCH`` before launching:

**CUDA (NVIDIA GPUs):**

.. code-block:: bash

   export QUANTUM_COLLIDER_ARCH=cuda
   python -m quantum_collider_sandbox

**CPU (for debugging):**

.. code-block:: bash

   export QUANTUM_COLLIDER_ARCH=cpu
   python -m quantum_collider_sandbox

**Auto-detect preferred GPU backend:**

.. code-block:: bash

   export QUANTUM_COLLIDER_ARCH=gpu
   python -m quantum_collider_sandbox


Makefile Targets
================

.. list-table::
   :header-rows: 1
   :widths: 15 65

   * - Target
     - Description

   * - ``make run``
     - Start the simulation (main entry point)

   * - ``make install``
     - Install package in editable mode with dev dependencies

   * - ``make test``
     - Run pytest test suite

   * - ``make lint``
     - Run pylint on source code

   * - ``make test-cov``
     - Run pytest with coverage report

   * - ``make format-check``
     - Run ruff + black format checks

   * - ``make format``
     - Auto-fix formatting with ruff + black

   * - ``make docs``
     - Build Sphinx documentation

   * - ``make prod-ready``
     - Run format-check, lint, and coverage tests


Troubleshooting
===============

**"No GPU detected"**

If Taichi cannot find your GPU:

1. Check your GPU drivers:
   
   .. code-block:: bash

      glxinfo | grep "OpenGL driver"

2. Verify Vulkan support:
   
   .. code-block:: bash

      vulkaninfo

3. Force CPU backend for testing:
   
   .. code-block:: bash

      export QUANTUM_COLLIDER_ARCH=cpu
      python -m quantum_collider_sandbox

**"ImportError: cannot import taichi"**

Reinitialize your virtual environment:

.. code-block:: bash

   rm -rf .venv
   python -m venv .venv
   source .venv/bin/activate
   make install

**"FPS is very low (< 1 FPS)"**

See :ref:`Performance Tuning <performance>` section. Common causes:

- TRAIL_LENGTH too high (reduce from 40 to 5-10)
- Too many particles for your GPU
- Rendering resolution too high (reduce WINDOW_WIDTH/HEIGHT)

**"Particles not rendering"**

1. Try resetting view: ``R`` key
2. Check particle count slider (ImGui left panel)
3. Rotate camera: right-mouse drag
4. Verify GPU backend is working: check console for errors


Getting Help
============

- **Documentation:** https://ml3m.github.io/quantum-collider-sandbox/
- **Issues:** https://github.com/ml3m/quantum-collider-sandbox/issues
- **Quick test:** Run ``make test`` to verify physics engine
- **Debug mode:** Check console output for Taichi warnings
