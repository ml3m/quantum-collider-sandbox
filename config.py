MAX_PARTICLES = 2000
TRAIL_LENGTH = 80

DT = 0.002
SUBSTEPS = 3
COULOMB_K = 40.0
GRAVITY_G = 0.0
SOFTENING = 0.05
CUTOFF_RADIUS = 15.0

MAGNETIC_FIELD = (0.0, 0.0, 0.0)
E_FIELD = (0.0, 0.0, 0.0)

STRONG_FORCE_K = 0.0
STRONG_FORCE_RANGE = 0.5

SPEED_OF_LIGHT = 30.0
USE_RELATIVITY = False

SYNCHROTRON_COEFF = 0.0

COLLISION_RESTITUTION = 0.85
MAX_VELOCITY = 25.0
SPAWN_VELOCITY_SPREAD = 2.5
PAIR_CREATION_THRESHOLD = 15.0

BOUNDARY_MODE = "reflect"
BOUNDARY_SIZE = 12.0

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
WINDOW_TITLE = "Quantum Collider Sandbox"

CAMERA_POS = (0.0, 2.0, 22.0)
CAMERA_LOOKAT = (0.0, 0.0, 0.0)
CAMERA_FOV = 50

BACKGROUND_COLOR = (0.01, 0.01, 0.03)

BASE_PARTICLE_RADIUS = 0.08
PARTICLE_RADIUS_SCALE = 0.35

NUM_TYPES = 10

PARTICLE_TYPES = {
    0: {"name": "proton",     "mass": 1.0,    "charge":  1.0,  "radius": 0.15, "decay_prob": 0.0,    "color": (0.25, 0.55, 1.0),  "baryon": True},
    1: {"name": "electron",   "mass": 0.005,  "charge": -1.0,  "radius": 0.06, "decay_prob": 0.0,    "color": (1.0,  0.85, 0.15), "baryon": False},
    2: {"name": "pion+",      "mass": 0.15,   "charge":  1.0,  "radius": 0.10, "decay_prob": 0.004,  "color": (1.0,  0.25, 0.25), "baryon": False},
    3: {"name": "pion-",      "mass": 0.15,   "charge": -1.0,  "radius": 0.10, "decay_prob": 0.004,  "color": (0.25, 1.0,  0.25), "baryon": False},
    4: {"name": "kaon",       "mass": 0.50,   "charge":  1.0,  "radius": 0.12, "decay_prob": 0.002,  "color": (1.0,  0.55, 0.0),  "baryon": False},
    5: {"name": "muon",       "mass": 0.11,   "charge": -1.0,  "radius": 0.08, "decay_prob": 0.006,  "color": (0.85, 0.15, 0.85), "baryon": False},
    6: {"name": "photon",     "mass": 0.001,  "charge":  0.0,  "radius": 0.04, "decay_prob": 0.0,    "color": (1.0,  1.0,  1.0),  "baryon": False},
    7: {"name": "heavy_x",    "mass": 5.0,    "charge":  2.0,  "radius": 0.28, "decay_prob": 0.015,  "color": (0.0,  1.0,  1.0),  "baryon": True},
    8: {"name": "neutron",    "mass": 1.0,    "charge":  0.0,  "radius": 0.15, "decay_prob": 0.0001, "color": (0.6,  0.6,  0.6),  "baryon": True},
    9: {"name": "positron",   "mass": 0.005,  "charge":  1.0,  "radius": 0.06, "decay_prob": 0.0,    "color": (0.3,  1.0,  0.9),  "baryon": False},
}

DECAY_CHANNELS = {
    2: [([1, 6], 1.0)],
    3: [([1, 6], 1.0)],
    4: [([2, 3], 0.6), ([5, 6], 0.4)],
    5: [([1, 6, 6], 1.0)],
    7: [([2, 3], 0.35), ([0, 1], 0.25), ([4, 5], 0.25), ([2, 3, 6], 0.15)],
    8: [([0, 1, 6], 1.0)],
}

# 0=scatter, 1=annihilate, 2=collision-induced decay
COLLISION_RULES = {
    (1, 9): 1,
    (7, 7): 2,
}
