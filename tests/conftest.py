"""Shared pytest configuration for the Book Creator project."""

from __future__ import annotations

import sys
from pathlib import Path
import sysconfig

ROOT = Path(__file__).resolve().parent.parent
EXTRA_PATHS = [ROOT, ROOT / "libs/python"]
for extra in EXTRA_PATHS:
    sys.path.insert(0, str(extra))

SITE_PACKAGES = Path(sysconfig.get_paths().get("purelib", ""))
if SITE_PACKAGES and str(SITE_PACKAGES) not in sys.path:
    sys.path.append(str(SITE_PACKAGES))
