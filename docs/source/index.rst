================================================================================
Quantum Collider Sandbox
================================================================================

Real-Time GPU Particle Physics Simulation with PDG-accurate particle catalog.

.. image:: ../../assets/1.png
   :alt: Quantum Collider Sandbox screenshot
   :width: 100%
   :align: center

**40 observable particles** with real masses, lifetimes, decay channels, and proper
relativistic kinematics. Built on Taichi for GPU acceleration (Vulkan/CUDA/CPU backends).

.. toctree::
   :maxdepth: 3
   :caption: Getting Started

   quickstart
   installation

.. toctree::
   :maxdepth: 3
   :caption: Usage & Features

   usage
   presets
   controls

.. toctree::
   :maxdepth: 3
   :caption: Configuration

   parameters
   configuration
   performance

.. toctree::
   :maxdepth: 3
   :caption: Technical

   architecture
   physics
   api

.. toctree::
   :maxdepth: 2
   :caption: Development & Reference

   development
   known_issues
   troubleshooting


Quick Start
-----------

.. code-block:: bash

   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox
   python -m venv .venv && source .venv/bin/activate
   make install && make run

On Windows, activate with ``.venv\Scripts\activate`` instead.

Key Features
============

🎯 **Accurate Physics**
   - 40 PDG particles (leptons, bosons, Higgs, mesons, baryons)
   - Relativistic 2-5 body decays with Lorentz boosts
   - Quantum numbers (flavor, color, spin) tracking
   - Time dilation (special + general relativity)

⚡ **GPU Acceleration**
   - Real-time simulation at 1k-2k particles
   - Taichi backend (Vulkan/CUDA/CPU)
   - Phase 1 trail optimization: 10x vertex reduction
   - Optimized for modern GPUs

🎨 **Advanced Visualization**
   - Particle trails with motion filtering
   - Collision flashes and decay events
   - Black hole accretion disk & photon ring
   - Gravitational lensing effects
   - 3D starfield background

🔧 **Configurable Physics**
   - 10 simulation presets
   - Coulomb, Newtonian, strong, and magnetic forces
   - Force constants editable in real-time
   - Custom particle spawning

📊 **Data I/O**
   - HDF5 state export/import
   - JSONL physics event logging
   - CSV collision data
   - CMS/ATLAS format support


System Requirements
===================

**Hardware**
   - GPU with Vulkan support (NVIDIA, AMD, Intel)
   - 2GB+ VRAM (4GB+ recommended for 1k+ particles)
   - Multi-core CPU (4+ cores)

**Software**
   - Python 3.10 – 3.12 (3.12.2 recommended)
   - Vulkan drivers installed and working

**Tested Platforms**
   - Linux (main development platform)
   - Windows 10/11
   - macOS 12+


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
