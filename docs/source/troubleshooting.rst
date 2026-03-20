================================================================================
Troubleshooting & FAQ
================================================================================

Common problems and their solutions.

Quick Troubleshooting Guide
===========================

**Application won't start**

1. Check Python version: ``python --version`` (need 3.10+)
2. Check virtual environment: ``source .venv/bin/activate``
3. Check Vulkan: ``vulkaninfo | head -20``
4. Try CPU backend: ``export TAICHI_BACKEND=cpu && python -m quantum_collider_sandbox``

---

**FPS very low (< 10 at 100 particles)**

1. Check GPU in use: ``nvidia-smi`` or ``rocm-smi``
2. Is window resolution too high? (try 1280x720)
3. Are trails disabled? (press T key)
4. Try: ``export TAICHI_BACKEND=cpu`` to test CPU

---

**GPU shows 0% usage (CPU maxed out)**

- Typical on first run (Taichi JIT compiling kernels)
- Wait 3-5 seconds
- If persists: Taichi installation issue

---

**Particles not visible**

1. Try resetting: Press ``R`` key
2. Zoom out: Scroll mouse wheel down
3. Rotate camera: Right-mouse drag
4. Check particle count slider (ImGui, should be > 0)
5. Press H for help overlay

---

**Simulation crashes when spawning many particles**

1. Reduce particle count (ImGui slider)
2. Check VRAM usage: ``nvidia-smi``
3. Close other GPU-using applications
4. Upgrade GPU or reduce other settings

---

**Data export fails**

1. Check ``data/exports/`` directory exists and is writable
2. Check disk space: ``df -h``
3. Try: ``mkdir -p data/{exports,logs}``

---

Installation Problems
=====================

**"ModuleNotFoundError: No module named taichi"**

.. code-block:: bash

   # Reinstall from scratch
   rm -rf .venv
   python -m venv .venv
   source .venv/bin/activate
   make install

**"pip: command not found"**

.. code-block:: bash

   # Use python -m pip instead
   python -m pip install -e ".[dev]"

**"No module named 'quantum_collider_sandbox'"**

.. code-block:: bash

   # Reinstall in dev mode
   pip install -e .

**Virtual environment activation fails**

*Linux/macOS:*

.. code-block:: bash

   chmod +x .venv/bin/activate
   source .venv/bin/activate

*Windows (PowerShell):*

.. code-block:: powershell

   .venv\Scripts\Activate.ps1

**"fatal: not a git repository" during make install**

.. code-block:: bash

   # Init git
   git init
   git add .
   git commit -m "initial"

GPU & Driver Issues
===================

**"Vulkan not available" or "Cannot find GPU"**

*NVIDIA:*

.. code-block:: bash

   # Check NVIDIA GPU
   nvidia-smi

   # Install Vulkan
   sudo apt install vulkan-tools libvulkan1
   vulkaninfo | grep -i "Device \|vulkan"

*AMD:*

.. code-block:: bash

   # Check AMD GPU
   rocm-smi

   # Install Vulkan
   sudo apt install vulkan-tools
   vulkaninfo

*Intel:*

.. code-block:: bash

   # Check Intel GPU
   lspci | grep -i vga

   # Install Vulkan
   sudo apt install vulkan-tools

**"GPU memory allocation failed"**

.. code-block:: bash

   # Check available VRAM
   nvidia-smi

   # Try CPU backend for testing
   export TAICHI_BACKEND=cpu
   python -m quantum_collider_sandbox

   # Or reduce particles / disable trails

**Taichi backend won't recognize GPU**

.. code-block:: bash

   # Force GPU selection
   export TAICHI_DEVICE=0  # Device 0
   export TAICHI_BACKEND=cuda  # Force CUDA (NVIDIA)
   python -m quantum_collider_sandbox

   # Check available backends
   python -c "import taichi as ti; print(ti.supported_archs())"

**"Out of GPU memory at 1k particles"**

Typical GPU VRAM for different counts:

