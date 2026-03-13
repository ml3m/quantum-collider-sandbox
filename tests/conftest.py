"""Pytest configuration. Initialize Taichi once before any Taichi-using tests."""

import taichi as ti

ti.init(arch=ti.cpu)
