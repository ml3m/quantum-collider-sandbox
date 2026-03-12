#!/usr/bin/env python3
"""Backward-compatible entry point. Prefer: python -m quantum_collider_sandbox"""

import sys
from pathlib import Path

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from quantum_collider_sandbox.__main__ import main

if __name__ == "__main__":
    main()