- 100 particles: ~50 MB
- 500 particles: ~150 MB
- 1k particles: ~300 MB (w/ trails; Phase 1: ~100 MB)
- 2k particles: ~600 MB

If you have 2GB VRAM:

.. code-block:: python

   # Reduce trail length in config.py
   TRAIL_LENGTH = 20  # Was 40
   # Or disable trails entirely
   TRAILS_ENABLED_DEFAULT = False

Simulation & Physics Issues
===========================

**Particles freeze or move erratically**

1. Reduce force constants (ImGui sliders)
2. Increase SUBSTEPS (ImGui slider: 4 → 8)
3. Reduce DT to half value in config
4. Check if particles are frozen (try R to reset)

**Energy increases or decreases unexpectedly**

- Small changes (< 1% per 100 steps): Normal (numerical precision)
- Large changes: Reduce DT or increase SUBSTEPS
- See :ref:`Known Issues <known_issues>` for energy drift info

**Collisions don't seem to happen**

1. Spawn more particles (ImGui slider)
2. Increase Coulomb force to bring particles closer
3. Check ``detect_collisions()`` radius in code (should be particle size sum)
4. Enable collision flash visual (should see yellow flashes)

**Dead particles not removed**

- Compaction happens in ``do_maintenance()``
- Press ``R`` to completely reset
- Check particle count in ImGui (should decrease as particles decay/escape)

**Trails look buggy or cut off**

1. Reduce TRAIL_LENGTH in config (40 → 20)
2. Increase SUBSTEPS (smoother tracking)
3. Check MIN_TRAIL_LENGTH_FOR_RENDER (should be 3)
4. Try pressing T to toggle trails off/on

**Black hole seems to repel particles**

- Check ``BLACK_HOLE_MASS`` is positive
- Typical value: ~1000 (relative to particle masses)
- Reduce if repulsion too strong

Visualization Issues
====================

**UI panels invisible / ImGui broken**

.. code-block:: bash

   # Rebuild with fresh debug info
   python -m quantum_collider_sandbox

   # Press H to show/hide help
   # Press Escape to toggle ImGui panel

**Window won't resize**

- Windowed mode: Currently fixed resolution
- Change WINDOW_WIDTH / WINDOW_HEIGHT in config
- Restart simulation

**Colors look wrong**

1. Check monitor color profile
2. Adjust ``BACKGROUND_COLOR`` in config
3. Colors hard-coded per particle type in ``pdg_table.py``

**Starfield/background doesn't render**

.. code-block:: python

   # In config.py, check:
   BACKGROUND_STARS = True
   BACKGROUND_COLOR = (0.01, 0.01, 0.03)

**Black hole effects (lensing, disk) not visible**

- Works only with ``use_black_hole=True`` in preset
- Try "Black Hole" preset from ImGui dropdown
- Disk is behind particles (Z-ordering)

Performance Issues
==================

**FPS drops when moving camera**

- GPU is bottleneck (rendering, not physics)
- Reduce window resolution
- Disable trails (T key)
- Reduce trail length (config: TRAIL_LENGTH = 20)

**FPS inconsistent (stutters and freezes)**

1. Check for CPU bottleneck: ``top`` or Task Manager
2. Close other applications
3. Reduce SUBSTEPS (faster but less smooth physics)
4. Check GPU temperature: ``nvidia-smi``

**Simulation is CPU-bound, not GPU**

- Normal on first run (JIT compilation)
- Check console for compilation messages
- Subsequent runs should be GPU-bound
- If persists: Check ``TAICHI_BACKEND`` is correct

**Memory usage grows over time**

- File handles not closing: Check ``data_loader.py`` context managers
- GPU memory may be fragmented after long runs
- Restart simulation periodically

Data I/O Issues
===============

**Export fails with "Permission denied"**

.. code-block:: bash

   # Create data directories with proper permissions
   mkdir -p data/{exports,logs}
   chmod 755 data/{exports,logs}

**HDF5 export creates but can't import back**

