import taichi as ti
import random
import time
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE,
    CAMERA_POS, CAMERA_LOOKAT, CAMERA_FOV,
    BASE_PARTICLE_RADIUS, PARTICLE_RADIUS_SCALE,
    PARTICLE_TYPES, TRAIL_LENGTH, MAX_PARTICLES,
    DT, SUBSTEPS, COULOMB_K, GRAVITY_G, MAGNETIC_FIELD,
    BOUNDARY_MODE, BOUNDARY_SIZE,
)
import simulation as sim


class Renderer:
    def __init__(self):
        self.window = ti.ui.Window(
            WINDOW_TITLE, (WINDOW_WIDTH, WINDOW_HEIGHT), vsync=True,
        )
        self.canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.camera = ti.ui.Camera()
        self.camera.position(*CAMERA_POS)
        self.camera.lookat(*CAMERA_LOOKAT)
        self.camera.fov(CAMERA_FOV)

        self.gui = self.window.get_gui()

        self.paused = False
        self.show_trails = True
        self.show_flashes = True
        self.dt = DT
        self.substeps = SUBSTEPS
        self.coulomb_k = COULOMB_K
        self.gravity_g = GRAVITY_G
        self.mag_x = MAGNETIC_FIELD[0]
        self.mag_y = MAGNETIC_FIELD[1]
        self.mag_z = MAGNETIC_FIELD[2]
        self.boundary_mode_idx = 0 if BOUNDARY_MODE == "reflect" else (1 if BOUNDARY_MODE == "periodic" else 2)
        self.boundary_size = BOUNDARY_SIZE
        self.spawn_type = 0
        self.spawn_mass_mult = 1.0
        self.spawn_charge_mult = 1.0
        self.spawn_speed = 3.0
        self.particle_size = BASE_PARTICLE_RADIUS
        self.trail_width = 1.5

        self.boundary_modes = ["reflect", "periodic", "none"]

        self.last_time = time.time()
        self.fps = 0.0
        self.frame_count = 0

    def handle_input(self):
        while self.window.get_event(ti.ui.PRESS):
            key = self.window.event.key
            if key == ti.ui.ESCAPE:
                self.window.running = False
            elif key == ti.ui.SPACE:
                self.paused = not self.paused
            elif key == 'r':
                self._reset_sim()
            elif key == 'c':
                self._trigger_collision_demo()
            elif key == 't':
                self.show_trails = not self.show_trails
            elif key == 'f':
                self.show_flashes = not self.show_flashes
            elif key == 'e':
                sim.export_state(f"state_{int(time.time())}.h5")

    def _reset_sim(self):
        sim.init_simulation()
        self._setup_demo()

    def _trigger_collision_demo(self):
        sim.add_particle((-5.0, 0.0, 0.0), (4.0, 0.1, 0.0), 7)
        sim.add_particle((5.0, 0.0, 0.0), (-4.0, -0.1, 0.0), 7)

    def _setup_demo(self):
        sim.add_particle((-3.5, 0.0, 0.0), (3.0, 0.3, 0.0), 7)
        sim.add_particle((3.5, 0.0, 0.0), (-3.0, -0.3, 0.0), 7)
        sim.add_particle((0.0, 3.5, 0.0), (-1.2, -1.8, 0.0), 0)
        sim.add_particle((0.0, -3.5, 0.0), (1.2, 1.8, 0.0), 0)
        sim.add_particle((3.0, 3.0, 0.0), (-2.0, -1.0, 0.5), 2)
        sim.add_particle((-3.0, -3.0, 0.0), (2.0, 1.0, -0.5), 3)
        sim.add_particle((1.5, -2.0, 1.0), (-0.8, 1.5, -0.4), 4)
        sim.add_particle((-1.5, 2.0, -1.0), (0.8, -1.5, 0.4), 5)
        sim.add_particle((4.0, 1.0, 0.5), (-1.5, -0.5, 0.0), 1)
        sim.add_particle((-4.0, -1.0, -0.5), (1.5, 0.5, 0.0), 9)

    def draw_gui(self):
        bmode = self.boundary_modes[self.boundary_mode_idx]
        st = sim.cached_stats

        with self.gui.sub_window("Simulation", 0.005, 0.005, 0.22, 0.62) as w:
            w.text("-- Physics --")
            self.dt = w.slider_float("Timestep", self.dt, 0.0001, 0.02)
            self.substeps = w.slider_int("Substeps", self.substeps, 1, 10)
            self.coulomb_k = w.slider_float("Coulomb K", self.coulomb_k, 0.0, 200.0)
            self.gravity_g = w.slider_float("Gravity G", self.gravity_g, 0.0, 80.0)
            w.text("")
            w.text("-- Magnetic Field --")
            self.mag_x = w.slider_float("B_x", self.mag_x, -20.0, 20.0)
            self.mag_y = w.slider_float("B_y", self.mag_y, -20.0, 20.0)
            self.mag_z = w.slider_float("B_z", self.mag_z, -20.0, 20.0)
            w.text("")
            w.text("-- Boundary --")
            self.boundary_mode_idx = w.slider_int("Mode", self.boundary_mode_idx, 0, 2)
            w.text(f"  [{bmode}]")
            self.boundary_size = w.slider_float("Size", self.boundary_size, 3.0, 30.0)
            w.text("")
            w.text("-- Visuals --")
            self.particle_size = w.slider_float("P.Size", self.particle_size, 0.01, 0.3)
            self.trail_width = w.slider_float("Trail W", self.trail_width, 0.5, 5.0)

        type_names = [PARTICLE_TYPES[i]["name"] for i in sorted(PARTICLE_TYPES.keys())]
        with self.gui.sub_window("Spawner", 0.005, 0.64, 0.22, 0.35) as w:
            w.text("-- Spawn Particle --")
            self.spawn_type = w.slider_int("Type", self.spawn_type, 0, len(type_names) - 1)
            w.text(f"  [{type_names[self.spawn_type]}]")
            self.spawn_mass_mult = w.slider_float("Mass x", self.spawn_mass_mult, 0.1, 10.0)
            self.spawn_charge_mult = w.slider_float("Charge x", self.spawn_charge_mult, -5.0, 5.0)
            self.spawn_speed = w.slider_float("Speed", self.spawn_speed, 0.0, 25.0)
            if w.button("Spawn at Origin"):
                vx = (random.random() - 0.5) * self.spawn_speed
                vy = (random.random() - 0.5) * self.spawn_speed
                vz = (random.random() - 0.5) * self.spawn_speed * 0.3
                idx = sim.add_particle((0.0, 0.0, 0.0), (vx, vy, vz), self.spawn_type)
                if idx >= 0:
                    sim.mass[idx] = float(sim.mass[idx]) * self.spawn_mass_mult
                    sim.charge[idx] = float(sim.charge[idx]) * self.spawn_charge_mult
            if w.button("Spawn Burst (10)"):
                for _ in range(10):
                    px = (random.random() - 0.5) * 2.0
                    py = (random.random() - 0.5) * 2.0
                    pz = (random.random() - 0.5) * 1.0
                    vx = (random.random() - 0.5) * self.spawn_speed
                    vy = (random.random() - 0.5) * self.spawn_speed
                    vz = (random.random() - 0.5) * self.spawn_speed * 0.3
                    sim.add_particle((px, py, pz), (vx, vy, vz), self.spawn_type)
            if w.button("Head-On Collision"):
                self._trigger_collision_demo()

        with self.gui.sub_window("Stats", 0.77, 0.005, 0.225, 0.30) as w:
            status = "PAUSED" if self.paused else "RUNNING"
            w.text(f"Status: {status}  FPS: {self.fps:.0f}")
            w.text(f"Particles: {st['particles']}")
            w.text(f"Step: {st['step']}")
            w.text(f"Collisions: {st['collisions']}")
            w.text(f"Decays: {st['decays']}")
            w.text(f"KE: {st['ke']:.2f}")
            w.text(f"|P|: {st['mom']:.3f}")

        with self.gui.sub_window("Keys", 0.77, 0.32, 0.225, 0.18) as w:
            w.text("SPACE  Pause/Resume")
            w.text("R  Reset")
            w.text("C  Head-on collision")
            w.text("T  Toggle trails")
            w.text("F  Toggle flashes")
            w.text("E  Export state (.h5)")
            w.text("RMB+drag  Orbit camera")

    def render(self):
        self.frame_count += 1

        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        if dt > 0:
            self.fps = self.fps * 0.9 + (1.0 / dt) * 0.1

        self.camera.track_user_inputs(
            self.window,
            movement_speed=0.08,
            yaw_speed=2.0,
            pitch_speed=2.0,
            hold_key=ti.ui.RMB,
        )
        self.scene.set_camera(self.camera)
        self.scene.ambient_light((0.15, 0.15, 0.2))
        self.scene.point_light(pos=(8, 8, 15), color=(1.0, 0.95, 0.9))
        self.scene.point_light(pos=(-8, -5, -10), color=(0.3, 0.3, 0.5))

        sim.prepare_render(self.particle_size, PARTICLE_RADIUS_SCALE)

        # Single GPU read for particle count
        rc = sim.render_count[None]
        if rc > 0:
            self.scene.particles(
                sim.render_pos,
                radius=self.particle_size,
                per_vertex_color=sim.render_color,
                index_count=rc,
            )

        if self.show_flashes:
            frc = sim.flash_render_count[None]
            if frc > 0:
                self.scene.particles(
                    sim.flash_render_pos,
                    radius=self.particle_size * 3.0,
                    per_vertex_color=sim.flash_render_color,
                    index_count=min(frc, sim.MAX_FLASHES),
                )

        if self.show_trails:
            tc = sim.trail_line_count[None]
            if tc > 0:
                num_verts = min(tc * 2, MAX_PARTICLES * TRAIL_LENGTH * 2)
                self.scene.lines(
                    sim.trail_vertices,
                    width=self.trail_width,
                    per_vertex_color=sim.trail_colors,
                    vertex_count=num_verts,
                )

        self.canvas.scene(self.scene)
        self.draw_gui()
        self.window.show()

    @property
    def running(self):
        return self.window.running

    @property
    def boundary_mode(self):
        return self.boundary_modes[self.boundary_mode_idx]

    @property
    def mag_field(self):
        return (self.mag_x, self.mag_y, self.mag_z)
