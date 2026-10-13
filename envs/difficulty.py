"""Difficulty protocol for garment initial states.

Three levels:
  L1 FLAT       : slight random translation + yaw only.
  L2 PERTURBED  : one corner lifted and dropped; light wrinkles.
  L3 CRUMPLED   : 1-2 grasp-lift-drop cycles; requires recovery.

Day 3: interface + numeric parameters only.
Day 4: actual physics manipulation against GarmentLabBackend.

Contract with GarmentLabBackend.reset(seed, difficulty):
  - config_for(name) returns the frozen DifficultyConfig.
  - apply(backend, config) mutates the backend's garment state.
    For Day 3 this raises NotImplementedError for non-flat levels;
    Day 4 fills it in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DifficultyLevel(str, Enum):
    FLAT = "flat"
    PERTURBED = "perturbed"
    CRUMPLED = "crumpled"

    @classmethod
    def parse(cls, name: Optional[str]) -> "DifficultyLevel":
        if name is None:
            return cls.FLAT
        try:
            return cls(name.lower())
        except ValueError as e:
            raise ValueError(
                f"unknown difficulty {name!r}; "
                f"expected one of {[m.value for m in cls]}"
            ) from e


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class DifficultyConfig:
    name: DifficultyLevel

    # Random translation / rotation applied to the garment at reset.
    translate_xy_range: Tuple[float, float] = (0.0, 0.0)     # meters
    yaw_range: Tuple[float, float] = (0.0, 0.0)              # radians

    # L2 / L3: corner lift-drop parameters.
    num_lift_drops: int = 0
    lift_height_range: Tuple[float, float] = (0.0, 0.0)      # meters
    lift_hold_steps: int = 0
    drop_xy_jitter: float = 0.0                              # meters

    # Physics settle before observation is returned.
    settle_steps: int = 120

    # Whether the expert should run recovery moves before folding.
    needs_recovery: bool = False
    max_recovery_moves: int = 0

    # Extra free-form fields for future tuning.
    notes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Frozen defaults (Day 3). Day 4 may tune numbers, not the schema.
# ---------------------------------------------------------------------------

DEFAULTS: Dict[DifficultyLevel, DifficultyConfig] = {
    DifficultyLevel.FLAT: DifficultyConfig(
        name=DifficultyLevel.FLAT,
        translate_xy_range=(0.0, 0.03),
        yaw_range=(-np.pi / 18, np.pi / 18),   # +-10 degrees
        num_lift_drops=0,
        settle_steps=120,
        needs_recovery=False,
        max_recovery_moves=0,
        notes="Slight random translation and yaw only.",
    ),
    DifficultyLevel.PERTURBED: DifficultyConfig(
        name=DifficultyLevel.PERTURBED,
        translate_xy_range=(0.0, 0.03),
        yaw_range=(-np.pi / 18, np.pi / 18),
        num_lift_drops=1,
        lift_height_range=(0.05, 0.10),
        lift_hold_steps=30,
        drop_xy_jitter=0.02,
        settle_steps=180,
        needs_recovery=True,
        max_recovery_moves=1,
        notes="One corner lifted and dropped; light wrinkles.",
    ),
    DifficultyLevel.CRUMPLED: DifficultyConfig(
        name=DifficultyLevel.CRUMPLED,
        translate_xy_range=(0.0, 0.05),
        yaw_range=(-np.pi / 9, np.pi / 9),     # +-20 degrees
        num_lift_drops=2,
        lift_height_range=(0.08, 0.15),
        lift_hold_steps=45,
        drop_xy_jitter=0.04,
        settle_steps=240,
        needs_recovery=True,
        max_recovery_moves=2,
        notes="Two grasp-lift-drop cycles; requires recovery before folding.",
    ),
}


# ---------------------------------------------------------------------------
# YAML loader (optional)
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_configs(yaml_path: Optional[Path] = None) -> Dict[DifficultyLevel, DifficultyConfig]:
    """Load configs from YAML if available; otherwise return DEFAULTS.

    Unknown keys in YAML are ignored to keep the schema stable.
    """
    if yaml_path is None:
        yaml_path = Path(__file__).resolve().parent.parent / "configs" / "difficulty.yaml"
    data = _load_yaml(Path(yaml_path))
    if not data:
        return dict(DEFAULTS)

    out: Dict[DifficultyLevel, DifficultyConfig] = {}
    for lvl in DifficultyLevel:
        entry = data.get(lvl.value, {})
        base = DEFAULTS[lvl]
        cfg = DifficultyConfig(
            name=lvl,
            translate_xy_range=tuple(entry.get("translate_xy_range", base.translate_xy_range)),
            yaw_range=tuple(entry.get("yaw_range", base.yaw_range)),
            num_lift_drops=int(entry.get("num_lift_drops", base.num_lift_drops)),
            lift_height_range=tuple(entry.get("lift_height_range", base.lift_height_range)),
            lift_hold_steps=int(entry.get("lift_hold_steps", base.lift_hold_steps)),
            drop_xy_jitter=float(entry.get("drop_xy_jitter", base.drop_xy_jitter)),
            settle_steps=int(entry.get("settle_steps", base.settle_steps)),
            needs_recovery=bool(entry.get("needs_recovery", base.needs_recovery)),
            max_recovery_moves=int(entry.get("max_recovery_moves", base.max_recovery_moves)),
            notes=str(entry.get("notes", base.notes)),
        )
        out[lvl] = cfg
    return out


# ---------------------------------------------------------------------------
# Apply to a backend
# ---------------------------------------------------------------------------

def sample_initial_offset(
    config: DifficultyConfig,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, float]:
    """Sample (xy_offset, yaw). Called by the backend before physics settle."""
    tx_lo, tx_hi = config.translate_xy_range
    dx = float(rng.uniform(tx_lo, tx_hi))
    dy = float(rng.uniform(tx_lo, tx_hi))
    y_lo, y_hi = config.yaw_range
    yaw = float(rng.uniform(y_lo, y_hi))
    return np.array([dx, dy], dtype=np.float32), yaw


def apply(backend, config: DifficultyConfig, rng: np.random.Generator) -> None:
    """Mutate the backend's garment state according to config.

    Day 3:
        - FLAT: only records offset/yaw; Day 4 wires the actual reset.
        - PERTURBED / CRUMPLED: not implemented yet.

    Day 4 will implement the lift-drop loop here.
    """
    if config.name == DifficultyLevel.FLAT:
        # Backend will call sample_initial_offset() itself.
        return
    raise NotImplementedError(
        f"difficulty={config.name.value!r} perturbation is Day 4 work. "
        "Only 'flat' is wired on Day 3."
    )
