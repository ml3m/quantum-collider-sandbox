.. Quantum Collider Sandbox documentation master file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Quantum Collider Sandbox
=========================

Real-Time GPU Particle Physics Simulation with PDG-accurate particle catalog.
40 observable particles, real masses, lifetimes, decay channels, and proper
relativistic kinematics.

.. image:: ../../assets/1.png
   :alt: Quantum Collider Sandbox screenshot
   :width: 100%
   :align: center

Quick Start
-----------

.. code-block:: bash

   git clone https://github.com/ml3m/quantum-collider-sandbox.git
   cd quantum-collider-sandbox
   python -m venv .venv && source .venv/bin/activate
   make install && make run

On Windows, activate with ``.venv\Scripts\activate`` instead.

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents

   parameters
   contact

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
