import taichi as ti
import numpy as np
from config import (
    MAX_PARTICLES, TRAIL_LENGTH, COULOMB_K, GRAVITY_G,
    SOFTENING, CUTOFF_RADIUS, COLLISION_RESTITUTION, SPAWN_VELOCITY_SPREAD,
    MAX_VELOCITY, BOUNDARY_SIZE, SPEED_OF_LIGHT, PAIR_CREATION_THRESHOLD,
    NUM_TYPES,
)
from particles import (
    MAX_DECAY_PRODUCTS, MAX_CHANNELS,
    type_mass, type_charge, type_radius, type_decay_prob, type_color,
    type_is_baryon, collision_rule_table,
    num_channels, channel_num_products, channel_products, channel_branch_cumulative,
)

MAX_FLASHES = 256
NUM_STATS = 48
INV_MASS_BUF = 64

pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
vel = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
force = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
mass = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
charge = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
radius = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
ptype = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
alive = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
frozen = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
decay_prob = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)

trail_pos = ti.Vector.field(3, dtype=ti.f32, shape=(MAX_PARTICLES, TRAIL_LENGTH))
trail_head = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
trail_count = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

num_active = ti.field(dtype=ti.i32, shape=())

# Stats: bulk-read by CPU every N frames via to_numpy()
# 0:ke 1-3:mom 4:collisions 5:decays 6:step 7:n_active
# 8-17:per-type counts 18:annihilations 19:pair_creations
# 20:detector_hits 21:detector_energy 22:avg_speed 23:total_pe
# 24-26:sel pos 27-29:sel vel 30:sel mass 31:sel charge
# 32:sel type 33:sel ke 34:sel frozen 35:sel speed
stats = ti.field(dtype=ti.f32, shape=NUM_STATS)

collision_count_acc = ti.field(dtype=ti.i32, shape=())
decay_count_acc = ti.field(dtype=ti.i32, shape=())
annihilation_count_acc = ti.field(dtype=ti.i32, shape=())
pair_creation_count_acc = ti.field(dtype=ti.i32, shape=())
detector_hits_acc = ti.field(dtype=ti.i32, shape=())
detector_energy_acc = ti.field(dtype=ti.f32, shape=())
step_counter = ti.field(dtype=ti.i32, shape=())

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
flash_render_color = ti.Vector.field(3, dtype=ti.f32, shape=MAX_FLASHES)
flash_life = ti.field(dtype=ti.f32, shape=MAX_FLASHES)
flash_count = ti.field(dtype=ti.i32, shape=())
flash_render_count = ti.field(dtype=ti.i32, shape=())

_compact_src = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
_compact_count = ti.field(dtype=ti.i32, shape=())
_needs_compact = ti.field(dtype=ti.i32, shape=())

cached_stats = {}
time_series = {"step": [], "ke": [], "particles": [], "collisions": [], "decays": [],
               "annihilations": [], "pair_creations": [], "momentum": []}


def _reset_cached():
    keys = ["ke", "mom", "collisions", "decays", "step", "particles",
            "annihilations", "pair_creations", "detector_hits", "detector_energy",
            "avg_speed", "total_pe", "flash_rc",
            "sel_px", "sel_py", "sel_pz", "sel_vx", "sel_vy", "sel_vz",
            "sel_mass", "sel_charge", "sel_type", "sel_ke", "sel_frozen", "sel_speed"]
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
    step_counter[None] = 0
    flash_count[None] = 0
    flash_render_count[None] = 0
    inv_mass_head[None] = 0
    for i in range(NUM_STATS):
        stats[i] = 0.0
    for i in range(MAX_PARTICLES):
        alive[i] = 0
        frozen[i] = 0
        trail_head[i] = 0
        trail_count[i] = 0
    for i in range(INV_MASS_BUF):
        inv_mass_buffer[i] = 0.0


def init_simulation():
    _clear_all()
    _reset_cached()
    for k in time_series:
        time_series[k].clear()


