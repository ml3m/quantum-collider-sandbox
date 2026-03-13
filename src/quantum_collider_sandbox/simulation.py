# pylint: disable=C0302 disable=C0103
"""Taichi-based GPU physics simulation: forces, collisions, decays, black hole."""

import h5py
import numpy as np
import taichi as ti

from . import config as _config
from .config import (
    COLLISION_RESTITUTION,
    CUTOFF_RADIUS,
    FLASH_OPACITY,
    MAX_PARTICLES,
    MAX_VELOCITY,
    MIN_VELOCITY,
    NUM_TYPES,
    SOFTENING,
    TRAIL_LENGTH,
)
from .particles import (
    channel_branch_cumulative,
    channel_num_products,
    channel_products,
    collision_rule_table,
    num_channels,
    type_charge,
    type_color,
    type_is_baryon,
    type_lifetime,
    type_mass,
    type_radius,
)
from .pdg_table import PHOTON

MAX_FLASHES = 256
INV_MASS_BUF = 64

# ── stats array layout ───────────────────────────────────────────────────
# 0:ke 1-3:mom 4:collisions 5:decays 6:step 7:n_active
# 8..(8+NUM_TYPES-1): per-type counts
_S_ANN = 8 + NUM_TYPES  # 56
_S_PAIR = _S_ANN + 1  # 57
_S_DHIT = _S_PAIR + 1  # 58
_S_DENE = _S_DHIT + 1  # 59
_S_ASPD = _S_DENE + 1  # 60
_S_BHC = _S_ASPD + 1  # 61
_S_SEL = _S_BHC + 1  # 62  (12 slots: px py pz vx vy vz m q type ke frozen speed)
NUM_STATS = _S_SEL + 12  # 74

pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
vel = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
force = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
mass = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
charge = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
radius = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
ptype = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
alive = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
frozen = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

trail_pos = ti.Vector.field(3, dtype=ti.f32, shape=(MAX_PARTICLES, TRAIL_LENGTH))
trail_head = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
trail_count = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

num_active = ti.field(dtype=ti.i32, shape=())

stats = ti.field(dtype=ti.f32, shape=NUM_STATS)

collision_count_acc = ti.field(dtype=ti.i32, shape=())
decay_count_acc = ti.field(dtype=ti.i32, shape=())
annihilation_count_acc = ti.field(dtype=ti.i32, shape=())
pair_creation_count_acc = ti.field(dtype=ti.i32, shape=())
detector_hits_acc = ti.field(dtype=ti.i32, shape=())
detector_energy_acc = ti.field(dtype=ti.f32, shape=())
bh_captures_acc = ti.field(dtype=ti.i32, shape=())
step_counter = ti.field(dtype=ti.i32, shape=())

BH_RING_N = 128
bh_ring_pos = ti.Vector.field(3, dtype=ti.f32, shape=BH_RING_N)
bh_ring_color = ti.Vector.field(3, dtype=ti.f32, shape=BH_RING_N)
bh_eh_pos = ti.Vector.field(3, dtype=ti.f32, shape=1)
bh_eh_color = ti.Vector.field(3, dtype=ti.f32, shape=1)

BH_SHADOW_FACTOR = 2.598

NUM_BG_STARS = 800
star_pos = ti.Vector.field(3, dtype=ti.f32, shape=NUM_BG_STARS)
star_color = ti.Vector.field(3, dtype=ti.f32, shape=NUM_BG_STARS)

DISK_N = 400
disk_pos = ti.Vector.field(3, dtype=ti.f32, shape=DISK_N)
disk_vel = ti.Vector.field(3, dtype=ti.f32, shape=DISK_N)
disk_color = ti.Vector.field(3, dtype=ti.f32, shape=DISK_N)

inv_mass_buffer = ti.field(dtype=ti.f32, shape=INV_MASS_BUF)
inv_mass_head = ti.field(dtype=ti.i32, shape=())

render_pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
render_color = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
render_count = ti.field(dtype=ti.i32, shape=())

trail_vertices = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES * TRAIL_LENGTH * 2)
trail_colors = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES * TRAIL_LENGTH * 2)
trail_line_count = ti.field(dtype=ti.i32, shape=())

spawn_queue_pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
spawn_queue_vel = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
spawn_queue_type = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
spawn_count = ti.field(dtype=ti.i32, shape=())

flash_render_pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_FLASHES)
flash_render_color = ti.Vector.field(4, dtype=ti.f32, shape=MAX_FLASHES)  # RGBA for transparency
flash_life = ti.field(dtype=ti.f32, shape=MAX_FLASHES)
flash_count = ti.field(dtype=ti.i32, shape=())
flash_render_count = ti.field(dtype=ti.i32, shape=())

_compact_src = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
_compact_count = ti.field(dtype=ti.i32, shape=())
_needs_compact = ti.field(dtype=ti.i32, shape=())

cached_stats = {}
time_series = {
    "step": [],
    "ke": [],
    "particles": [],
    "collisions": [],
    "decays": [],
    "annihilations": [],
    "pair_creations": [],
    "momentum": [],
}


def _reset_cached() -> None:
    """Reset cached statistics to zero."""
    keys = [
        "ke",
        "mom",
        "mom_x",
        "mom_y",
        "mom_z",
        "collisions",
        "decays",
        "step",
        "particles",
        "annihilations",
        "pair_creations",
        "detector_hits",
        "detector_energy",
        "avg_speed",
        "total_pe",
        "flash_rc",
        "bh_captures",
        "sel_px",
        "sel_py",
        "sel_pz",
        "sel_vx",
        "sel_vy",
        "sel_vz",
        "sel_mass",
        "sel_charge",
        "sel_type",
        "sel_ke",
        "sel_frozen",
        "sel_speed",
    ]
    for k in keys:
        cached_stats[k] = 0.0
    for i in range(NUM_TYPES):
        cached_stats[f"type_{i}"] = 0
    cached_stats["inv_masses"] = []


@ti.kernel
def _clear_all():
    num_active[None] = 0
    spawn_count[None] = 0
    collision_count_acc[None] = 0
    decay_count_acc[None] = 0
    annihilation_count_acc[None] = 0
    pair_creation_count_acc[None] = 0
    detector_hits_acc[None] = 0
    detector_energy_acc[None] = 0.0
    bh_captures_acc[None] = 0
    step_counter[None] = 0
    flash_count[None] = 0
    flash_render_count[None] = 0
    trail_line_count[None] = 0
    inv_mass_head[None] = 0
    for i in range(NUM_STATS):
        stats[i] = 0.0
    for i in range(MAX_PARTICLES):
        alive[i] = 0
        frozen[i] = 0
        trail_head[i] = 0
        trail_count[i] = 0
        for t in range(TRAIL_LENGTH):
            trail_pos[i, t] = ti.Vector([0.0, 0.0, 0.0])
    for i in range(MAX_PARTICLES * TRAIL_LENGTH * 2):
        trail_vertices[i] = ti.Vector([0.0, 0.0, 0.0])
        trail_colors[i] = ti.Vector([0.0, 0.0, 0.0])
    for i in range(INV_MASS_BUF):
        inv_mass_buffer[i] = 0.0


def init_simulation() -> None:
    """Initialize or reset the simulation state."""
    _clear_all()
    _reset_cached()
    for key in time_series:
        time_series[key].clear()


