import taichi as ti
import numpy as np
from config import (
    MAX_PARTICLES, TRAIL_LENGTH, COULOMB_K, GRAVITY_G,
    SOFTENING, CUTOFF_RADIUS, COLLISION_RESTITUTION, SPAWN_VELOCITY_SPREAD,
    MAX_VELOCITY, BOUNDARY_SIZE,
)
from particles import (
    NUM_TYPES, MAX_DECAY_PRODUCTS, MAX_CHANNELS,
    type_mass, type_charge, type_radius, type_decay_prob, type_color,
    num_channels, channel_num_products, channel_products, channel_branch_cumulative,
)

MAX_FLASHES = 256

pos = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
vel = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
force = ti.Vector.field(3, dtype=ti.f32, shape=MAX_PARTICLES)
mass = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
charge = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
radius = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
ptype = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
alive = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
decay_prob = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)
kinetic_energy = ti.field(dtype=ti.f32, shape=MAX_PARTICLES)

trail_pos = ti.Vector.field(3, dtype=ti.f32, shape=(MAX_PARTICLES, TRAIL_LENGTH))
trail_head = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)
trail_count = ti.field(dtype=ti.i32, shape=MAX_PARTICLES)

num_active = ti.field(dtype=ti.i32, shape=())

# Stats written by GPU, read periodically by CPU
stats = ti.field(dtype=ti.f32, shape=8)
# [0]=total_ke, [1]=mom_x, [2]=mom_y, [3]=mom_z, [4]=collision_count, [5]=decay_count, [6]=step_count, [7]=num_active
collision_count_acc = ti.field(dtype=ti.i32, shape=())
decay_count_acc = ti.field(dtype=ti.i32, shape=())
step_counter = ti.field(dtype=ti.i32, shape=())

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

# Cached stats read from GPU (Python-side)
cached_stats = {
    "ke": 0.0, "mom": 0.0,
    "collisions": 0, "decays": 0,
    "step": 0, "particles": 0,
    "flash_rc": 0,
}


@ti.kernel
def _clear_all():
    num_active[None] = 0
    spawn_count[None] = 0
    collision_count_acc[None] = 0
    decay_count_acc[None] = 0
    step_counter[None] = 0
    flash_count[None] = 0
    for i in range(8):
        stats[i] = 0.0
    for i in range(MAX_PARTICLES):
        alive[i] = 0
        trail_head[i] = 0
        trail_count[i] = 0


def init_simulation():
    _clear_all()
    cached_stats["ke"] = 0.0
    cached_stats["mom"] = 0.0
    cached_stats["collisions"] = 0
    cached_stats["decays"] = 0
    cached_stats["step"] = 0
    cached_stats["particles"] = 0
    cached_stats["flash_rc"] = 0


def add_particle(position, velocity, particle_type):
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
    trail_head[idx] = 0
    trail_count[idx] = 0
    num_active[None] = n + 1
    return idx


@ti.kernel
def compute_forces(coulomb_k: ti.f32, gravity_g: ti.f32,
                   bx: ti.f32, by: ti.f32, bz: ti.f32):
    n = num_active[None]
    mag_field = ti.Vector([bx, by, bz])
    has_mag = mag_field.norm() > 1e-8
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

        if has_mag:
            f += qi * vel[i].cross(mag_field)

        force[i] = f