.. code-block:: bash

   # Verify file structure
   h5dump -H data/exports/state_*.h5

   # Try with verbose loading
   python -c "
   import h5py
   with h5py.File('data/exports/state_1234567.h5', 'r') as f:
       print(list(f.keys()))
   "

**JSONL physics log is empty**

1. Make sure collisions/decays occur:
   - Spawn enough particles
   - Check physics presets (some have no collisions by default)
   - Wait for collision events to happen
2. Export while simulation is running: ``Ctrl+Shift+J``
3. Check file was created: ``ls -la data/logs/`

**Load state doesn't restore particles**

1. Verify HDF5 file integrity: ``h5check data/exports/state_*.h5``
2. Try converting with h5py first:
   
   .. code-block:: python

      import h5py
      with h5py.File("old_state.h5", "r") as f:
          # Check contents
          for key in f.keys():
              print(f"{key}: {f[key].shape}")


Platform-Specific Issues
========================

**Linux (Most common development platform)**

Usually works out-of-the-box with NVIDIA/AMD drivers.

**macOS**

- Vulkan support limited; may need Metal backend
- Set ``export TAICHI_BACKEND=metal``
- Homebrew install: ``brew install vulkan-loader``

**Windows**

- Use ``.venv\Scripts\activate`` instead of `. .venv/bin/activate`
- PowerShell may need execution policy: ``Set-ExecutionPolicy -ExecutionPolicy RemoteSigned``
- GPU driver: Must manually install (Windows Update may not be sufficient)

**WSL (Windows Subsystem for Linux)**

- WSL2 with GPU support: Requires recent NVIDIA drivers (495+)
- WSL1: No GPU support
- Use CPU backend in WSL1: ``export TAICHI_BACKEND=cpu``

Getting Help
============

**Check status by:**

1. Running tests: ``make test`` (if passes, core sim is OK)
2. Checking logs: Simulation prints to stderr
3. Searching issues: https://github.com/ml3m/quantum-collider-sandbox/issues
4. Reading documentation: https://ml3m.github.io/quantum-collider-sandbox/

**To report a bug:**

1. Collect info:
   - ``python --version``
   - ``nvidia-smi`` (or AMD equivalent)
   - Operating system
   - Steps to reproduce
2. Run with debug output:
   
   .. code-block:: bash

      export TAICHI_LOG_LEVEL=debug
      python -m quantum_collider_sandbox 2>&1 | head -100

3. File GitHub issue with:
   - Title: Concise description
   - Environment: Python, GPU, OS
   - Steps to reproduce
   - Error messages/logs
   - Expected vs. actual behavior


FAQ
===

**Q: What GPU do I need?**

A: Any GPU with Vulkan support (NVIDIA 600+, AMD Radeon R7+, Intel iGPU). 4GB+ VRAM recommended for 2k+ particles.

**Q: Can I run on CPU?**

A: Yes, but slowly. Use ``export TAICHI_BACKEND=cpu`` for testing.

**Q: What's the max particle count?**

A: Soft limit ~2k for smooth FPS (30+). Hard limit is 100 (MAX_PARTICLES). Can increase but requires code recompilation.

**Q: Why is my energy not conserved?**

A: 32-bit float precision + numerical integration error. Rate ~0.01% per 1000 frames. Use leapfrog integrator for best conservation.

**Q: Can I save/load simulations?**

A: Yes! Press ``Ctrl+S`` to save state to HDF5. Press ``Ctrl+L`` to load.

**Q: How do I export data for analysis?**

A: Press ``Ctrl+Shift+J`` to export physics events (JSONL). Use Python to analyze collision/decay events.

**Q: Can I extend the simulation with custom particles?**

A: Yes! Edit ``pdg_table.py`` to add particles. See :ref:`Development <development>` guide.

**Q: Is this scientifically accurate?**

A: Mostly for sandbox use. See :ref:`Known Issues <known_issues>` for physics inaccuracies. Good for education; not research-grade.

**Q: What license is this?**

A: Check ``LICENSE`` file (typically open source). See repo for details.