def add_particle(position, velocity, particle_type, is_frozen=False):
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
    decay_prob[idx] = float(type_decay_prob[particle_type])
    alive[idx] = 1
    frozen[idx] = 1 if is_frozen else 0
    trail_head[idx] = 0
    trail_count[idx] = 0
    num_active[None] = n + 1
    return idx


@ti.kernel
def compute_forces(coulomb_k: ti.f32, gravity_g: ti.f32,
                   bx: ti.f32, by: ti.f32, bz: ti.f32,
                   ex: ti.f32, ey: ti.f32, ez: ti.f32,
                   strong_k: ti.f32, strong_range: ti.f32):
    n = num_active[None]
    mag_field = ti.Vector([bx, by, bz])
    e_field = ti.Vector([ex, ey, ez])
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

        force[i] = f


@ti.kernel
def integrate(dt: ti.f32, use_rel: ti.i32, c_light: ti.f32, synchro: ti.f32):
    n = num_active[None]
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
                damp = power * dt / (effective_m * spd * spd)
                vel[i] *= ti.max(1.0 - damp, 0.5)

        vel[i] += acc * dt
        speed = vel[i].norm()
        if speed > MAX_VELOCITY:
            vel[i] *= MAX_VELOCITY / speed
        pos[i] += vel[i] * dt


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