def add_particle(position, velocity, particle_type, is_frozen=False):  # noqa: PLR0913
    """Add a particle to the simulation. Returns index or -1 if full."""
    n = num_active[None]
    if n >= MAX_PARTICLES:
        return -1
    idx = n
    pos[idx] = ti.Vector(position)
    vel[idx] = ti.Vector(velocity)
    force[idx] = ti.Vector([0.0, 0.0, 0.0])
    ptype[idx] = particle_type
    mass[idx] = float(type_mass[particle_type])
    charge[idx] = float(type_charge[particle_type])
    radius[idx] = float(type_radius[particle_type])
    alive[idx] = 1
    frozen[idx] = 1 if is_frozen else 0
    trail_head[idx] = 0
    trail_count[idx] = 0
    num_active[None] = n + 1
    return idx


@ti.kernel
def compute_forces(
    coulomb_k: ti.f32,
    gravity_g: ti.f32,
    bx: ti.f32,
    by: ti.f32,
    bz: ti.f32,
    ex: ti.f32,
    ey: ti.f32,
    ez: ti.f32,
    strong_k: ti.f32,
    strong_range: ti.f32,
    bh_on: ti.i32,
    bh_gm: ti.f32,
    bh_rs: ti.f32,
    bhx: ti.f32,
    bhy: ti.f32,
    bhz: ti.f32,
):
    n = num_active[None]
    mag_field = ti.Vector([bx, by, bz])
    e_field = ti.Vector([ex, ey, ez])
    bh_p = ti.Vector([bhx, bhy, bhz])
    has_mag = mag_field.norm() > 1e-8
    has_e = e_field.norm() > 1e-8
    for i in range(n):
        if alive[i] == 0:
            continue
        f = ti.Vector([0.0, 0.0, 0.0])
        qi = charge[i]
        mi = mass[i]
        pi = pos[i]
        for j in range(n):
            if i == j or alive[j] == 0:
                continue
            diff = pos[j] - pi
            dist_sq = diff.dot(diff) + SOFTENING * SOFTENING
            dist = ti.sqrt(dist_sq)
            if dist > CUTOFF_RADIUS:
                continue
            direction = diff / dist
            if coulomb_k != 0.0:
                f -= coulomb_k * qi * charge[j] / dist_sq * direction
            if gravity_g > 0.0:
                f += gravity_g * mi * mass[j] / dist_sq * direction
            if strong_k > 0.0 and dist < strong_range:
                bi = type_is_baryon[ptype[i]]
                bj = type_is_baryon[ptype[j]]
                if bi == 1 and bj == 1:
                    yukawa = -strong_k * ti.exp(-dist / (strong_range * 0.3)) / (dist + 0.01)
                    f += yukawa * direction

        if has_e:
            f += qi * e_field
        if has_mag:
            f += qi * vel[i].cross(mag_field)

        if bh_on == 1:
            diff_bh = bh_p - pi
            r_bh = diff_bh.norm()
            if r_bh > bh_rs * 1.01:
                r_eff = r_bh - bh_rs
                f_bh_mag = bh_gm * mi / (r_eff * r_eff)
                f += f_bh_mag * (diff_bh / r_bh)

        force[i] = f


@ti.kernel
def _integrate_step(
    dt_kick: ti.f32,
    dt_drift: ti.f32,
    use_rel: ti.i32,
    c_light: ti.f32,
    synchro: ti.f32,
    bh_on: ti.i32,
    bh_rs: ti.f32,
    bhx: ti.f32,
    bhy: ti.f32,
    bhz: ti.f32,
):
    """Kick (v += dt_kick*a) and optionally drift (x += v*dt_drift)."""
    n = num_active[None]
    bh_p = ti.Vector([bhx, bhy, bhz])
    for i in range(n):
        if alive[i] == 0 or frozen[i] == 1:
            continue
        m = mass[i]
        effective_m = m
        if use_rel == 1 and c_light > 0.0:
            speed_sq = vel[i].norm_sqr()
            beta_sq = speed_sq / (c_light * c_light)
            gamma = 1.0 / ti.sqrt(1.0 - ti.min(beta_sq, 0.99))
            effective_m = m * gamma

        acc = force[i] / effective_m

        if synchro > 0.0 and charge[i] != 0.0:
            acc_sq = acc.norm_sqr()
            q_sq = charge[i] * charge[i]
            power = synchro * q_sq * acc_sq
            spd = vel[i].norm()
            if spd > 0.1:
                damp = power * dt_kick / (effective_m * spd * spd)
                vel[i] *= ti.max(1.0 - damp, 0.5)

        vel[i] += acc * dt_kick
        speed = vel[i].norm()
        if speed > MAX_VELOCITY:
            vel[i] *= MAX_VELOCITY / speed

        if dt_drift > 0.0:
            pos[i] += vel[i] * dt_drift

        if bh_on == 1:
            r_bh = (pos[i] - bh_p).norm()
            if r_bh < bh_rs:
                alive[i] = 0
                ti.atomic_add(bh_captures_acc[None], 1)