@ti.kernel
def integrate(dt: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        acc = force[i] / mass[i]
        vel[i] += acc * dt
        speed = vel[i].norm()
        if speed > MAX_VELOCITY:
            vel[i] *= MAX_VELOCITY / speed
        pos[i] += vel[i] * dt


@ti.kernel
def apply_boundaries_reflect(bound: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        for d in ti.static(range(3)):
            if pos[i][d] > bound:
                pos[i][d] = bound
                vel[i][d] = -vel[i][d] * 0.9
            elif pos[i][d] < -bound:
                pos[i][d] = -bound
                vel[i][d] = -vel[i][d] * 0.9


@ti.kernel
def apply_boundaries_periodic(bound: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        for d in ti.static(range(3)):
            if pos[i][d] > bound:
                pos[i][d] -= 2.0 * bound
            elif pos[i][d] < -bound:
                pos[i][d] += 2.0 * bound


@ti.kernel
def detect_collisions():
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
                pos[i] -= 0.5 * overlap * normal
                pos[j] += 0.5 * overlap * normal

                rel_vel = vel[i] - vel[j]
                vel_along_normal = rel_vel.dot(normal)

                if vel_along_normal > 0:
                    total_mass = mass[i] + mass[j]
                    restitution = ti.cast(COLLISION_RESTITUTION, ti.f32)
                    impulse = (1.0 + restitution) * vel_along_normal / total_mass
                    vel[i] -= impulse * mass[j] * normal
                    vel[j] += impulse * mass[i] * normal
                    ti.atomic_add(collision_count_acc[None], 1)

                    fidx = ti.atomic_add(flash_count[None], 1)
                    if fidx < MAX_FLASHES:
                        flash_render_pos[fidx] = (pos[i] + pos[j]) * 0.5
                        c1 = type_color[ptype[i]]
                        c2 = type_color[ptype[j]]
                        flash_render_color[fidx] = (c1 + c2) * 0.25
                        flash_life[fidx] = 0.6


@ti.kernel
def monte_carlo_decay(dt: ti.f32):
    n = num_active[None]
    for i in range(n):
        if alive[i] == 0:
            continue
        pt = ptype[i]
        dp = decay_prob[i]
        if dp <= 0.0:
            continue
        nc = num_channels[pt]
        if nc == 0:
            continue
        if ti.random(ti.f32) < dp * dt * 100.0:
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
    new_count = 0
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
            idx = ti.atomic_add(_compact_count[None], 1)
            _compact_src[idx] = i
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
def _compute_stats():
    n = num_active[None]
    ke = ti.cast(0.0, ti.f32)
    mx = ti.cast(0.0, ti.f32)
    my = ti.cast(0.0, ti.f32)
    mz = ti.cast(0.0, ti.f32)
    for i in range(n):
        if alive[i] == 0:
            continue
        speed_sq = vel[i].norm_sqr()
        ti.atomic_add(ke, 0.5 * mass[i] * speed_sq)
        p = mass[i] * vel[i]
        ti.atomic_add(mx, p[0])
        ti.atomic_add(my, p[1])
        ti.atomic_add(mz, p[2])
    stats[0] = ke
    stats[1] = mx
    stats[2] = my
    stats[3] = mz
    stats[4] = ti.cast(collision_count_acc[None], ti.f32)
    stats[5] = ti.cast(decay_count_acc[None], ti.f32)
    stats[6] = ti.cast(step_counter[None], ti.f32)
    stats[7] = ti.cast(n, ti.f32)


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
            render_color[idx] = ti.min(base_color + glow, 1.0)


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


def step(dt, coulomb_k=COULOMB_K, gravity_g=GRAVITY_G,
         mag_field=(0.0, 0.0, 0.0), boundary_mode="reflect",
         boundary_size=BOUNDARY_SIZE):
    compute_forces(coulomb_k, gravity_g, mag_field[0], mag_field[1], mag_field[2])
    integrate(dt)

    if boundary_mode == "reflect":
        apply_boundaries_reflect(boundary_size)
    elif boundary_mode == "periodic":
        apply_boundaries_periodic(boundary_size)

    detect_collisions()
    monte_carlo_decay(dt)
    _apply_spawn_queue()
    _finalize_spawn()
    record_trails()
    step_counter[None] += 1


def do_maintenance(dt):
    _update_flashes_and_compact(dt)
    _check_and_compact()
    if _needs_compact[None]:
        _do_compact(_compact_count[None])


def refresh_stats():
    _compute_stats()
    s = stats.to_numpy()
    cached_stats["ke"] = float(s[0])
    mom_sq = s[1]**2 + s[2]**2 + s[3]**2
    cached_stats["mom"] = float(mom_sq**0.5)
    cached_stats["collisions"] = int(s[4])
    cached_stats["decays"] = int(s[5])
    cached_stats["step"] = int(s[6])
    cached_stats["particles"] = int(s[7])
    cached_stats["flash_rc"] = flash_render_count[None]


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
    print(f"Exported {n} particles to {filepath}")
