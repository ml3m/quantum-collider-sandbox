Changelog
=========

All notable changes to this project will be documented in this file.

1.1.0 (2026-03-21)
------------------

**Phase 1 Optimization & Comprehensive Documentation**

- **Performance:** Heavy trail rendering optimization (10x vertex reduction, 2-3x FPS improvement at 1k particles)
- **Trail tuning:** TRAIL_LENGTH reduced 400→40 with extensive configuration presets (1k, 2k, 5k+ particles)
- **Documentation:** Added 13 comprehensive documentation pages covering quickstart, usage, architecture, physics, API, and troubleshooting
- **Configuration:** Added detailed tuning guides for different hardware capabilities and physics scenarios
- **Code quality:** Extracted duplicate particle spawn logic into reusable helper function (eliminated R0801 warning)
- **CI/CD:** Fixed pre-commit hooks to work without venv activation (changed pylint to Python language handler)
- **Physics docs:** Documented all force models, kinematics, collision physics, and 9 known limitations with workarounds
- **Developer guide:** Added comprehensive development documentation with extending, testing, and profiling guides

1.0.1 (2025-03-13)
------------------

- Fixed README RST table markup for PyPI rendering
- Added Python version constraint (>=3.10,<3.13)
- Added project URLs to PyPI metadata
- Removed redundant requirements.txt
- Updated README with format-check, format, test-cov targets
- Fixed README clone path

1.0.0 (2025-03-13)
------------------

- Initial release
- PDG-accurate particle catalog (40 particles)
- Real-time GPU physics simulation (Taichi/Vulkan)
- Collisions, decays, annihilations with relativistic kinematics
- Black hole, particle gun, presets
