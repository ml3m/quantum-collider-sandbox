"""Tests for config module."""

from quantum_collider_sandbox.config import (
    INTEGRATOR,
    MAX_PARTICLES,
    NUM_TYPES,
    SPEED_OF_LIGHT,
)


def test_config_constants() -> None:
    """Verify config constants have expected values."""
    assert MAX_PARTICLES > 0
    assert NUM_TYPES > 0
    assert SPEED_OF_LIGHT > 0
    assert INTEGRATOR in ("euler", "leapfrog")
