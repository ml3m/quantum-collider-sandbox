================================================================================
Quick Start Guide
================================================================================

Get the simulation running in minutes.

Installation (60 seconds)
==========================

**Linux / macOS:**

.. code-block:: bash

   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox
   python -m venv .venv && source .venv/bin/activate
   make install
   make run

**Windows:**

.. code-block:: bash

   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   python -m quantum_collider_sandbox

First Run
=========

When you start the simulation:

1. **Wait for initialization** (~3-5 seconds)
   - Taichi loads (first-time JIT compilation)
   - GPU buffers allocate

2. **You should see:**
   - 3D particle visualization in center
   - ImGui control panels on left
   - Status bar showing particle count, FPS, energy

3. **Try these keys immediately:**
   - ``SPACE`` — Play/pause simulation
   - ``R`` — Reset (spawn default particles)
   - ``T`` — Toggle particle trails
   - Mouse scroll — Zoom camera
   - Right-mouse drag — Rotate view


Common First Steps
==================

**Spawn more particles:**
   1. Use ImGui "# Particles" slider on left panel (0-100)
   2. Or press ``+`` / ``-`` keys to increment

**Change simulation preset:**
   1. Click "Presets" dropdown in ImGui panel
   2. Select one: Rutherford, Cyclotron, LHC pp, e⁺e⁻ annihilation, etc.

**Turn off trails:**
   1. Press ``T`` key to toggle trails (saves FPS)
   2. Or disable in ImGui "Trails" checkbox

**Adjust physics constants (real-time):**
   1. Find sliders: Coulomb K, Gravity G, Magnetic B, etc.
   2. Drag to tune forces

**Export data:**
   1. Press ``Ctrl+S`` to save current state as HDF5
   2. Press ``Ctrl+Shift+J`` to export physics events as JSONL

Control Reference (Quick)
==========================

+---+---+
| Action | Key |
+===+===+
| Play/Pause | ``SPACE`` |
+---+---+
| Reset | ``R`` |
+---+---+
| Spawn +1 particle | ``+`` |
+---+---+
| Remove particle | ``-`` |
+---+---+
| Toggle trails | ``T`` |
+---+---+
| Toggle UI | ``H`` |
+---+---+
| Save state | ``Ctrl+S`` |
+---+---+
| Help | ``?`` or ``H`` |
+---+---+

Next Steps
==========

See full documentation:

- **Advanced Controls** → :ref:`Controls Reference <controls>`
- **Configuration** → :ref:`Tuning Parameters <configuration>`
- **Presets Explained** → :ref:`Built-in Presets <presets>`
- **Physics Model** → :ref:`Physics Background <physics>`
- **Performance Tuning** → :ref:`Optimization Guide <performance>`
- **API** → :ref:`Python API Reference <api>`
