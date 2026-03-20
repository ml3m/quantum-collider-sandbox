"""Taichi UI window, camera, particle rendering, trails, and ImGui controls."""

import json
import math
import random
import time
from pathlib import Path

import taichi as ti

from . import config
from . import simulation as sim
from .config import (
    BACKGROUND_COLOR,
    BASE_PARTICLE_RADIUS,
    BH_MASS,
    BOUNDARY_MODE,
    BOUNDARY_SIZE,
    CAMERA_FOV,
    CAMERA_LOOKAT,
    CAMERA_POS,
    COULOMB_K,
    DT,
    E_FIELD,
    GRAVITY_G,
    MAGNETIC_FIELD,
    MAX_PARTICLES,
    NUM_TYPES,
    PAIR_CREATION_THRESHOLD,
    PARTICLE_RADIUS_SCALE,
    SPEED_OF_LIGHT,
    STRONG_FORCE_K,
    STRONG_FORCE_RANGE,
    SUBSTEPS,
    SYNCHROTRON_COEFF,
    TRAIL_LENGTH,
    TRAIL_WIDTH,
    USE_RELATIVITY,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from .pdg_table import (
    ANTIPROTON,
    DELTA_PP,
    ELECTRON,
    K_MINUS,
    K_PLUS,
    MUON_MINUS,
    MUON_PLUS,
    NEUTRON,
    PHOTON,
    PI_MINUS,
    PI_PLUS,
    PI_ZERO,
    POSITRON,
    PROTON,
)
from .pdg_table import (
    PARTICLES as PDG_PARTICLES,
)


class Renderer:
    """Main rendering and UI controller for the particle simulation."""

    def __init__(self):
        self.window = ti.ui.Window(
            WINDOW_TITLE,
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            vsync=True,
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
        self.show_photons = True
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
        if BOUNDARY_MODE == "reflect":
            self.boundary_mode_idx = 0
        elif BOUNDARY_MODE == "periodic":
            self.boundary_mode_idx = 1
        else:
            self.boundary_mode_idx = 2
        self.boundary_size = BOUNDARY_SIZE
        self.particle_size = BASE_PARTICLE_RADIUS
        self.trail_width = TRAIL_WIDTH

        self.spawn_type = PROTON
        self.spawn_mass_mult = 1.0
        self.spawn_charge_mult = 1.0
        self.spawn_speed = 3.0

        self.gun_enabled = False
        self.gun_type = PROTON
        self.gun_speed = 5.0
        self.gun_spread = 0.3
        self.gun_rate = 10.0
        self.gun_px, self.gun_py, self.gun_pz = -8.0, 0.0, 0.0
        self.gun_dx, self.gun_dy, self.gun_dz = 1.0, 0.0, 0.0
        self._gun_accum = 0.0

        self.selected_particle = 0

        self.bh_enabled = False
        self.bh_mass = BH_MASS
        self.bh_x, self.bh_y, self.bh_z = 0.0, 0.0, 0.0
        self._bh_ring_dirty = True
        self._disk_initialized = False

        # Particle count control
        self.particle_count_target = 1000
        self._particle_count_prev = self.particle_count_target
        self._load_particle_count_config()

        sim.init_bg_stars()

        self.boundary_modes = ["reflect", "periodic", "none"]

        self.type_names = []
        for i in range(NUM_TYPES):
            p = PDG_PARTICLES.get(i)
            self.type_names.append(p["name"] if p else f"rsv_{i}")

        self._spawn_ids = sorted(PDG_PARTICLES.keys())

        self.last_time = time.time()
        self.fps = 0.0
        self.frame_count = 0
        self._preset_keys_prev = [False] * 11
        self._preset_idx = 0

    def _get_particle_config_path(self) -> Path:
        """Get path to particle count config file."""
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / ".particle_config.json"

    def _load_particle_count_config(self) -> None:
        """Load saved particle count preference from config file."""
        config_path = self._get_particle_config_path()
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.particle_count_target = max(
                        1, min(data.get("particle_count", 1000), 50000)
                    )
            except (OSError, json.JSONDecodeError):
                self.particle_count_target = 1000
        self._particle_count_prev = self.particle_count_target

    def _save_particle_count_config(self) -> None:
        """Save particle count preference to config file."""
        config_path = self._get_particle_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"particle_count": self.particle_count_target}, f)
        except OSError:
            pass  # Silently fail if can't write config

    def _update_particle_count(self) -> None:
        """Apply particle count changes if slider was modified."""
        if self.particle_count_target != self._particle_count_prev:
            sim.set_particle_count(self.particle_count_target)
            self._particle_count_prev = self.particle_count_target
            self._save_particle_count_config()

    def _presets(self):
        """Return list of preset methods (0-9). Key 1=Default, 2=Rutherford, ..., 0=N-body."""
        return [
            self._preset_default,
            self._preset_rutherford,
            self._preset_cyclotron,
            self._preset_gas,
            self._preset_two_beam,
            self._preset_black_hole,
            self._preset_lhc_pp,
            self._preset_ee_annihilation,
            self._preset_physics_playground,
            self._preset_virial_cluster,
        ]

    def handle_input(self) -> None:
        """Process keyboard input events."""
        while self.window.get_event(ti.ui.PRESS):
            key = self.window.event.key
            if key == ti.ui.ESCAPE:
                self.window.running = False
            elif key == ti.ui.SPACE:
                self.paused = not self.paused
            elif key == "r":
                self._reset_sim()
            elif key == "c":
                self._trigger_collision_demo()
            elif key == "t":
                self.show_trails = not self.show_trails
            elif key == "f":
                self.show_flashes = not self.show_flashes
            elif key == "y":
                self.show_photons = not self.show_photons
            elif key == "e":
                out_dir = config.EXPORT_DIR
                out_dir.mkdir(parents=True, exist_ok=True)
                sim.export_state(str(out_dir / f"state_{int(time.time())}.h5"))
            elif key == "g":
                self.gun_enabled = not self.gun_enabled
            elif key == ti.ui.TAB:
                n = sim.cached_stats.get("particles", 1)
                self.selected_particle = (self.selected_particle + 1) % max(n, 1)
            elif key == "p":
                idx = self.selected_particle
                if idx < sim.num_active[None]:
                    current = sim.frozen[idx]
                    sim.frozen[idx] = 0 if current else 1
            elif key == "b":
                self.bh_enabled = not self.bh_enabled
                self._bh_ring_dirty = True
            elif key in "1234567890" or (isinstance(key, int) and 48 <= key <= 57):
                k = chr(key) if isinstance(key, int) else key
                idx = ord(k) - ord("1") if k != "0" else 9
                if 0 <= idx <= 9:
                    self._preset_idx = idx
                    self._presets()[idx]()

        # Fallback: number keys via is_pressed (works when get_event misses them)
        for i in range(1, 11):
            k = str(i) if i < 10 else "0"
            if self.window.is_pressed(k):
                if not self._preset_keys_prev[i]:
                    self._preset_idx = i - 1
                    self._presets()[i - 1]()
                self._preset_keys_prev[i] = True
            else:
                self._preset_keys_prev[i] = False

    def fire_gun(self, real_dt: float) -> None:
        """Spawn particles from the gun at configured rate."""
        if not self.gun_enabled:
            return
        self._gun_accum += real_dt * self.gun_rate
        while self._gun_accum >= 1.0:
            self._gun_accum -= 1.0
            dx = self.gun_dx + (random.random() - 0.5) * self.gun_spread
            dy = self.gun_dy + (random.random() - 0.5) * self.gun_spread
            dz = self.gun_dz + (random.random() - 0.5) * self.gun_spread
            mag = (dx * dx + dy * dy + dz * dz) ** 0.5
            if mag > 0:
                dx /= mag
                dy /= mag
                dz /= mag
            sim.add_particle(
                (self.gun_px, self.gun_py, self.gun_pz),
                (dx * self.gun_speed, dy * self.gun_speed, dz * self.gun_speed),
                self.gun_type,
            )

    def _reset_sim(self):
        """Reset to the currently selected preset."""
        self._presets()[self._preset_idx]()

    def _preset_default(self):
        """Default demo: mixed particles (initial state on startup)."""
        sim.init_simulation()
        self._setup_demo()

    def _trigger_collision_demo(self):
        sim.add_particle((-5.0, 0.0, 0.0), (6.0, 0.1, 0.0), PROTON)
        sim.add_particle((5.0, 0.0, 0.0), (-6.0, -0.1, 0.0), ANTIPROTON)

    def _setup_demo(self):
        # Projectiles that arc under gravity (vy initial upward)
        sim.add_particle((-4.0, -2.0, 0.0), (3.0, 5.0, 0.2), PROTON)
        sim.add_particle((4.0, -2.0, 0.0), (-3.0, 5.0, -0.2), ANTIPROTON)
        sim.add_particle((-2.0, -3.0, 1.0), (2.0, 4.0, 0.0), PROTON)
        sim.add_particle((2.0, -3.0, -1.0), (-2.0, 4.0, 0.0), NEUTRON)
        # Particles affected by E-field (Ey>0) and B-field (Bz) - curved trajectories
        sim.add_particle((0.0, 2.0, 0.0), (2.0, 0.0, 1.0), PI_PLUS)
        sim.add_particle((0.0, -2.0, 0.0), (-2.0, 0.0, -1.0), PI_MINUS)
        sim.add_particle((-3.0, 0.0, 2.0), (1.0, 3.0, -0.5), K_PLUS)
        sim.add_particle((3.0, 0.0, -2.0), (-1.0, -3.0, 0.5), MUON_MINUS)
        sim.add_particle((-1.0, 1.0, 0.0), (4.0, 2.0, 0.0), ELECTRON)
        sim.add_particle((1.0, -1.0, 0.0), (-4.0, -2.0, 0.0), POSITRON)

    def _preset_rutherford(self):
        sim.init_simulation()
        self.coulomb_k = 60.0
        self.gravity_g = 0.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.strong_k = 0.0
        sim.add_particle((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), DELTA_PP, is_frozen=True)
        for i in range(8):
            y = -3.0 + i * 0.8
            sim.add_particle((-8.0, y, 0.0), (5.0, 0.0, 0.0), PROTON)

    def _preset_cyclotron(self):
        sim.init_simulation()
        self.coulomb_k = 0.0
        self.gravity_g = 0.0
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 8.0
        self.strong_k = 0.0
        types = [ELECTRON, POSITRON, MUON_MINUS, MUON_PLUS, PI_PLUS, PI_MINUS]
        for i in range(6):
            angle = i * 1.047
            vx = math.cos(angle) * 4.0
            vy = math.sin(angle) * 4.0
            sim.add_particle((0.0, 0.0, 0.0), (vx, vy, 0.0), types[i % len(types)])

    def _preset_gas(self):
        sim.init_simulation()
        self.coulomb_k = 5.0
        self.gravity_g = 2.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.boundary_size = 8.0
        types = [PROTON, ELECTRON, PI_PLUS, PI_MINUS, NEUTRON]
        for _ in range(60):
            tid = random.choice(types)
            px = random.uniform(-5, 5)
            py = random.uniform(-5, 5)
            pz = random.uniform(-3, 3)
            vx = random.uniform(-2, 2)
            vy = random.uniform(-2, 2)
            vz = random.uniform(-1, 1)
            sim.add_particle((px, py, pz), (vx, vy, vz), tid)

    def _preset_black_hole(self):
        sim.init_simulation()
        self.bh_enabled = True
        self.bh_mass = 300.0
        self.bh_x, self.bh_y, self.bh_z = 0.0, 0.0, 0.0
        self._bh_ring_dirty = True
        self._disk_initialized = False
        self.coulomb_k = 0.0
        self.gravity_g = 0.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.strong_k = 0.0
        self.use_relativity = True
        bh_rs = 2.0 * self.bh_mass / (self.c_light * self.c_light)
        r_isco = 3.0 * bh_rs
        r_orbit = r_isco * 1.5
        orbit_types = [
            PROTON,
            ELECTRON,
            PI_PLUS,
            PI_MINUS,
            K_PLUS,
            MUON_MINUS,
            NEUTRON,
            POSITRON,
            K_MINUS,
            MUON_PLUS,
            PHOTON,
            PI_ZERO,
        ]
        for i in range(12):
            angle = i * math.pi * 2.0 / 12
            px = r_orbit * math.cos(angle)
            pz = r_orbit * math.sin(angle)
            v_circ = math.sqrt(self.bh_mass * r_orbit) / (r_orbit - bh_rs)
            vx = -v_circ * math.sin(angle)
            vz = v_circ * math.cos(angle)
            sim.add_particle((px, 0.0, pz), (vx, 0.0, vz), orbit_types[i])
        far_types = [PROTON, ELECTRON, PI_PLUS, K_PLUS, NEUTRON, PI_MINUS, MUON_MINUS, POSITRON]
        for i in range(8):
            angle = i * math.pi * 2.0 / 8
            r_far = r_orbit * 2.5
            px = r_far * math.cos(angle)
            pz = r_far * math.sin(angle)
            v_circ = math.sqrt(self.bh_mass * r_far) / (r_far - bh_rs)
            vx = -v_circ * math.sin(angle) * 0.7
            vz = v_circ * math.cos(angle) * 0.7
            sim.add_particle((px, 0.0, pz), (vx, 0.0, vz), far_types[i])

    def _preset_two_beam(self):
        sim.init_simulation()
        self.coulomb_k = 30.0
        self.gravity_g = 0.0
        self.gun_enabled = False
        for i in range(10):
            y = -2.0 + i * 0.4
            sim.add_particle((-7.0, y, 0.0), (6.0, 0.0, 0.0), PROTON)
            sim.add_particle((7.0, -y, 0.0), (-6.0, 0.0, 0.0), PROTON)

    def _preset_lhc_pp(self):
        """LHC-style proton-proton head-on collision."""
        sim.init_simulation()
        self.coulomb_k = 5.0
        self.gravity_g = 0.0
        self.strong_k = 20.0
        self.strong_range = 1.5
        self.use_relativity = True
        self.mag_x = self.mag_y = self.mag_z = 0.0
        speed = self.c_light * 0.85
        for i in range(6):
            y = -1.0 + i * 0.4
            sim.add_particle((-6.0, y, 0.0), (speed, 0.0, 0.0), PROTON)
            sim.add_particle((6.0, -y, 0.0), (-speed, 0.0, 0.0), PROTON)

    def _preset_ee_annihilation(self):
        """Electron-positron annihilation."""
        sim.init_simulation()
        self.coulomb_k = 15.0
        self.gravity_g = 0.0
        self.strong_k = 0.0
        self.use_relativity = True
        self.mag_x = self.mag_y = self.mag_z = 0.0
        speed = self.c_light * 0.7
        for i in range(5):
            y = -1.0 + i * 0.5
            sim.add_particle((-6.0, y, 0.0), (speed, 0.0, 0.0), ELECTRON)
            sim.add_particle((6.0, -y, 0.0), (-speed, 0.0, 0.0), POSITRON)

    def _preset_physics_playground(self):
        """Gravity + E-field + B-field + relativity for visible physics effects."""
        sim.init_simulation()
        self.coulomb_k = 25.0
        self.gravity_g = 6.0
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 5.0
        self.ex = 0.0
        self.ey = 2.0
        self.ez = 0.0
        self.strong_k = 0.0
        self.use_relativity = True
        self.synchro = 0.02
        self.boundary_size = 10.0
        for i in range(12):
            angle = i * math.pi * 2.0 / 12
            px = 4.0 * math.cos(angle)
            pz = 4.0 * math.sin(angle)
            vx = -2.0 * math.sin(angle) + 0.5
            vz = 2.0 * math.cos(angle)
            vy = 3.0 + (i % 3) * 1.5
            sim.add_particle((px, -2.0, pz), (vx, vy, vz), [PROTON, ELECTRON, PI_PLUS][i % 3])

    def _preset_virial_cluster(self):
        """N-body virial cluster: ~80 particles in a gravitationally bound sphere.
        Orbits, collisions, and slow evaporation. Pure gravity, no E/B."""
        sim.init_simulation()
        self.coulomb_k = 0.0
        self.gravity_g = 18.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.ex = self.ey = self.ez = 0.0
        self.strong_k = 0.0
        self.use_relativity = False
        self.boundary_size = 18.0
        self.boundary_mode_idx = 0  # reflect

        n = 80
        radius = 4.5
        v_rms = 2.2  # virial: 2*KE ~ |PE| gives roughly bound orbits

        types = [PROTON, NEUTRON, PI_PLUS, PI_MINUS, K_PLUS, MUON_MINUS]
        for i in range(n):
            # Uniform random in sphere (rejection sampling)
            while True:
                x = (random.random() * 2 - 1) * radius
                y = (random.random() * 2 - 1) * radius
                z = (random.random() * 2 - 1) * radius
                if x * x + y * y + z * z <= radius * radius:
                    break
            # Random velocity direction, magnitude from virial
            theta = random.random() * 2 * math.pi
            phi = math.acos(2 * random.random() - 1)
            speed = v_rms * (0.6 + 0.8 * random.random())
            vx = speed * math.sin(phi) * math.cos(theta)
            vy = speed * math.sin(phi) * math.sin(theta)
            vz = speed * math.cos(phi)
            sim.add_particle((x, y, z), (vx, vy, vz), types[i % len(types)])

    def _preset_minimal(self):
        """Minimal: 2 particles head-on."""
        sim.init_simulation()
        self.coulomb_k = 20.0
        self.gravity_g = 0.0
        self.mag_x = self.mag_y = self.mag_z = 0.0
        self.ex = self.ey = self.ez = 0.0
        self.strong_k = 0.0
        self.use_relativity = False
        sim.add_particle((-4.0, 0.0, 0.0), (3.0, 0.0, 0.0), PROTON)
        sim.add_particle((4.0, 0.0, 0.0), (-3.0, 0.0, 0.0), PROTON)

    def draw_gui(self) -> None:
        """Draw ImGui control panels. Uses normalized coords (0-1) per Taichi API so
        panels stay on left/right edges when resizing (imgui.ini deleted at startup)."""
        st = sim.cached_stats
        bmode = self.boundary_modes[self.boundary_mode_idx]

        # Layout: x,y,width,height all 0-1 relative to full window (Taichi sub_window API)
        # Left column: x=0 (flush left). Right column: x=1-W, width W (flush right)
        left_panel_width, right_panel_width = 0.20, 0.18  # left/right panel widths
        right_column_x = 1.0 - right_panel_width  # right column x = flush right

        with self.gui.sub_window("Physics", 0.0, 0.0, left_panel_width, 0.58) as w:
            self.dt = w.slider_float("Timestep", self.dt, 0.00001, 0.02)
            self.substeps = w.slider_int("Substeps", self.substeps, 1, 10)
            self.time_scale = w.slider_float("Time x", self.time_scale, 0.01, 10.0)
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
            integrator_idx = 1 if config.INTEGRATOR == "leapfrog" else 0
            integrator_idx = w.slider_int("Integrator", integrator_idx, 0, 1)
            config.INTEGRATOR = "leapfrog" if integrator_idx == 1 else "euler"
            w.text("  0=Euler 1=Leapfrog")

        with self.gui.sub_window("Boundary", 0.0, 0.59, left_panel_width, 0.14) as w:
            self.boundary_mode_idx = w.slider_int("Mode", self.boundary_mode_idx, 0, 2)
            w.text(f"  [{bmode}]")
            self.boundary_size = w.slider_float("Size", self.boundary_size, 3.0, 30.0)
            self.particle_size = w.slider_float("P.Size", self.particle_size, 0.02, 0.3)
            self.trail_width = w.slider_float("Trail W", self.trail_width, 0.5, 5.0)
            if w.button("Photons ON" if self.show_photons else "Photons OFF"):
                self.show_photons = not self.show_photons
            w.text("  (Y key)")

        with self.gui.sub_window("Black Hole", 0.0, 0.72, left_panel_width, 0.17) as w:
            bh_int = w.slider_int("BH On", 1 if self.bh_enabled else 0, 0, 1)
            old_bh = self.bh_enabled
            self.bh_enabled = bh_int == 1
            old_mass = self.bh_mass
            self.bh_mass = w.slider_float("BH Mass", self.bh_mass, 10.0, 2000.0)
            old_x, old_y, old_z = self.bh_x, self.bh_y, self.bh_z
            self.bh_x = w.slider_float("BH X", self.bh_x, -15.0, 15.0)
            self.bh_y = w.slider_float("BH Y", self.bh_y, -15.0, 15.0)
            bh_rs = 2.0 * self.bh_mass / (self.c_light * self.c_light)
            r_isco = 3.0 * bh_rs
            w.text(f"r_s={bh_rs:.3f}  ISCO={r_isco:.3f}")
            w.text(f"Captures: {st.get('bh_captures', 0)}")
            if (
                self.bh_enabled != old_bh
                or self.bh_mass != old_mass
                or self.bh_x != old_x
                or self.bh_y != old_y
                or self.bh_z != old_z
            ):
                self._bh_ring_dirty = True
                self._disk_initialized = False

        with self.gui.sub_window("Spawn & Particles", 0.0, 0.75, left_panel_width, 0.22) as w:
            # Particle count control
            self.particle_count_target = w.slider_int(
                "Part.Count", self.particle_count_target, 1, 50000
            )
            self._update_particle_count()
            current_n = sim.num_active[None]
            w.text(f"  Current: {current_n}")
            w.text("")

            # Spawn controls
            spawn_idx = (
                self._spawn_ids.index(self.spawn_type) if self.spawn_type in self._spawn_ids else 0
            )
            spawn_idx = w.slider_int("Type", spawn_idx, 0, len(self._spawn_ids) - 1)
            self.spawn_type = self._spawn_ids[spawn_idx]
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

        with self.gui.sub_window("Stats", right_column_x, 0.0, right_panel_width, 0.38) as w:
            status = "PAUSED" if self.paused else "RUNNING"
            gun_str = "  GUN ON" if self.gun_enabled else ""
            w.text(f"{status}  FPS:{self.fps:.0f}{gun_str}")
            w.text(f"Particles: {st.get('particles',0)}  Step: {st.get('step',0)}")
            w.text(f"Collisions: {st.get('collisions',0)}")
            w.text(f"Decays: {st.get('decays',0)}")
            w.text(f"Annihilations: {st.get('annihilations',0)}")
            w.text(f"Pair creations: {st.get('pair_creations',0)}")
            w.text(f"Detector hits: {st.get('detector_hits',0)}")
            det_e = st.get("detector_energy", 0)
            det_h = max(st.get("detector_hits", 0), 1)
            w.text(f"Det avg E: {det_e/det_h:.2f}")
            w.text(f"KE: {st.get('ke',0):.2f}")
            w.text(f"|P|: {st.get('mom',0):.3f}")
            w.text(f"Avg speed: {st.get('avg_speed',0):.2f}")

        with self.gui.sub_window("Census", right_column_x, 0.39, right_panel_width, 0.22) as w:
            for i in range(NUM_TYPES):
                cnt = st.get(f"type_{i}", 0)
                if cnt > 0:
                    w.text(f"{self.type_names[i]}: {cnt}")

        with self.gui.sub_window("Inspector", right_column_x, 0.62, right_panel_width, 0.20) as w:
            w.text(f"Sel #{self.selected_particle} (TAB cycle, P pin)")
            sel_t = int(st.get("sel_type", 0))
            has_particles = st.get("particles", 0) > 0
            in_range = 0 <= sel_t < NUM_TYPES
            tn = self.type_names[sel_t] if in_range and has_particles else "---"
            frz = "FROZEN" if st.get("sel_frozen", 0) else ""
            w.text(f"Type: {tn}  {frz}")
            w.text(f"m={st.get('sel_mass',0):.4f}  q={st.get('sel_charge',0):.0f}")
            px_val = st.get("sel_px", 0)
            py_val = st.get("sel_py", 0)
            pz_val = st.get("sel_pz", 0)
            w.text(f"pos: ({px_val:.1f},{py_val:.1f},{pz_val:.1f})")
            w.text(f"spd: {st.get('sel_speed',0):.2f}  KE: {st.get('sel_ke',0):.3f}")
            pdg_info = PDG_PARTICLES.get(sel_t)
            if pdg_info and st.get("particles", 0) > 0:
                sp = pdg_info["spin"]
                bn = pdg_info["baryon_num"]
                ln = pdg_info["lepton_num"]
                ss = pdg_info["strangeness"]
                w.text(f"spin={sp}  B={bn} L={ln} S={ss}")
                lt = pdg_info["lifetime_s"]
                mass_mev = pdg_info["mass_mev"]
                lt_str = "stable" if lt > 1e20 else f"{lt:.2e}s"
                w.text(f"{mass_mev:.2f} MeV  {lt_str}")

        with self.gui.sub_window(
            "Gun/Presets", right_column_x, 0.83, right_panel_width, 0.165
        ) as w:
            gun_int = w.slider_int("Gun", 1 if self.gun_enabled else 0, 0, 1)
            self.gun_enabled = gun_int == 1
            gun_idx = (
                self._spawn_ids.index(self.gun_type) if self.gun_type in self._spawn_ids else 0
            )
            gun_idx = w.slider_int("G.Type", gun_idx, 0, len(self._spawn_ids) - 1)
            self.gun_type = self._spawn_ids[gun_idx]
            self.gun_speed = w.slider_float("G.Spd", self.gun_speed, 1.0, 20.0)
            self.gun_rate = w.slider_float("G.Rate", self.gun_rate, 1.0, 60.0)
            w.text("Presets (keys 1-9,0):")
            preset_names = [
                "1 Def",
                "2 Ruth",
                "3 Cycl",
                "4 Gas",
                "5 Beam",
                "6 BH",
                "7 LHC",
                "8 e+e-",
                "9 Play",
                "0 N-body",
            ]
            for i, name in enumerate(preset_names):
                if w.button(name):
                    self._preset_idx = i
                    self._presets()[i]()

    def render(self) -> None:
        """Render one frame: particles, trails, black hole, GUI."""
        n = sim.num_active[None]
        if n > 0:
            self.selected_particle = max(0, min(self.selected_particle, n - 1))
        else:
            self.selected_particle = 0

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
        self.canvas.set_background_color(BACKGROUND_COLOR)
        self.scene.set_camera(self.camera)
        self.scene.ambient_light((0.15, 0.15, 0.2))
        self.scene.point_light(pos=(8, 8, 15), color=(1.0, 0.95, 0.9))
        self.scene.point_light(pos=(-8, -5, -10), color=(0.3, 0.3, 0.5))

        bh_rs = 2.0 * self.bh_mass / (self.c_light * self.c_light) if self.bh_enabled else 0.0
        bh_pos_tup = (self.bh_x, self.bh_y, self.bh_z)
        sim.prepare_render(
            self.particle_size,
            PARTICLE_RADIUS_SCALE,
            self.bh_enabled,
            bh_rs,
            bh_pos_tup,
            hide_photons=not self.show_photons,
            show_trails=self.show_trails,
        )

        self.scene.particles(
            sim.star_pos,
            radius=0.06,
            per_vertex_color=sim.star_color,
            index_count=sim.NUM_BG_STARS,
        )

        rc = sim.render_count[None]
        if rc > 0:
            self.scene.particles(
                sim.render_pos,
                radius=self.particle_size,
                per_vertex_color=sim.render_color,
                index_count=rc,
            )

        if self.bh_enabled:
            if self._bh_ring_dirty:
                sim.build_bh_ring(self.bh_x, self.bh_y, self.bh_z, bh_rs)
                self._bh_ring_dirty = False
            if not self._disk_initialized:
                sim.init_accretion_disk(self.bh_x, self.bh_y, self.bh_z, self.bh_gm, bh_rs)
                self._disk_initialized = True

            r_shadow = sim.BH_SHADOW_FACTOR * bh_rs
            self.scene.particles(
                sim.bh_eh_pos,
                radius=max(r_shadow, 0.08),
                per_vertex_color=sim.bh_eh_color,
                index_count=1,
            )
            self.scene.particles(
                sim.bh_ring_pos,
                radius=bh_rs * 0.15 + 0.015,
                per_vertex_color=sim.bh_ring_color,
                index_count=sim.BH_RING_N,
            )
            self.scene.particles(
                sim.disk_pos,
                radius=bh_rs * 0.18 + 0.02,
                per_vertex_color=sim.disk_color,
                index_count=sim.DISK_N,
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
                nv = min(tc * 2, MAX_PARTICLES * TRAIL_LENGTH * 2)
                self.scene.lines(
                    sim.trail_vertices,
                    width=self.trail_width,
                    per_vertex_color=sim.trail_colors,
                    vertex_count=nv,
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

    @property
    def bh_gm(self):
        return self.bh_mass

    @property
    def bh_rs(self):
        return 2.0 * self.bh_mass / (self.c_light * self.c_light) if self.c_light > 0 else 0.0

    @property
    def bh_pos(self):
        return (self.bh_x, self.bh_y, self.bh_z)
