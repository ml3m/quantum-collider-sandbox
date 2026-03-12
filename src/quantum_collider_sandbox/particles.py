"""Particle type data and Taichi field definitions for simulation."""

import taichi as ti

from .config import NUM_TYPES
from .pdg_table import COLLISION_RULES, LIFETIME_SCALE, MASS_SCALE, PARTICLES

MAX_DECAY_PRODUCTS = 4
MAX_CHANNELS = 8

type_mass = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_charge = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_radius = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_color = ti.Vector.field(3, dtype=ti.f32, shape=NUM_TYPES)
type_is_baryon = ti.field(dtype=ti.i32, shape=NUM_TYPES)
type_spin = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_lifetime = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_baryon_num = ti.field(dtype=ti.i32, shape=NUM_TYPES)
type_lepton_num = ti.field(dtype=ti.i32, shape=NUM_TYPES)
type_strangeness = ti.field(dtype=ti.i32, shape=NUM_TYPES)
type_antiparticle = ti.field(dtype=ti.i32, shape=NUM_TYPES)

num_channels = ti.field(dtype=ti.i32, shape=NUM_TYPES)
channel_num_products = ti.field(
    dtype=ti.i32, shape=(NUM_TYPES, MAX_CHANNELS)
)
channel_products = ti.field(
    dtype=ti.i32, shape=(NUM_TYPES, MAX_CHANNELS, MAX_DECAY_PRODUCTS)
)
channel_branch_cumulative = ti.field(
    dtype=ti.f32, shape=(NUM_TYPES, MAX_CHANNELS)
)

collision_rule_table = ti.field(dtype=ti.i32, shape=(NUM_TYPES, NUM_TYPES))


def load_particle_data() -> None:
    """Load PDG particle data into Taichi fields."""
    for tid, props in PARTICLES.items():
        type_mass[tid] = props["mass_mev"] * MASS_SCALE
        type_charge[tid] = float(props["charge_e"])
        type_radius[tid] = props["radius"]
        type_color[tid] = ti.Vector(props["color"])
        type_is_baryon[tid] = 1 if props["baryon_num"] != 0 else 0
        type_spin[tid] = props["spin"]

        lifetime = props["lifetime_s"]
        type_lifetime[tid] = lifetime / LIFETIME_SCALE if lifetime < 1e30 else 1e30

        type_baryon_num[tid] = props["baryon_num"]
        type_lepton_num[tid] = props["lepton_num"]
        type_strangeness[tid] = props["strangeness"]

        anti = props["anti_id"]
        type_antiparticle[tid] = anti if anti >= 0 else tid

        decays = props.get("decays", [])
        num_channels[tid] = min(len(decays), MAX_CHANNELS)
        cumulative = 0.0
        for ci, (ratio, products) in enumerate(decays):
            if ci >= MAX_CHANNELS:
                break
            n_prod = min(len(products), MAX_DECAY_PRODUCTS)
            channel_num_products[tid, ci] = n_prod
            for pi in range(n_prod):
                channel_products[tid, ci, pi] = products[pi]
            cumulative += ratio
            channel_branch_cumulative[tid, ci] = cumulative

    for t1 in range(NUM_TYPES):
        for t2 in range(NUM_TYPES):
            collision_rule_table[t1, t2] = 0

    for (t1, t2), rule_id in COLLISION_RULES.items():
        collision_rule_table[t1, t2] = rule_id
        collision_rule_table[t2, t1] = rule_id

    for tid, props in PARTICLES.items():
        anti = props["anti_id"]
        if (
            anti >= 0
            and anti != tid
            and collision_rule_table[tid, anti] == 0
        ):
            if props["baryon_num"] != 0:
                collision_rule_table[tid, anti] = 2
                collision_rule_table[anti, tid] = 2
            elif props["lepton_num"] != 0:
                collision_rule_table[tid, anti] = 1
                collision_rule_table[anti, tid] = 1


def get_type_name(tid: int) -> str:
    """Return particle type name by ID."""
    particle = PARTICLES.get(tid)
    return particle["name"] if particle else f"type_{tid}"


def get_type_id_by_name(name: str) -> int:
    """Return particle type ID by name, or -1 if not found."""
    for particle_tid, props in PARTICLES.items():
        if props["name"] == name:
            return particle_tid
    return -1
