import taichi as ti
import random
import time
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE,
    CAMERA_POS, CAMERA_LOOKAT, CAMERA_FOV,
    BASE_PARTICLE_RADIUS, PARTICLE_RADIUS_SCALE,
    PARTICLE_TYPES, TRAIL_LENGTH, MAX_PARTICLES, NUM_TYPES,
    DT, SUBSTEPS, COULOMB_K, GRAVITY_G, MAGNETIC_FIELD, E_FIELD,
    STRONG_FORCE_K, STRONG_FORCE_RANGE, SPEED_OF_LIGHT,
    USE_RELATIVITY, SYNCHROTRON_COEFF, PAIR_CREATION_THRESHOLD,
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
        self.time_scale = 1.0
        self.coulomb_k = COULOMB_K
        self.gravity_g = GRAVITY_G
        self.mag_x, self.mag_y, self.mag_z = MAGNETIC_FIELD
        self.ex, self.ey, self.ez = E_FIELD
        self.strong_k = STRONG_FORCE_K
        self.strong_range = STRONG_FORCE_RANGE
        self.use_relativity = USE_RELATIVITY
        self.c_light = SPEED_OF_LIGHT
        self.synchro = SYNCHROTRON_COEFF
        self.pair_threshold = PAIR_CREATION_THRESHOLD
        self.boundary_mode_idx = 0 if BOUNDARY_MODE == "reflect" else (1 if BOUNDARY_MODE == "periodic" else 2)
        self.boundary_size = BOUNDARY_SIZE
        self.particle_size = BASE_PARTICLE_RADIUS
        self.trail_width = 1.5

        self.spawn_type = 0
        self.spawn_mass_mult = 1.0
        self.spawn_charge_mult = 1.0
        self.spawn_speed = 3.0

        self.gun_enabled = False
        self.gun_type = 0
        self.gun_speed = 5.0
        self.gun_spread = 0.3
        self.gun_rate = 10.0
        self.gun_px, self.gun_py, self.gun_pz = -8.0, 0.0, 0.0
        self.gun_dx, self.gun_dy, self.gun_dz = 1.0, 0.0, 0.0
        self._gun_accum = 0.0

        self.selected_particle = 0

        self.boundary_modes = ["reflect", "periodic", "none"]
        self.type_names = [PARTICLE_TYPES[i]["name"] for i in range(NUM_TYPES)]

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
            elif key == 'g':
                self.gun_enabled = not self.gun_enabled
            elif key == ti.ui.TAB:
                n = sim.cached_stats.get("particles", 1)
                self.selected_particle = (self.selected_particle + 1) % max(n, 1)
            elif key == 'p':
                idx = self.selected_particle
                if idx < sim.num_active[None]:
                    current = sim.frozen[idx]
                    sim.frozen[idx] = 0 if current else 1
            elif key == '1':
                self._preset_rutherford()
            elif key == '2':
                self._preset_cyclotron()
            elif key == '3':
                self._preset_gas()
            elif key == '4':
                self._preset_two_beam()

    def fire_gun(self, real_dt):
        if not self.gun_enabled:
            return
        self._gun_accum += real_dt * self.gun_rate
        while self._gun_accum >= 1.0:
            self._gun_accum -= 1.0
            dx = self.gun_dx + (random.random() - 0.5) * self.gun_spread
            dy = self.gun_dy + (random.random() - 0.5) * self.gun_spread
            dz = self.gun_dz + (random.random() - 0.5) * self.gun_spread
            mag = (dx*dx + dy*dy + dz*dz) ** 0.5
            if mag > 0:
                dx /= mag; dy /= mag; dz /= mag
            sim.add_particle(
                (self.gun_px, self.gun_py, self.gun_pz),
                (dx * self.gun_speed, dy * self.gun_speed, dz * self.gun_speed),
                self.gun_type,
            )

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

    def _preset_rutherford(self):
        sim.init_simulation()
        self.coulomb_k = 60.0
        self.gravity_g = 0.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.strong_k = 0.0
        sim.add_particle((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 7, is_frozen=True)
        for i in range(8):
            y = -3.0 + i * 0.8
            sim.add_particle((-8.0, y, 0.0), (5.0, 0.0, 0.0), 0)

    def _preset_cyclotron(self):
        sim.init_simulation()
        self.coulomb_k = 0.0
        self.gravity_g = 0.0
        self.mag_x = 0.0; self.mag_y = 0.0; self.mag_z = 8.0
        self.strong_k = 0.0
        for i in range(6):
            angle = i * 1.047
            import math
            vx = math.cos(angle) * 4.0
            vy = math.sin(angle) * 4.0
            sim.add_particle((0.0, 0.0, 0.0), (vx, vy, 0.0), i % 5)

    def _preset_gas(self):
        sim.init_simulation()
        self.coulomb_k = 5.0
        self.gravity_g = 2.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.boundary_size = 8.0
        for _ in range(60):
            tid = random.choice([0, 1, 2, 3, 8])
            px = random.uniform(-5, 5)
            py = random.uniform(-5, 5)
            pz = random.uniform(-3, 3)
            vx = random.uniform(-2, 2)
            vy = random.uniform(-2, 2)
            vz = random.uniform(-1, 1)
            sim.add_particle((px, py, pz), (vx, vy, vz), tid)

    def _preset_two_beam(self):
        sim.init_simulation()
        self.coulomb_k = 30.0
        self.gravity_g = 0.0
        self.gun_enabled = False
        for i in range(10):
            y = -2.0 + i * 0.4
            sim.add_particle((-7.0, y, 0.0), (6.0, 0.0, 0.0), 0)
            sim.add_particle((7.0, -y, 0.0), (-6.0, 0.0, 0.0), 0)

    def draw_gui(self):
        st = sim.cached_stats
        bmode = self.boundary_modes[self.boundary_mode_idx]

        with self.gui.sub_window("Physics", 0.003, 0.003, 0.20, 0.58) as w:
            self.dt = w.slider_float("Timestep", self.dt, 0.0001, 0.02)
            self.substeps = w.slider_int("Substeps", self.substeps, 1, 10)
            self.time_scale = w.slider_float("Time x", self.time_scale, 0.1, 10.0)
            self.coulomb_k = w.slider_float("Coulomb", self.coulomb_k, 0.0, 200.0)
            self.gravity_g = w.slider_float("Gravity", self.gravity_g, 0.0, 80.0)
            self.strong_k = w.slider_float("Strong F", self.strong_k, 0.0, 100.0)
            self.strong_range = w.slider_float("S.Range", self.strong_range, 0.1, 3.0)
            w.text("")
            w.text("-- Fields --")
            self.mag_x = w.slider_float("B_x", self.mag_x, -20.0, 20.0)
            self.mag_y = w.slider_float("B_y", self.mag_y, -20.0, 20.0)
            self.mag_z = w.slider_float("B_z", self.mag_z, -20.0, 20.0)
            self.ex = w.slider_float("E_x", self.ex, -20.0, 20.0)
            self.ey = w.slider_float("E_y", self.ey, -20.0, 20.0)
            self.ez = w.slider_float("E_z", self.ez, -20.0, 20.0)
            w.text("")
            rel_int = w.slider_int("Relativity", 1 if self.use_relativity else 0, 0, 1)
            self.use_relativity = rel_int == 1
            self.synchro = w.slider_float("Synchro", self.synchro, 0.0, 1.0)
            self.pair_threshold = w.slider_float("Pair Thr", self.pair_threshold, 1.0, 50.0)

        with self.gui.sub_window("Boundary", 0.003, 0.59, 0.20, 0.12) as w:
            self.boundary_mode_idx = w.slider_int("Mode", self.boundary_mode_idx, 0, 2)
            w.text(f"  [{bmode}]")
            self.boundary_size = w.slider_float("Size", self.boundary_size, 3.0, 30.0)
            self.particle_size = w.slider_float("P.Size", self.particle_size, 0.02, 0.3)
            self.trail_width = w.slider_float("Trail W", self.trail_width, 0.5, 5.0)

        with self.gui.sub_window("Spawn", 0.003, 0.72, 0.20, 0.27) as w:
            self.spawn_type = w.slider_int("Type", self.spawn_type, 0, NUM_TYPES - 1)
            w.text(f"  [{self.type_names[self.spawn_type]}]")
            self.spawn_speed = w.slider_float("Speed", self.spawn_speed, 0.0, 25.0)
            if w.button("Spawn 1"):
                vx = (random.random() - 0.5) * self.spawn_speed
                vy = (random.random() - 0.5) * self.spawn_speed
                vz = (random.random() - 0.5) * self.spawn_speed * 0.3
                sim.add_particle((0, 0, 0), (vx, vy, vz), self.spawn_type)
            if w.button("Burst 20"):
                for _ in range(20):
                    px = (random.random() - 0.5) * 3
                    py = (random.random() - 0.5) * 3
                    pz = (random.random() - 0.5) * 1
                    vx = (random.random() - 0.5) * self.spawn_speed
                    vy = (random.random() - 0.5) * self.spawn_speed
                    vz = (random.random() - 0.5) * self.spawn_speed * 0.3
                    sim.add_particle((px, py, pz), (vx, vy, vz), self.spawn_type)
            if w.button("Collision"):
                self._trigger_collision_demo()

        with self.gui.sub_window("Stats", 0.795, 0.003, 0.202, 0.38) as w:
            status = "PAUSED" if self.paused else "RUNNING"
            gun_str = "  GUN ON" if self.gun_enabled else ""
            w.text(f"{status}  FPS:{self.fps:.0f}{gun_str}")
            w.text(f"Particles: {st.get('particles',0)}  Step: {st.get('step',0)}")
            w.text(f"Collisions: {st.get('collisions',0)}")
            w.text(f"Decays: {st.get('decays',0)}")
            w.text(f"Annihilations: {st.get('annihilations',0)}")
            w.text(f"Pair creations: {st.get('pair_creations',0)}")
            w.text(f"Detector hits: {st.get('detector_hits',0)}")
            det_e = st.get('detector_energy', 0)
            det_h = max(st.get('detector_hits', 0), 1)
            w.text(f"Det avg E: {det_e/det_h:.2f}")
            w.text(f"KE: {st.get('ke',0):.2f}")
            w.text(f"|P|: {st.get('mom',0):.3f}")
            w.text(f"Avg speed: {st.get('avg_speed',0):.2f}")

        with self.gui.sub_window("Census", 0.795, 0.39, 0.202, 0.22) as w:
            for i in range(NUM_TYPES):
                cnt = st.get(f"type_{i}", 0)
                if cnt > 0:
                    w.text(f"{self.type_names[i]}: {cnt}")

        with self.gui.sub_window("Inspector", 0.795, 0.62, 0.202, 0.20) as w:
            w.text(f"Sel #{self.selected_particle} (TAB cycle, P pin)")
            sel_t = int(st.get('sel_type', 0))
            tn = self.type_names[sel_t] if 0 <= sel_t < NUM_TYPES and st.get('particles', 0) > 0 else "---"
            frz = "FROZEN" if st.get('sel_frozen', 0) else ""
            w.text(f"Type: {tn}  {frz}")
            w.text(f"m={st.get('sel_mass',0):.3f}  q={st.get('sel_charge',0):.1f}")
            w.text(f"pos: ({st.get('sel_px',0):.1f},{st.get('sel_py',0):.1f},{st.get('sel_pz',0):.1f})")
            w.text(f"spd: {st.get('sel_speed',0):.2f}  KE: {st.get('sel_ke',0):.3f}")

        with self.gui.sub_window("Gun/Presets", 0.795, 0.83, 0.202, 0.165) as w:
            gun_int = w.slider_int("Gun", 1 if self.gun_enabled else 0, 0, 1)
            self.gun_enabled = gun_int == 1
            self.gun_type = w.slider_int("G.Type", self.gun_type, 0, NUM_TYPES - 1)
            self.gun_speed = w.slider_float("G.Spd", self.gun_speed, 1.0, 20.0)
            self.gun_rate = w.slider_float("G.Rate", self.gun_rate, 1.0, 60.0)
            w.text("Presets: 1=Ruth 2=Cycl 3=Gas 4=Beam")

    def render(self):
        self.frame_count += 1
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        if dt > 0:
            self.fps = self.fps * 0.9 + (1.0 / dt) * 0.1

        self.camera.track_user_inputs(
            self.window, movement_speed=0.08,
            yaw_speed=2.0, pitch_speed=2.0, hold_key=ti.ui.RMB,
        )
        self.scene.set_camera(self.camera)
        self.scene.ambient_light((0.15, 0.15, 0.2))
        self.scene.point_light(pos=(8, 8, 15), color=(1.0, 0.95, 0.9))
        self.scene.point_light(pos=(-8, -5, -10), color=(0.3, 0.3, 0.5))

        sim.prepare_render(self.particle_size, PARTICLE_RADIUS_SCALE)

        rc = sim.render_count[None]
        if rc > 0:
            self.scene.particles(
                sim.render_pos, radius=self.particle_size,
                per_vertex_color=sim.render_color, index_count=rc,
            )

        if self.show_flashes:
            frc = sim.flash_render_count[None]
            if frc > 0:
                self.scene.particles(
                    sim.flash_render_pos, radius=self.particle_size * 3.0,
                    per_vertex_color=sim.flash_render_color,
                    index_count=min(frc, sim.MAX_FLASHES),
                )

        if self.show_trails:
            tc = sim.trail_line_count[None]
            if tc > 0:
                nv = min(tc * 2, MAX_PARTICLES * TRAIL_LENGTH * 2)
                self.scene.lines(
                    sim.trail_vertices, width=self.trail_width,
                    per_vertex_color=sim.trail_colors, vertex_count=nv,
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

    @property
    def e_field(self):
        return (self.ex, self.ey, self.ez)