@ti.kernel
def detect_collisions(pair_threshold: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        for j in range(i + 1, n):
            if alive[j] == 0:
                continue
            diff = pos[j] - pos[i]
            dist = diff.norm()
            min_dist = (radius[i] + radius[j]) * 1.5
            if dist < min_dist and dist > 1e-8:
                normal = diff / dist
                overlap = min_dist - dist
                t1 = ptype[i]
                t2 = ptype[j]
                rule = collision_rule_table[t1, t2]

                if rule == 1:
                    # Annihilation (e.g. electron + positron -> 2 photons)
                    alive[i] = 0
                    alive[j] = 0
                    ti.atomic_add(annihilation_count_acc[None], 1)
                    center = (pos[i] + pos[j]) * 0.5
                    mom = mass[i] * vel[i] + mass[j] * vel[j]
                    mom_dir = mom.normalized() if mom.norm() > 1e-8 else ti.Vector([1.0, 0.0, 0.0])
                    perp = ti.Vector([0.0, 1.0, 0.0])
                    if ti.abs(mom_dir.dot(perp)) > 0.9:
                        perp = ti.Vector([1.0, 0.0, 0.0])
                    perp = (perp - mom_dir * perp.dot(mom_dir)).normalized()
                    s1 = ti.atomic_add(spawn_count[None], 1)
                    if s1 < MAX_PARTICLES:
                        spawn_queue_pos[s1] = center
                        spawn_queue_vel[s1] = (mom_dir + perp * 0.3).normalized() * MAX_VELOCITY * 0.8
                        spawn_queue_type[s1] = 6
                    s2 = ti.atomic_add(spawn_count[None], 1)
                    if s2 < MAX_PARTICLES:
                        spawn_queue_pos[s2] = center
                        spawn_queue_vel[s2] = (mom_dir - perp * 0.3).normalized() * MAX_VELOCITY * 0.8
                        spawn_queue_type[s2] = 6
                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = center
                        flash_render_color[fidx] = ti.Vector([0.9, 0.9, 0.3])
                        flash_life[fidx] = 1.0

                elif rule == 2:
                    # Collision-induced decay: both particles decay
                    alive[i] = 0
                    alive[j] = 0
                    ti.atomic_add(collision_count_acc[None], 1)
                    center = (pos[i] + pos[j]) * 0.5
                    parent_vel = (mass[i] * vel[i] + mass[j] * vel[j]) / (mass[i] + mass[j])
                    inv_m = mass[i] + mass[j]
                    idx_im = ti.atomic_add(inv_mass_head[None], 1) % INV_MASS_BUF
                    inv_mass_buffer[idx_im] = inv_m
                    for p in range(4):
                        product_type = ti.cast(ti.random(ti.f32) * 6, ti.i32)
                        product_type = ti.max(0, ti.min(product_type, 5))
                        theta = ti.random(ti.f32) * 6.28318
                        phi = ti.acos(2.0 * ti.random(ti.f32) - 1.0)
                        rd = ti.Vector([ti.sin(phi)*ti.cos(theta), ti.sin(phi)*ti.sin(theta), ti.cos(phi)])
                        s = ti.atomic_add(spawn_count[None], 1)
                        if s < MAX_PARTICLES:
                            spawn_queue_pos[s] = center + rd * 0.2
                            spawn_queue_vel[s] = parent_vel * 0.3 + rd * SPAWN_VELOCITY_SPREAD * 2.0
                            spawn_queue_type[s] = product_type
                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = center
                        flash_render_color[fidx] = ti.Vector([0.3, 0.8, 0.8])
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

                        # Pair creation from high-energy collision
                        combined_ke = 0.5 * mass[i] * vel[i].norm_sqr() + 0.5 * mass[j] * vel[j].norm_sqr()
                        if combined_ke > pair_threshold and ti.random(ti.f32) < 0.08:
                            c = (pos[i] + pos[j]) * 0.5
                            theta = ti.random(ti.f32) * 6.28318
                            phi = ti.acos(2.0 * ti.random(ti.f32) - 1.0)
                            rd = ti.Vector([ti.sin(phi)*ti.cos(theta), ti.sin(phi)*ti.sin(theta), ti.cos(phi)])
                            creation_cost = type_mass[1] + type_mass[9]
                            if combined_ke > creation_cost * 2.0:
                                s1 = ti.atomic_add(spawn_count[None], 1)
                                if s1 < MAX_PARTICLES:
                                    spawn_queue_pos[s1] = c + rd * 0.15
                                    spawn_queue_vel[s1] = rd * SPAWN_VELOCITY_SPREAD
                                    spawn_queue_type[s1] = 1
                                s2 = ti.atomic_add(spawn_count[None], 1)
                                if s2 < MAX_PARTICLES:
                                    spawn_queue_pos[s2] = c - rd * 0.15
                                    spawn_queue_vel[s2] = -rd * SPAWN_VELOCITY_SPREAD
                                    spawn_queue_type[s2] = 9
                                ti.atomic_add(pair_creation_count_acc[None], 1)
                                factor = ti.sqrt(ti.max(1.0 - creation_cost / (combined_ke + 1e-8), 0.1))
                                if frozen[i] == 0:
                                    vel[i] *= factor
                                if frozen[j] == 0:
                                    vel[j] *= factor
                                fidx = ti.atomic_add(flash_count[None], 1)
                                if fidx < MAX_FLASHES:
                                    flash_render_pos[fidx] = c
                                    flash_render_color[fidx] = ti.Vector([0.5, 0.3, 0.7])
                                    flash_life[fidx] = 0.8

                    fidx2 = ti.atomic_add(flash_count[None], 1)
                    if fidx2 < MAX_FLASHES:
                        flash_render_pos[fidx2] = (pos[i] + pos[j]) * 0.5
                        c1 = type_color[t1]
                        c2 = type_color[t2]
                        flash_render_color[fidx2] = (c1 + c2) * 0.25
                        flash_life[fidx2] = 0.6


@ti.kernel
def monte_carlo_decay(dt: ti.f32, use_rel: ti.i32, c_light: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0 or frozen[i] == 1:
            continue
        pt = ptype[i]
        dp = decay_prob[i]
        if dp <= 0.0:
            continue
        nc = num_channels[pt]
        if nc == 0:
            continue

        effective_dp = dp
        if use_rel == 1 and c_light > 0.0:
            speed_sq = vel[i].norm_sqr()
            beta_sq = speed_sq / (c_light * c_light)
            gamma = 1.0 / ti.sqrt(1.0 - ti.min(beta_sq, 0.99))
            effective_dp = dp / gamma

        if ti.random(ti.f32) < effective_dp * dt * 100.0:
            r = ti.random(ti.f32)
            selected_channel = 0
            for c in range(nc):
                if r <= channel_branch_cumulative[pt, c]:
                    selected_channel = c
                    break

            n_products = channel_num_products[pt, selected_channel]
            parent_pos = pos[i]
            parent_vel = vel[i]
            parent_mass_val = mass[i]

            alive[i] = 0
            ti.atomic_add(decay_count_acc[None], 1)

            idx_im = ti.atomic_add(inv_mass_head[None], 1) % INV_MASS_BUF
            inv_mass_buffer[idx_im] = parent_mass_val

            fidx = ti.atomic_add(flash_count[None], 1)
            if fidx < MAX_FLASHES:
                flash_render_pos[fidx] = parent_pos
                flash_render_color[fidx] = type_color[pt] * 0.35
                flash_life[fidx] = 0.8

            total_product_mass = 0.0
            for p in range(n_products):
                total_product_mass += type_mass[channel_products[pt, selected_channel, p]]

            for p in range(n_products):
                product_type = channel_products[pt, selected_channel, p]
                product_mass = type_mass[product_type]
                frac = product_mass / (total_product_mass + 1e-8)

                theta = ti.random(ti.f32) * 6.28318
                phi = ti.acos(2.0 * ti.random(ti.f32) - 1.0)
                rand_dir = ti.Vector([
                    ti.sin(phi) * ti.cos(theta),
                    ti.sin(phi) * ti.sin(theta),
                    ti.cos(phi),
                ])

                available_e = 0.5 * parent_mass_val * parent_vel.norm_sqr()
                kick = ti.sqrt(2.0 * available_e / (product_mass + 1e-8) / n_products + 1e-8)
                kick = ti.min(kick, SPAWN_VELOCITY_SPREAD * 3.0)

                idx = ti.atomic_add(spawn_count[None], 1)
                if idx < MAX_PARTICLES:
                    spawn_queue_pos[idx] = parent_pos + rand_dir * (radius[i] * 1.5)
                    spawn_queue_vel[idx] = parent_vel * frac + rand_dir * kick
                    spawn_queue_type[idx] = product_type


@ti.kernel
def _apply_spawn_queue():
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
            decay_prob[idx] = type_decay_prob[pt]
            alive[idx] = 1
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
            decay_prob[w] = decay_prob[r]
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
        ti.atomic_add(stats[8 + pt], 1.0)
    stats[0] = ke
    stats[1] = mx
    stats[2] = my
    stats[3] = mz
    stats[4] = ti.cast(collision_count_acc[None], ti.f32)
    stats[5] = ti.cast(decay_count_acc[None], ti.f32)
    stats[6] = ti.cast(step_counter[None], ti.f32)
    stats[7] = alive_count
    stats[18] = ti.cast(annihilation_count_acc[None], ti.f32)
    stats[19] = ti.cast(pair_creation_count_acc[None], ti.f32)
    stats[20] = ti.cast(detector_hits_acc[None], ti.f32)
    stats[21] = detector_energy_acc[None]
    if alive_count > 0:
        stats[22] = spd_sum / alive_count

    if sel_idx >= 0 and sel_idx < n and alive[sel_idx] == 1:
        stats[24] = pos[sel_idx][0]
        stats[25] = pos[sel_idx][1]
        stats[26] = pos[sel_idx][2]
        stats[27] = vel[sel_idx][0]
        stats[28] = vel[sel_idx][1]
        stats[29] = vel[sel_idx][2]
        stats[30] = mass[sel_idx]
        stats[31] = charge[sel_idx]
        stats[32] = ti.cast(ptype[sel_idx], ti.f32)
        stats[33] = 0.5 * mass[sel_idx] * vel[sel_idx].norm_sqr()
        stats[34] = ti.cast(frozen[sel_idx], ti.f32)
        stats[35] = vel[sel_idx].norm()


@ti.kernel
def build_render_data(base_r: ti.f32, r_scale: ti.f32):
    n = num_active[None]
    render_count[None] = 0
    for i in range(n):
        if alive[i] == 1:
            idx = ti.atomic_add(render_count[None], 1)
            render_pos[idx] = pos[i]
            pt = ptype[i]
            base_color = type_color[pt]
            speed = vel[i].norm()
            glow = ti.min(speed / 10.0, 1.0) * 0.4
            c = ti.min(base_color + glow, 1.0)
            if frozen[i] == 1:
                c = c * 0.5 + ti.Vector([0.5, 0.5, 0.5]) * 0.5
            render_color[idx] = c


@ti.kernel
def build_trail_lines():
    trail_line_count[None] = 0
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
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
                fade = alpha * alpha
                trail_vertices[vi] = trail_pos[i, idx_a]
                trail_vertices[vi + 1] = trail_pos[i, idx_b]
                trail_colors[vi] = base_color * fade * 0.5
                trail_colors[vi + 1] = base_color * fade * 0.7


def step(dt, coulomb_k, gravity_g, mag_field, e_field,
         strong_k, strong_range, use_rel, c_light, synchro,
         boundary_mode, boundary_size, pair_threshold):
    compute_forces(coulomb_k, gravity_g,
                   mag_field[0], mag_field[1], mag_field[2],
                   e_field[0], e_field[1], e_field[2],
                   strong_k, strong_range)
    integrate(dt, 1 if use_rel else 0, c_light, synchro)

    if boundary_mode == "reflect":
        apply_boundaries_reflect(boundary_size)
    elif boundary_mode == "periodic":
        apply_boundaries_periodic(boundary_size)

    detect_collisions(pair_threshold)
    monte_carlo_decay(dt, 1 if use_rel else 0, c_light)
    _apply_spawn_queue()
    _finalize_spawn()
    record_trails()
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
    cached_stats["mom"] = float((s[1]**2 + s[2]**2 + s[3]**2)**0.5)
    cached_stats["collisions"] = int(s[4])
    cached_stats["decays"] = int(s[5])
    cached_stats["step"] = int(s[6])
    cached_stats["particles"] = int(s[7])
    for i in range(NUM_TYPES):
        cached_stats[f"type_{i}"] = int(s[8 + i])
    cached_stats["annihilations"] = int(s[18])
    cached_stats["pair_creations"] = int(s[19])
    cached_stats["detector_hits"] = int(s[20])
    cached_stats["detector_energy"] = float(s[21])
    cached_stats["avg_speed"] = float(s[22])
    cached_stats["sel_px"] = float(s[24])
    cached_stats["sel_py"] = float(s[25])
    cached_stats["sel_pz"] = float(s[26])
    cached_stats["sel_vx"] = float(s[27])
    cached_stats["sel_vy"] = float(s[28])
    cached_stats["sel_vz"] = float(s[29])
    cached_stats["sel_mass"] = float(s[30])
    cached_stats["sel_charge"] = float(s[31])
    cached_stats["sel_type"] = int(s[32])
    cached_stats["sel_ke"] = float(s[33])
    cached_stats["sel_frozen"] = int(s[34])
    cached_stats["sel_speed"] = float(s[35])
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


def prepare_render(base_r, r_scale):
    build_render_data(base_r, r_scale)
    build_trail_lines()


def export_state(filepath):
    n = num_active[None]
    if n == 0:
        return
    import h5py
    positions = np.zeros((n, 3), dtype=np.float32)
    velocities = np.zeros((n, 3), dtype=np.float32)
    masses = np.zeros(n, dtype=np.float32)
    charges = np.zeros(n, dtype=np.float32)
    types = np.zeros(n, dtype=np.int32)

    for i in range(n):
        p = pos[i]; v = vel[i]
        positions[i] = [float(p[0]), float(p[1]), float(p[2])]
        velocities[i] = [float(v[0]), float(v[1]), float(v[2])]
        masses[i] = float(mass[i])
        charges[i] = float(charge[i])
        types[i] = int(ptype[i])

    with h5py.File(filepath, 'w') as f:
        f.create_dataset('positions', data=positions)
        f.create_dataset('velocities', data=velocities)
        f.create_dataset('masses', data=masses)
        f.create_dataset('charges', data=charges)
        f.create_dataset('types', data=types)
        f.attrs['num_particles'] = n

        for key, vals in time_series.items():
            if vals:
                f.create_dataset(f'timeseries/{key}', data=np.array(vals, dtype=np.float32))

    print(f"Exported {n} particles + time series to {filepath}")