@ti.kernel
def apply_boundaries_reflect(bound: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0 or frozen[i] == 1:
            continue
        for d in ti.static(range(3)):
            if pos[i][d] > bound:
                pos[i][d] = bound
                vel[i][d] = -vel[i][d] * 0.9
                ke = 0.5 * mass[i] * vel[i].norm_sqr()
                ti.atomic_add(detector_hits_acc[None], 1)
                ti.atomic_add(detector_energy_acc[None], ke)
            elif pos[i][d] < -bound:
                pos[i][d] = -bound
                vel[i][d] = -vel[i][d] * 0.9
                ke = 0.5 * mass[i] * vel[i].norm_sqr()
                ti.atomic_add(detector_hits_acc[None], 1)
                ti.atomic_add(detector_energy_acc[None], ke)
        # Prevent zero-velocity trap: boundary restitution can decay v to 0
        speed = vel[i].norm()
        if speed > 0.0 and speed < MIN_VELOCITY:
            vel[i] = vel[i] * (MIN_VELOCITY / speed)


@ti.kernel
def apply_boundaries_periodic(bound: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0 or frozen[i] == 1:
            continue
        for d in ti.static(range(3)):
            if pos[i][d] > bound:
                pos[i][d] -= 2.0 * bound
            elif pos[i][d] < -bound:
                pos[i][d] += 2.0 * bound


# ── Relativistic kinematics helpers ───────────────────────────────────────


@ti.func
def _boost_to_lab(
    E_star: ti.f32, p_star_vec: ti.template(), parent_vel: ti.template(), c_light: ti.f32
) -> ti.template():
    """Lorentz boost from parent rest frame to lab frame, returns velocity."""
    v_sq = parent_vel.norm_sqr()
    c_sq = c_light * c_light
    result = ti.Vector([0.0, 0.0, 0.0])

    if v_sq < 1e-12 * c_sq:
        if E_star > 1e-30:
            result = p_star_vec / E_star * c_light
        else:
            result = p_star_vec * c_light
    else:
        beta = ti.sqrt(v_sq) / c_light
        gamma = 1.0 / ti.sqrt(ti.max(1.0 - beta * beta, 0.01))
        V_hat = parent_vel / ti.sqrt(v_sq)

        p_par = p_star_vec.dot(V_hat)
        p_perp = p_star_vec - p_par * V_hat

        p_lab_par = gamma * (p_par + beta * E_star)
        E_lab = gamma * (E_star + beta * p_par)

        if E_lab > 1e-30:
            result = (p_perp + p_lab_par * V_hat) / E_lab * c_light
        else:
            result = (p_perp + p_lab_par * V_hat) * c_light

    speed = result.norm()
    if speed > c_light * 0.999:
        result = result * (c_light * 0.999 / speed)
    return result


@ti.func
def _random_dir() -> ti.template():
    theta = ti.random(ti.f32) * 6.28318
    cos_phi = 2.0 * ti.random(ti.f32) - 1.0
    sin_phi = ti.sqrt(ti.max(1.0 - cos_phi * cos_phi, 0.0))
    return ti.Vector([sin_phi * ti.cos(theta), sin_phi * ti.sin(theta), cos_phi])


@ti.func
def cm_decay_2body(M: ti.f32, m1: ti.f32, m2: ti.f32, parent_vel: ti.template(), c_light: ti.f32):
    """2-body decay M -> m1 + m2 with proper CM kinematics + Lorentz boost.
    All masses in sim units. Returns (v1_lab, v2_lab)."""
    sum_m = m1 + m2
    diff_m = m1 - m2
    arg = (M * M - sum_m * sum_m) * (M * M - diff_m * diff_m)
    p_star = ti.sqrt(ti.max(arg, 0.0)) / (2.0 * M + 1e-30)
    E1_star = ti.sqrt(p_star * p_star + m1 * m1)
    E2_star = ti.sqrt(p_star * p_star + m2 * m2)

    d = _random_dir()
    p1_cm = d * p_star
    p2_cm = -d * p_star

    v1 = _boost_to_lab(E1_star, p1_cm, parent_vel, c_light)
    v2 = _boost_to_lab(E2_star, p2_cm, parent_vel, c_light)
    return v1, v2


@ti.func
def cm_decay_3body(
    M: ti.f32, m1: ti.f32, m2: ti.f32, m3: ti.f32, parent_vel: ti.template(), c_light: ti.f32
):
    """3-body decay via recursive 2-body: M -> d1 + virtual(m23), virtual -> d2 + d3.
    Invariant mass m23 sampled from phase space."""
    m23_min = m2 + m3 + 1e-6
    m23_max = M - m1 - 1e-6
    m23 = m23_min + ti.random(ti.f32) * ti.max(m23_max - m23_min, 1e-6)

    v1, v23 = cm_decay_2body(M, m1, m23, parent_vel, c_light)
    v2, v3 = cm_decay_2body(m23, m2, m3, v23, c_light)
    return v1, v2, v3


@ti.func
def cm_decay_4body(
    M: ti.f32,
    m1: ti.f32,
    m2: ti.f32,
    m3: ti.f32,
    m4: ti.f32,
    parent_vel: ti.template(),
    c_light: ti.f32,
):
    """4-body decay via recursive 2-body: M -> (m1+m2) + (m3+m4), each 2-body."""
    m12_min = m1 + m2 + 1e-6
    m12_max = M - m3 - m4 - 1e-6
    m12 = m12_min + ti.random(ti.f32) * ti.max(m12_max - m12_min, 1e-6)
    m34 = M - m12

    v12, v34 = cm_decay_2body(M, m12, m34, parent_vel, c_light)
    v1, v2 = cm_decay_2body(m12, m1, m2, v12, c_light)
    v3, v4 = cm_decay_2body(m34, m3, m4, v34, c_light)
    return v1, v2, v3, v4


@ti.func
def cm_decay_5body(
    M: ti.f32,
    m1: ti.f32,
    m2: ti.f32,
    m3: ti.f32,
    m4: ti.f32,
    m5: ti.f32,
    parent_vel: ti.template(),
    c_light: ti.f32,
):
    """5-body decay via recursive 2-body + 3-body: M -> (m1+m2) + (m3+m4+m5)."""
    m12_min = m1 + m2 + 1e-6
    m12_max = M - m3 - m4 - m5 - 1e-6
    m12 = m12_min + ti.random(ti.f32) * ti.max(m12_max - m12_min, 1e-6)
    m345 = M - m12

    v12, v345 = cm_decay_2body(M, m12, m345, parent_vel, c_light)
    v1, v2 = cm_decay_2body(m12, m1, m2, v12, c_light)
    v3, v4, v5 = cm_decay_3body(m345, m3, m4, m5, v345, c_light)
    return v1, v2, v3, v4, v5


# ── Collision detection ───────────────────────────────────────────────────


@ti.kernel
def detect_collisions(pair_threshold: ti.f32, c_light: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        for j in range(i + 1, n):
            if alive[i] == 0:
                break
            if alive[j] == 0:
                continue
            diff = pos[j] - pos[i]
            dist = diff.norm()
            min_dist = (radius[i] + radius[j]) * 1.5
            if dist < min_dist:
                t1 = ptype[i]
                t2 = ptype[j]
                if t1 == PHOTON or t2 == PHOTON:  # pylint: disable=consider-using-in
                    continue
                # Use safe normal when dist nearly zero (avoids div-by-tiny, stuck overlap)
                overlap = min_dist - dist if dist > 1e-8 else min_dist
                normal = (diff / dist) if dist > 1e-8 else _random_dir()
                rule = collision_rule_table[t1, t2]

                if rule == 1:
                    # Lepton-antilepton annihilation -> 2 photons (momentum-conserving)
                    alive[i] = 0
                    alive[j] = 0
                    ti.atomic_add(annihilation_count_acc[None], 1)
                    center = (pos[i] + pos[j]) * 0.5
                    mom = mass[i] * vel[i] + mass[j] * vel[j]
                    parent_vel_c = mom / (mass[i] + mass[j])
                    inv_m = mass[i] + mass[j]
                    v1_ph, v2_ph = cm_decay_2body(inv_m, 0.0, 0.0, parent_vel_c, c_light)
                    d1 = v1_ph.normalized() if v1_ph.norm() > 1e-8 else _random_dir()
                    offset = 0.15
                    s1 = ti.atomic_add(spawn_count[None], 1)
                    if s1 < MAX_PARTICLES:
                        spawn_queue_pos[s1] = center + d1 * offset
                        spawn_queue_vel[s1] = v1_ph
                        spawn_queue_type[s1] = 12  # PHOTON
                    s2 = ti.atomic_add(spawn_count[None], 1)
                    if s2 < MAX_PARTICLES:
                        spawn_queue_pos[s2] = center - d1 * offset
                        spawn_queue_vel[s2] = v2_ph
                        spawn_queue_type[s2] = 12  # PHOTON
                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = center
                        flash_render_color[fidx] = ti.Vector([0.9, 0.9, 0.3, FLASH_OPACITY])
                        flash_life[fidx] = 1.0

                elif rule == 2:
                    # Baryon-antibaryon annihilation -> 5 pions (momentum-conserving)
                    alive[i] = 0
                    alive[j] = 0
                    ti.atomic_add(annihilation_count_acc[None], 1)
                    center = (pos[i] + pos[j]) * 0.5
                    parent_vel_c = (mass[i] * vel[i] + mass[j] * vel[j]) / (mass[i] + mass[j])
                    inv_m = mass[i] + mass[j]
                    idx_im = ti.atomic_add(inv_mass_head[None], 1) % INV_MASS_BUF
                    inv_mass_buffer[idx_im] = inv_m
                    pt1 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt1 = 18
                    elif rp < 0.66:
                        pt1 = 19
                    pt2 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt2 = 18
                    elif rp < 0.66:
                        pt2 = 19
                    pt3 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt3 = 18
                    elif rp < 0.66:
                        pt3 = 19
                    pt4 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt4 = 18
                    elif rp < 0.66:
                        pt4 = 19
                    pt5 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt5 = 18
                    elif rp < 0.66:
                        pt5 = 19
                    m1 = type_mass[pt1]
                    m2 = type_mass[pt2]
                    m3 = type_mass[pt3]
                    m4 = type_mass[pt4]
                    m5 = type_mass[pt5]
                    v1, v2, v3, v4, v5 = cm_decay_5body(
                        inv_m, m1, m2, m3, m4, m5, parent_vel_c, c_light
                    )
                    rd1 = _random_dir()
                    rd2 = _random_dir()
                    rd3 = _random_dir()
                    rd4 = _random_dir()
                    rd5 = _random_dir()
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd1 * 0.2
                        spawn_queue_vel[s] = v1
                        spawn_queue_type[s] = pt1
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd2 * 0.2
                        spawn_queue_vel[s] = v2
                        spawn_queue_type[s] = pt2
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd3 * 0.2
                        spawn_queue_vel[s] = v3
                        spawn_queue_type[s] = pt3
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd4 * 0.2
                        spawn_queue_vel[s] = v4
                        spawn_queue_type[s] = pt4
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd5 * 0.2
                        spawn_queue_vel[s] = v5
                        spawn_queue_type[s] = pt5
                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = center
                        flash_render_color[fidx] = ti.Vector([0.3, 0.8, 0.8, FLASH_OPACITY])
                        flash_life[fidx] = 1.2

                elif rule == 3:
                    # Collision-induced decay -> 4 light mesons (momentum-conserving)
                    alive[i] = 0
                    alive[j] = 0
                    ti.atomic_add(collision_count_acc[None], 1)
                    center = (pos[i] + pos[j]) * 0.5
                    parent_vel_c = (mass[i] * vel[i] + mass[j] * vel[j]) / (mass[i] + mass[j])
                    inv_m = mass[i] + mass[j]
                    idx_im = ti.atomic_add(inv_mass_head[None], 1) % INV_MASS_BUF
                    inv_mass_buffer[idx_im] = inv_m
                    pt1 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt1 = 18
                    elif rp < 0.66:
                        pt1 = 19
                    pt2 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt2 = 18
                    elif rp < 0.66:
                        pt2 = 19
                    pt3 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt3 = 18
                    elif rp < 0.66:
                        pt3 = 19
                    pt4 = 20
                    rp = ti.random(ti.f32)
                    if rp < 0.33:
                        pt4 = 18
                    elif rp < 0.66:
                        pt4 = 19
                    m1, m2, m3, m4 = type_mass[pt1], type_mass[pt2], type_mass[pt3], type_mass[pt4]
                    v1, v2, v3, v4 = cm_decay_4body(inv_m, m1, m2, m3, m4, parent_vel_c, c_light)
                    rd1 = _random_dir()
                    rd2 = _random_dir()
                    rd3 = _random_dir()
                    rd4 = _random_dir()
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd1 * 0.2
                        spawn_queue_vel[s] = v1
                        spawn_queue_type[s] = pt1
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd2 * 0.2
                        spawn_queue_vel[s] = v2
                        spawn_queue_type[s] = pt2
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd3 * 0.2
                        spawn_queue_vel[s] = v3
                        spawn_queue_type[s] = pt3
                    s = ti.atomic_add(spawn_count[None], 1)
                    if s < MAX_PARTICLES:
                        spawn_queue_pos[s] = center + rd4 * 0.2
                        spawn_queue_vel[s] = v4
                        spawn_queue_type[s] = pt4
                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = center
                        flash_render_color[fidx] = ti.Vector([0.3, 0.8, 0.8, FLASH_OPACITY])
                        flash_life[fidx] = 1.2

                else:
                    # Elastic scatter
                    if frozen[i] == 0:
                        pos[i] -= 0.5 * overlap * normal
                    if frozen[j] == 0:
                        pos[j] += 0.5 * overlap * normal

                    rel_vel = vel[i] - vel[j]
                    vel_along_normal = rel_vel.dot(normal)

                    if vel_along_normal > 0:
                        total_mass = mass[i] + mass[j]
                        restitution = ti.cast(COLLISION_RESTITUTION, ti.f32)
                        impulse = (1.0 + restitution) * vel_along_normal / total_mass
                        if frozen[i] == 0:
                            vel[i] -= impulse * mass[j] * normal
                        if frozen[j] == 0:
                            vel[j] += impulse * mass[i] * normal
                        ti.atomic_add(collision_count_acc[None], 1)

                        ke_i = 0.5 * mass[i] * vel[i].norm_sqr()
                        ke_j = 0.5 * mass[j] * vel[j].norm_sqr()
                        combined_ke = ke_i + ke_j
                        if combined_ke > pair_threshold and ti.random(ti.f32) < 0.08:
                            c = (pos[i] + pos[j]) * 0.5
                            rd = _random_dir()
                            creation_cost = type_mass[0] + type_mass[1]  # e- + e+ rest mass
                            if combined_ke > creation_cost * 2.0:
                                ke_remain = combined_ke - creation_cost
                                m_e = type_mass[0]
                                speed = ti.sqrt(ti.max(ke_remain / (m_e + 1e-30), 0.0))
                                speed = ti.min(speed, c_light * 0.999)
                                s1 = ti.atomic_add(spawn_count[None], 1)
                                if s1 < MAX_PARTICLES:
                                    spawn_queue_pos[s1] = c + rd * 0.15
                                    spawn_queue_vel[s1] = rd * speed
                                    spawn_queue_type[s1] = 0  # electron
                                s2 = ti.atomic_add(spawn_count[None], 1)
                                if s2 < MAX_PARTICLES:
                                    spawn_queue_pos[s2] = c - rd * 0.15
                                    spawn_queue_vel[s2] = -rd * speed
                                    spawn_queue_type[s2] = 1  # positron
                                ti.atomic_add(pair_creation_count_acc[None], 1)
                                ratio = creation_cost / (combined_ke + 1e-8)
                                factor = ti.sqrt(ti.max(1.0 - ratio, 0.1))
                                if frozen[i] == 0:
                                    vel[i] *= factor
                                if frozen[j] == 0:
                                    vel[j] *= factor
                                fidx = ti.atomic_add(flash_count[None], 1)
                                if fidx < MAX_FLASHES:
                                    flash_render_pos[fidx] = c
                                    flash_render_color[fidx] = ti.Vector(
                                        [0.5, 0.3, 0.7, FLASH_OPACITY]
                                    )
                                    flash_life[fidx] = 0.8

                    fidx2 = ti.atomic_add(flash_count[None], 1)
                    if fidx2 < MAX_FLASHES:
                        flash_render_pos[fidx2] = (pos[i] + pos[j]) * 0.5
                        c1 = type_color[t1]
                        c2 = type_color[t2]
                        flash_render_color[fidx2] = ti.Vector(
                            [
                                (c1[0] + c2[0]) * 0.25,
                                (c1[1] + c2[1]) * 0.25,
                                (c1[2] + c2[2]) * 0.25,
                                FLASH_OPACITY,
                            ]
                        )
                        flash_life[fidx2] = 0.6


# ── Monte Carlo decay with proper exponential law + relativistic kinematics ──


@ti.kernel
def monte_carlo_decay(
    dt: ti.f32,
    use_rel: ti.i32,
    c_light: ti.f32,
    bh_on: ti.i32,
    bh_rs: ti.f32,
    bhx: ti.f32,
    bhy: ti.f32,
    bhz: ti.f32,
):
    n = num_active[None]
    bh_p = ti.Vector([bhx, bhy, bhz])
    for i in range(n):
        if alive[i] == 0 or frozen[i] == 1:
            continue
        pt = ptype[i]
        nc = num_channels[pt]
        if nc == 0:
            continue

        tau = type_lifetime[pt]
        if tau <= 0.0 or tau >= 1e28:
            continue

        # Lorentz factor for SR time dilation
        gamma = 1.0
        if use_rel == 1 and c_light > 0.0:
            speed_sq = vel[i].norm_sqr()
            beta_sq = speed_sq / (c_light * c_light)
            gamma = 1.0 / ti.sqrt(1.0 - ti.min(beta_sq, 0.99))

        dt_proper = dt / gamma

        # Gravitational time dilation near BH
        if bh_on == 1:
            r_bh = (pos[i] - bh_p).norm()
            if r_bh > bh_rs:
                grav_factor = ti.sqrt(ti.max(1.0 - bh_rs / r_bh, 0.01))
                dt_proper *= grav_factor

        # P(decay in dt) = 1 - exp(-dt_proper / tau)
        p_decay = 1.0 - ti.exp(-dt_proper / tau)

        if ti.random(ti.f32) < p_decay:
            r = ti.random(ti.f32)
            selected_channel = 0
            for c in range(nc):
                if r <= channel_branch_cumulative[pt, c]:
                    selected_channel = c
                    break

            n_products = channel_num_products[pt, selected_channel]
            parent_pos = pos[i]
            parent_vel_v = vel[i]
            parent_m = mass[i]

            alive[i] = 0
            ti.atomic_add(decay_count_acc[None], 1)

            idx_im = ti.atomic_add(inv_mass_head[None], 1) % INV_MASS_BUF
            inv_mass_buffer[idx_im] = parent_m

            fidx = ti.atomic_add(flash_count[None], 1)
            if fidx < MAX_FLASHES:
                flash_render_pos[fidx] = parent_pos
                flash_render_color[fidx] = ti.Vector(
                    [
                        type_color[pt][0] * 0.35,
                        type_color[pt][1] * 0.35,
                        type_color[pt][2] * 0.35,
                        FLASH_OPACITY,
                    ]
                )
                flash_life[fidx] = 0.8

            pt0 = channel_products[pt, selected_channel, 0]
            m0 = type_mass[pt0]

            if n_products == 1:
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos
                    spawn_queue_vel[idx] = parent_vel_v
                    spawn_queue_type[idx] = pt0

            elif n_products == 2:
                pt1 = channel_products[pt, selected_channel, 1]
                m1 = type_mass[pt1]
                va, vb = cm_decay_2body(parent_m, m0, m1, parent_vel_v, c_light)
                offset_a = va.normalized() * 0.05 if va.norm() > 1e-8 else _random_dir() * 0.05
                offset_b = vb.normalized() * 0.05 if vb.norm() > 1e-8 else _random_dir() * 0.05
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + offset_a
                    spawn_queue_vel[idx] = va
                    spawn_queue_type[idx] = pt0
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + offset_b
                    spawn_queue_vel[idx] = vb
                    spawn_queue_type[idx] = pt1

            elif n_products == 3:
                pt1 = channel_products[pt, selected_channel, 1]
                pt2 = channel_products[pt, selected_channel, 2]
                m1 = type_mass[pt1]
                m2 = type_mass[pt2]
                va, vb, vc = cm_decay_3body(parent_m, m0, m1, m2, parent_vel_v, c_light)
                offset_a = va.normalized() * 0.05 if va.norm() > 1e-8 else _random_dir() * 0.05
                offset_b = vb.normalized() * 0.05 if vb.norm() > 1e-8 else _random_dir() * 0.05
                offset_c = vc.normalized() * 0.05 if vc.norm() > 1e-8 else _random_dir() * 0.05
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + offset_a
                    spawn_queue_vel[idx] = va
                    spawn_queue_type[idx] = pt0
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + offset_b
                    spawn_queue_vel[idx] = vb
                    spawn_queue_type[idx] = pt1
                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + offset_c
                    spawn_queue_vel[idx] = vc
                    spawn_queue_type[idx] = pt2

            else:
                # 4-body: M -> (01) + (23) via recursive 2-body
                pt1 = channel_products[pt, selected_channel, 1]
                pt2 = channel_products[pt, selected_channel, 2]
                pt3 = channel_products[pt, selected_channel, 3]
                m1 = type_mass[pt1]
                m2 = type_mass[pt2]
                m3 = type_mass[pt3]

                Q = parent_m - m0 - m1 - m2 - m3
                frac = ti.random(ti.f32)
                m_v1 = m0 + m1 + frac * Q * 0.45
                m_v2 = m2 + m3 + (1.0 - frac) * Q * 0.45

                v_v1, v_v2 = cm_decay_2body(parent_m, m_v1, m_v2, parent_vel_v, c_light)
                va, vb = cm_decay_2body(m_v1, m0, m1, v_v1, c_light)
                vc, vd = cm_decay_2body(m_v2, m2, m3, v_v2, c_light)

                products_4 = ti.Vector([pt0, pt1, pt2, pt3])
                offset_va = va.normalized() * 0.05 if va.norm() > 1e-8 else _random_dir() * 0.05
                offset_vb = vb.normalized() * 0.05 if vb.norm() > 1e-8 else _random_dir() * 0.05
                offset_vc = vc.normalized() * 0.05 if vc.norm() > 1e-8 else _random_dir() * 0.05
                offset_vd = vd.normalized() * 0.05 if vd.norm() > 1e-8 else _random_dir() * 0.05
                for pi in ti.static(range(4)):
                    v_out = va
                    pos_offset = offset_va
                    if pi == 1:
                        v_out = vb
                        pos_offset = offset_vb
                    elif pi == 2:
                        v_out = vc
                        pos_offset = offset_vc
                    elif pi == 3:
                        v_out = vd
                        pos_offset = offset_vd
                    idx = ti.atomic_add(spawn_count[None], 1)
                    if idx < MAX_PARTICLES:
                        spawn_queue_pos[idx] = parent_pos + pos_offset
                        spawn_queue_vel[idx] = v_out
                        spawn_queue_type[idx] = products_4[pi]


# ── Spawn / compact ──────────────────────────────────────────────────────


@ti.kernel
def _apply_spawn_queue():
    """Apply spawn queue: collision/decay products. All spawns get frozen=0 (never frozen).
    Must run before Leapfrog second half so new particles receive forces + half-kick."""
    sc = spawn_count[None]
    n = num_active[None]
    for i in range(sc):
        idx = n + i
        if idx < MAX_PARTICLES:
            pt = spawn_queue_type[i]
            pos[idx] = spawn_queue_pos[i]
            vel[idx] = spawn_queue_vel[i]
            force[idx] = ti.Vector([0.0, 0.0, 0.0])
            ptype[idx] = pt
            mass[idx] = type_mass[pt]
            charge[idx] = type_charge[pt]
            radius[idx] = type_radius[pt]
            alive[idx] = 1
            # Spawn products are never frozen; only add_particle(is_frozen=True) sets frozen
            frozen[idx] = 0
            trail_head[idx] = 0
            trail_count[idx] = 0


@ti.kernel
def _finalize_spawn():
    sc = spawn_count[None]
    if sc > 0:
        n = num_active[None]
        added = ti.min(sc, MAX_PARTICLES - n)
        num_active[None] = n + added
        spawn_count[None] = 0


@ti.kernel
def _update_flashes_and_compact(dt: ti.f32):
    fc = flash_count[None]
    flash_render_count[None] = 0
    for i in range(fc):
        flash_life[i] -= dt * 3.0
    ti.loop_config(serialize=True)
    for i in range(fc):
        if flash_life[i] > 0.0:
            w = ti.atomic_add(flash_render_count[None], 1)
            if w != i and w < MAX_FLASHES:
                flash_render_pos[w] = flash_render_pos[i]
                flash_render_color[w] = flash_render_color[i]
                flash_life[w] = flash_life[i]
    flash_count[None] = flash_render_count[None]


@ti.kernel
def _check_and_compact():
    _needs_compact[None] = 0
    _compact_count[None] = 0
    n = num_active[None]
    ti.loop_config(serialize=True)
    for i in range(n):
        if alive[i] == 1:
            ti.atomic_add(_compact_count[None], 1)
            _compact_src[_compact_count[None] - 1] = i
        else:
            _needs_compact[None] = 1


@ti.kernel
def _do_compact(new_n: ti.i32):
    for w in range(new_n):
        r = _compact_src[w]
        if w != r:
            pos[w] = pos[r]
            vel[w] = vel[r]
            force[w] = force[r]
            mass[w] = mass[r]
            charge[w] = charge[r]
            radius[w] = radius[r]
            ptype[w] = ptype[r]
            alive[w] = 1
            frozen[w] = frozen[r]
            trail_head[w] = trail_head[r]
            trail_count[w] = trail_count[r]
            for t in range(TRAIL_LENGTH):
                trail_pos[w, t] = trail_pos[r, t]
    for i in range(new_n, num_active[None]):
        alive[i] = 0
    num_active[None] = new_n


@ti.kernel
def record_trails():
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        head = trail_head[i]
        trail_pos[i, head] = pos[i]
        trail_head[i] = (head + 1) % TRAIL_LENGTH
        if trail_count[i] < TRAIL_LENGTH:
            trail_count[i] += 1


# ── Statistics ────────────────────────────────────────────────────────────


@ti.kernel
def _compute_stats(sel_idx: ti.i32):
    n = num_active[None]
    ke = ti.cast(0.0, ti.f32)
    mx = ti.cast(0.0, ti.f32)
    my = ti.cast(0.0, ti.f32)
    mz = ti.cast(0.0, ti.f32)
    spd_sum = ti.cast(0.0, ti.f32)
    alive_count = ti.cast(0.0, ti.f32)
    for i in range(NUM_STATS):
        stats[i] = 0.0
    for i in range(n):
        if alive[i] == 0:
            continue
        speed_sq = vel[i].norm_sqr()
        spd = ti.sqrt(speed_sq)
        ti.atomic_add(ke, 0.5 * mass[i] * speed_sq)
        p = mass[i] * vel[i]
        ti.atomic_add(mx, p[0])
        ti.atomic_add(my, p[1])
        ti.atomic_add(mz, p[2])
        ti.atomic_add(spd_sum, spd)
        ti.atomic_add(alive_count, 1.0)
        pt = ptype[i]
        if pt >= 0 and pt < NUM_TYPES:
            ti.atomic_add(stats[8 + pt], 1.0)
    stats[0] = ke
    stats[1] = mx
    stats[2] = my
    stats[3] = mz
    stats[4] = ti.cast(collision_count_acc[None], ti.f32)
    stats[5] = ti.cast(decay_count_acc[None], ti.f32)
    stats[6] = ti.cast(step_counter[None], ti.f32)
    stats[7] = alive_count
    stats[_S_ANN] = ti.cast(annihilation_count_acc[None], ti.f32)
    stats[_S_PAIR] = ti.cast(pair_creation_count_acc[None], ti.f32)
    stats[_S_DHIT] = ti.cast(detector_hits_acc[None], ti.f32)
    stats[_S_DENE] = detector_energy_acc[None]
    stats[_S_BHC] = ti.cast(bh_captures_acc[None], ti.f32)
    if alive_count > 0:
        stats[_S_ASPD] = spd_sum / alive_count

    if sel_idx >= 0 and sel_idx < n and alive[sel_idx] == 1:
        stats[_S_SEL + 0] = pos[sel_idx][0]
        stats[_S_SEL + 1] = pos[sel_idx][1]
        stats[_S_SEL + 2] = pos[sel_idx][2]
        stats[_S_SEL + 3] = vel[sel_idx][0]
        stats[_S_SEL + 4] = vel[sel_idx][1]
        stats[_S_SEL + 5] = vel[sel_idx][2]
        stats[_S_SEL + 6] = mass[sel_idx]
        stats[_S_SEL + 7] = charge[sel_idx]
        stats[_S_SEL + 8] = ti.cast(ptype[sel_idx], ti.f32)
        stats[_S_SEL + 9] = 0.5 * mass[sel_idx] * vel[sel_idx].norm_sqr()
        stats[_S_SEL + 10] = ti.cast(frozen[sel_idx], ti.f32)
        stats[_S_SEL + 11] = vel[sel_idx].norm()


# ── Render helpers ────────────────────────────────────────────────────────


@ti.kernel
def build_render_data(
    base_r: ti.f32,
    r_scale: ti.f32,
    bh_on: ti.i32,
    bh_rs: ti.f32,
    bhx: ti.f32,
    bhy: ti.f32,
    bhz: ti.f32,
    hide_photons: ti.i32,
):
    n = num_active[None]
    bh_p = ti.Vector([bhx, bhy, bhz])
    render_count[None] = 0
    for i in range(n):
        if alive[i] == 1:
            if hide_photons == 1 and ptype[i] == PHOTON:
                continue
            idx = ti.atomic_add(render_count[None], 1)
            render_pos[idx] = _deflect_pos(pos[i], bh_p, bh_rs, bh_on)
            pt = ptype[i]
            base_color = type_color[pt]
            speed = vel[i].norm()
            glow = ti.min(speed / 10.0, 1.0) * 0.4
            c = ti.min(base_color + glow, 1.0)
            if frozen[i] == 1:
                c = c * 0.5 + ti.Vector([0.5, 0.5, 0.5]) * 0.5
            if bh_on == 1:
                r_bh = (pos[i] - bh_p).norm()
                if r_bh > bh_rs and r_bh < bh_rs * 20.0:
                    sqrt_factor = ti.sqrt(ti.max(1.0 - bh_rs / r_bh, 0.01))
                    redshift = 1.0 - sqrt_factor
                    c = c * sqrt_factor + ti.Vector([1.0, 0.2, 0.0]) * redshift
            render_color[idx] = c


@ti.func
def _deflect_pos(
    p: ti.template(), bh_p: ti.template(), bh_rs: ti.f32, bh_on: ti.i32
) -> ti.template():
    result = p
    if bh_on == 1:
        to_bh = bh_p - p
        r = to_bh.norm()
        r_eff = r - bh_rs
        if r > bh_rs * 1.05 and r < bh_rs * 30.0 and r_eff > 0.01:
            strength = 2.0 * bh_rs * bh_rs / (r_eff * r_eff + bh_rs * 0.5)
            result = p + to_bh / r * strength
    return result


@ti.kernel
def build_trail_lines(
    bh_on: ti.i32, bh_rs: ti.f32, bhx: ti.f32, bhy: ti.f32, bhz: ti.f32, hide_photons: ti.i32
):
    trail_line_count[None] = 0
    n = num_active[None]
    bh_p = ti.Vector([bhx, bhy, bhz])
    for i in range(n):
        if alive[i] == 0:
            continue
        if hide_photons == 1 and ptype[i] == PHOTON:
            continue
        tc = trail_count[i]
        if tc < 2:
            continue
        head = trail_head[i]
        pt = ptype[i]
        base_color = type_color[pt]
        for seg in range(tc - 1):
            idx_a = (head - tc + seg + TRAIL_LENGTH) % TRAIL_LENGTH
            idx_b = (head - tc + seg + 1 + TRAIL_LENGTH) % TRAIL_LENGTH
            line_idx = ti.atomic_add(trail_line_count[None], 1)
            vi = line_idx * 2
            if vi + 1 < MAX_PARTICLES * TRAIL_LENGTH * 2:
                alpha = ti.cast(seg, ti.f32) / ti.cast(tc, ti.f32)
                fade = 0.35 + 0.65 * alpha
                pa = _deflect_pos(trail_pos[i, idx_a], bh_p, bh_rs, bh_on)
                pb = _deflect_pos(trail_pos[i, idx_b], bh_p, bh_rs, bh_on)
                trail_vertices[vi] = pa
                trail_vertices[vi + 1] = pb
                trail_colors[vi] = base_color * fade * 0.6
                trail_colors[vi + 1] = base_color * fade * 0.85


@ti.kernel
def build_bh_ring(bhx: ti.f32, bhy: ti.f32, bhz: ti.f32, bh_rs: ti.f32):
    r_shadow = BH_SHADOW_FACTOR * bh_rs
    half = BH_RING_N // 2
    for i in range(BH_RING_N):
        if i < half:
            y_frac = 1.0 - 2.0 * (ti.cast(i, ti.f32) + 0.5) / ti.cast(half, ti.f32)
            r_lat = ti.sqrt(ti.max(1.0 - y_frac * y_frac, 0.0))
            theta = 2.39996 * ti.cast(i, ti.f32)
            bh_ring_pos[i] = ti.Vector(
                [
                    bhx + r_shadow * r_lat * ti.cos(theta),
                    bhy + r_shadow * y_frac,
                    bhz + r_shadow * r_lat * ti.sin(theta),
                ]
            )
            brightness = 0.75 + 0.25 * ti.abs(y_frac)
            bh_ring_color[i] = ti.Vector([1.0, 0.92, 0.75]) * brightness
        else:
            angle = ti.cast(i - half, ti.f32) * 6.28318 / ti.cast(half, ti.f32)
            r_glow = r_shadow * 1.3
            bh_ring_pos[i] = ti.Vector(
                [
                    bhx + r_glow * ti.cos(angle),
                    bhy,
                    bhz + r_glow * ti.sin(angle),
                ]
            )
            brightness = 0.4 + 0.2 * ti.sin(angle * 5.0)
            bh_ring_color[i] = ti.Vector([1.0, 0.6, 0.15]) * brightness


@ti.kernel
def init_bg_stars():
    for i in range(NUM_BG_STARS):
        theta = ti.random(ti.f32) * 6.28318
        phi = ti.acos(2.0 * ti.random(ti.f32) - 1.0)
        r = 55.0 + ti.random(ti.f32) * 35.0
        star_pos[i] = ti.Vector(
            [
                r * ti.sin(phi) * ti.cos(theta),
                r * ti.sin(phi) * ti.sin(theta),
                r * ti.cos(phi),
            ]
        )
        brightness = 0.2 + ti.random(ti.f32) * 0.8
        brightness = brightness * brightness
        temp = ti.random(ti.f32)
        if temp < 0.25:
            star_color[i] = ti.Vector([0.7, 0.8, 1.0]) * brightness
        elif temp < 0.55:
            star_color[i] = ti.Vector([1.0, 1.0, 0.95]) * brightness
        elif temp < 0.80:
            star_color[i] = ti.Vector([1.0, 0.9, 0.7]) * brightness
        else:
            star_color[i] = ti.Vector([1.0, 0.7, 0.4]) * brightness


@ti.kernel
def init_accretion_disk(bhx: ti.f32, bhy: ti.f32, bhz: ti.f32, bh_gm: ti.f32, bh_rs: ti.f32):
    r_isco = 3.0 * bh_rs
    r_outer = 14.0 * bh_rs
    for i in range(DISK_N):
        t = ti.random(ti.f32)
        r = r_isco + t * t * (r_outer - r_isco)
        angle = ti.random(ti.f32) * 6.28318
        dy = (ti.random(ti.f32) - 0.5) * 0.12 * bh_rs
        disk_pos[i] = ti.Vector(
            [
                bhx + r * ti.cos(angle),
                bhy + dy,
                bhz + r * ti.sin(angle),
            ]
        )
        v_c = ti.sqrt(bh_gm * r) / (r - bh_rs + 0.01)
        disk_vel[i] = ti.Vector(
            [
                -v_c * ti.sin(angle),
                0.0,
                v_c * ti.cos(angle),
            ]
        )


@ti.kernel
def update_accretion_disk(
    dt: ti.f32, bh_gm: ti.f32, bh_rs: ti.f32, bhx: ti.f32, bhy: ti.f32, bhz: ti.f32
):
    bh = ti.Vector([bhx, bhy, bhz])
    r_isco = 3.0 * bh_rs
    r_outer = 14.0 * bh_rs
    for i in range(DISK_N):
        diff = bh - disk_pos[i]
        r = diff.norm()
        if r < bh_rs:
            angle = ti.random(ti.f32) * 6.28318
            r_new = r_outer * (0.7 + ti.random(ti.f32) * 0.3)
            disk_pos[i] = ti.Vector(
                [
                    bhx + r_new * ti.cos(angle),
                    bhy + (ti.random(ti.f32) - 0.5) * 0.12 * bh_rs,
                    bhz + r_new * ti.sin(angle),
                ]
            )
            v_c = ti.sqrt(bh_gm * r_new) / (r_new - bh_rs + 0.01)
            disk_vel[i] = ti.Vector([-v_c * ti.sin(angle), 0.0, v_c * ti.cos(angle)])
            r = r_new

        r_eff = ti.max(r - bh_rs, 0.01)
        f_mag = bh_gm / (r_eff * r_eff)
        disk_vel[i] += f_mag * (diff / r) * dt
        disk_vel[i] *= 0.9998
        disk_pos[i] += disk_vel[i] * dt

        disk_pos[i][1] *= 0.995
        disk_vel[i][1] *= 0.99

        r_now = (disk_pos[i] - bh).norm()
        temp_frac = ti.max(1.0 - (r_now - r_isco) / (r_outer - r_isco + 0.01), 0.0)
        temp_frac = ti.min(temp_frac, 1.0)

        hot = ti.Vector([0.85, 0.9, 1.0])
        warm = ti.Vector([1.0, 0.7, 0.3])
        cool = ti.Vector([0.8, 0.3, 0.08])
        if temp_frac > 0.5:
            t2 = (temp_frac - 0.5) * 2.0
            disk_color[i] = warm * (1.0 - t2) + hot * t2
        else:
            t2 = temp_frac * 2.0
            disk_color[i] = cool * (1.0 - t2) + warm * t2
        brightness = 0.5 + 0.9 * temp_frac
        disk_color[i] *= brightness


# ── Main step / maintenance / stats ───────────────────────────────────────


def _call_forces(
    coulomb_k, gravity_g, mag_field, e_field, strong_k, strong_range, bh_i, bh_gm, bh_rs, bh_pos
):
    """Compute forces from current positions."""
    compute_forces(
        coulomb_k,
        gravity_g,
        mag_field[0],
        mag_field[1],
        mag_field[2],
        e_field[0],
        e_field[1],
        e_field[2],
        strong_k,
        strong_range,
        bh_i,
        bh_gm,
        bh_rs,
        bh_pos[0],
        bh_pos[1],
        bh_pos[2],
    )


def step(
    dt,
    coulomb_k,
    gravity_g,
    mag_field,
    e_field,
    strong_k,
    strong_range,
    use_rel,
    c_light,
    synchro,
    boundary_mode,
    boundary_size,
    pair_threshold,
    bh_on=False,
    bh_gm=0.0,
    bh_rs=0.0,
    bh_pos=(0.0, 0.0, 0.0),
):
    """Leapfrog: half-kick -> drift -> collisions/decay/spawn -> half-kick.
    Spawned particles get forces + half-kick in same step (num_active updated before 2nd forces)."""
    bh_i = 1 if bh_on else 0
    use_rel_i = 1 if use_rel else 0
    bh_xyz = (bh_pos[0], bh_pos[1], bh_pos[2])
    use_leapfrog = _config.INTEGRATOR == "leapfrog"

    # 1. Forces, 2. Half-kick + drift (Leapfrog) or full Euler step
    _call_forces(
        coulomb_k, gravity_g, mag_field, e_field, strong_k, strong_range, bh_i, bh_gm, bh_rs, bh_pos
    )

    if use_leapfrog:
        _integrate_step(dt * 0.5, dt, use_rel_i, c_light, synchro, bh_i, bh_rs, *bh_xyz)
    else:
        _integrate_step(dt, dt, use_rel_i, c_light, synchro, bh_i, bh_rs, *bh_xyz)

    # 3. Boundaries, 4. Collisions (may spawn), 5. Decay (may spawn)
    if boundary_mode == "reflect":
        apply_boundaries_reflect(boundary_size)
    elif boundary_mode == "periodic":
        apply_boundaries_periodic(boundary_size)

    detect_collisions(pair_threshold, c_light)
    monte_carlo_decay(dt, use_rel_i, c_light, bh_i, bh_rs, bh_pos[0], bh_pos[1], bh_pos[2])
    # 6. Apply spawn queue (frozen=0), 7. Finalize (num_active += added)
    _apply_spawn_queue()
    _finalize_spawn()
    record_trails()

    # 8. Leapfrog second half: forces (include new particles), half-kick, no drift
    if use_leapfrog:
        _call_forces(
            coulomb_k,
            gravity_g,
            mag_field,
            e_field,
            strong_k,
            strong_range,
            bh_i,
            bh_gm,
            bh_rs,
            bh_pos,
        )
        _integrate_step(dt * 0.5, 0.0, use_rel_i, c_light, synchro, bh_i, bh_rs, *bh_xyz)

    step_counter[None] += 1


def do_maintenance(dt):
    _update_flashes_and_compact(dt)
    _check_and_compact()
    if _needs_compact[None]:
        _do_compact(_compact_count[None])


def refresh_stats(sel_idx=0):
    _compute_stats(sel_idx)
    s = stats.to_numpy()
    cached_stats["ke"] = float(s[0])
    cached_stats["mom"] = float((s[1] ** 2 + s[2] ** 2 + s[3] ** 2) ** 0.5)
    cached_stats["mom_x"] = float(s[1])
    cached_stats["mom_y"] = float(s[2])
    cached_stats["mom_z"] = float(s[3])
    cached_stats["collisions"] = int(s[4])
    cached_stats["decays"] = int(s[5])
    cached_stats["step"] = int(s[6])
    cached_stats["particles"] = int(s[7])
    for i in range(NUM_TYPES):
        cached_stats[f"type_{i}"] = int(s[8 + i])
    cached_stats["annihilations"] = int(s[_S_ANN])
    cached_stats["pair_creations"] = int(s[_S_PAIR])
    cached_stats["detector_hits"] = int(s[_S_DHIT])
    cached_stats["detector_energy"] = float(s[_S_DENE])
    cached_stats["avg_speed"] = float(s[_S_ASPD])
    cached_stats["bh_captures"] = int(s[_S_BHC])
    cached_stats["sel_px"] = float(s[_S_SEL + 0])
    cached_stats["sel_py"] = float(s[_S_SEL + 1])
    cached_stats["sel_pz"] = float(s[_S_SEL + 2])
    cached_stats["sel_vx"] = float(s[_S_SEL + 3])
    cached_stats["sel_vy"] = float(s[_S_SEL + 4])
    cached_stats["sel_vz"] = float(s[_S_SEL + 5])
    cached_stats["sel_mass"] = float(s[_S_SEL + 6])
    cached_stats["sel_charge"] = float(s[_S_SEL + 7])
    cached_stats["sel_type"] = int(s[_S_SEL + 8])
    cached_stats["sel_ke"] = float(s[_S_SEL + 9])
    cached_stats["sel_frozen"] = int(s[_S_SEL + 10])
    cached_stats["sel_speed"] = float(s[_S_SEL + 11])
    cached_stats["flash_rc"] = flash_render_count[None]

    ts = time_series
    ts["step"].append(cached_stats["step"])
    ts["ke"].append(cached_stats["ke"])
    ts["particles"].append(cached_stats["particles"])
    ts["collisions"].append(cached_stats["collisions"])
    ts["decays"].append(cached_stats["decays"])
    ts["annihilations"].append(cached_stats["annihilations"])
    ts["pair_creations"].append(cached_stats["pair_creations"])
    ts["momentum"].append(cached_stats["mom"])

    im = inv_mass_buffer.to_numpy()
    cached_stats["inv_masses"] = [float(x) for x in im if x > 0.01]


def prepare_render(
    base_r, r_scale, bh_on=False, bh_rs=0.0, bh_pos=(0.0, 0.0, 0.0), hide_photons=False
):
    bh_i = 1 if bh_on else 0
    hp = 1 if hide_photons else 0
    build_render_data(base_r, r_scale, bh_i, bh_rs, bh_pos[0], bh_pos[1], bh_pos[2], hp)
    build_trail_lines(bh_i, bh_rs, bh_pos[0], bh_pos[1], bh_pos[2], hp)
    if bh_on:
        bh_eh_pos[0] = ti.Vector([bh_pos[0], bh_pos[1], bh_pos[2]])
        bh_eh_color[0] = ti.Vector([0.0, 0.0, 0.0])


def export_state(filepath: str) -> None:
    """Export current state and time series to HDF5 file."""
    n = num_active[None]
    if n == 0:
        return
    positions = np.zeros((n, 3), dtype=np.float32)
    velocities = np.zeros((n, 3), dtype=np.float32)
    masses = np.zeros(n, dtype=np.float32)
    charges = np.zeros(n, dtype=np.float32)
    types = np.zeros(n, dtype=np.int32)

    for i in range(n):
        p_vec = pos[i]
        v_vec = vel[i]
        positions[i] = [float(p_vec[0]), float(p_vec[1]), float(p_vec[2])]
        velocities[i] = [float(v_vec[0]), float(v_vec[1]), float(v_vec[2])]
        masses[i] = float(mass[i])
        charges[i] = float(charge[i])
        types[i] = int(ptype[i])

    with h5py.File(filepath, "w") as f:
        f.create_dataset("positions", data=positions)
        f.create_dataset("velocities", data=velocities)
        f.create_dataset("masses", data=masses)
        f.create_dataset("charges", data=charges)
        f.create_dataset("types", data=types)
        f.attrs["num_particles"] = n

        for key, vals in time_series.items():
            if vals:
                f.create_dataset(f"timeseries/{key}", data=np.array(vals, dtype=np.float32))

    print(f"Exported {n} particles + time series to {filepath}")
