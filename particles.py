import taichi as ti
from config import PARTICLE_TYPES, DECAY_CHANNELS

NUM_TYPES = len(PARTICLE_TYPES)
MAX_DECAY_PRODUCTS = 3
MAX_CHANNELS = 4

type_mass = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_charge = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_radius = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_decay_prob = ti.field(dtype=ti.f32, shape=NUM_TYPES)
type_color = ti.Vector.field(3, dtype=ti.f32, shape=NUM_TYPES)

num_channels = ti.field(dtype=ti.i32, shape=NUM_TYPES)
channel_num_products = ti.field(dtype=ti.i32, shape=(NUM_TYPES, MAX_CHANNELS))
channel_products = ti.field(dtype=ti.i32, shape=(NUM_TYPES, MAX_CHANNELS, MAX_DECAY_PRODUCTS))
channel_branch_cumulative = ti.field(dtype=ti.f32, shape=(NUM_TYPES, MAX_CHANNELS))


def load_particle_data():
    for tid, props in PARTICLE_TYPES.items():
        type_mass[tid] = props["mass"]
        type_charge[tid] = props["charge"]
        type_radius[tid] = props["radius"]
        type_decay_prob[tid] = props["decay_prob"]
        type_color[tid] = ti.Vector(props["color"])

    for tid in range(NUM_TYPES):
        if tid in DECAY_CHANNELS:
            channels = DECAY_CHANNELS[tid]
            num_channels[tid] = min(len(channels), MAX_CHANNELS)
            cumulative = 0.0
            for ci, (products, ratio) in enumerate(channels):
                if ci >= MAX_CHANNELS:
                    break
                channel_num_products[tid, ci] = min(len(products), MAX_DECAY_PRODUCTS)
                for pi, prod in enumerate(products):
                    if pi < MAX_DECAY_PRODUCTS:
                        channel_products[tid, ci, pi] = prod
                cumulative += ratio
                channel_branch_cumulative[tid, ci] = cumulative
        else:
            num_channels[tid] = 0


def get_type_name(tid: int) -> str:
    return PARTICLE_TYPES.get(tid, {}).get("name", f"type_{tid}")


def get_type_id_by_name(name: str) -> int:
    for tid, props in PARTICLE_TYPES.items():
        if props["name"] == name:
            return tid
    return -1
