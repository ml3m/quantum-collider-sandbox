"""Simulation and window configuration constants."""

from pathlib import Path

# Directory for exported HDF5 state files
# Uses project root (parent of src/) when possible, else cwd/data/exports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPORT_DIR = _PROJECT_ROOT / "data" / "exports"

MAX_PARTICLES = 100
TRAIL_LENGTH = 1000

DT = 0.002
SUBSTEPS = 3
COULOMB_K = 40.0
GRAVITY_G = 6.0
SOFTENING = 0.05
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

NUM_TYPES = 48

BH_MASS = 200.0

# "euler" = simple Euler (faster, less accurate); "leapfrog" = symplectic (better energy)
INTEGRATOR = "leapfrog"
