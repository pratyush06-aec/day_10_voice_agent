from __future__ import annotations

from pathlib import Path
import json
import random
import copy
from typing import List, Dict, Optional

SCENARIOS_PATH = Path("shared-data/day10_scenarios.json")


def _read_json(path: Path) -> List[Dict]:
    """Read JSON file and return list of scenario dicts (or empty list)."""
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Scenarios JSON must be an array (list) of objects.")
        return data
    except Exception as e:
        # bubble up a helpful error for debugging
        raise RuntimeError(f"Failed to read/parse scenarios from {path}: {e}")


def load_scenarios() -> List[Dict]:
    """
    Load and return scenario objects from shared-data/day10_scenarios.json.

    Each scenario is expected to be a dict with at least:
      - "id": unique string
      - "prompt": the improv prompt/instruction
      - "hint": short hint text (optional)
    """
    raw = _read_json(SCENARIOS_PATH)
    # Basic validation & normalization
    validated: List[Dict] = []
    seen_ids = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Scenario at index {i} is not an object/dict.")
        sid = item.get("id") or item.get("name")
        if not sid or not isinstance(sid, str):
            raise ValueError(f"Scenario at index {i} missing a valid 'id' string.")
        if sid in seen_ids:
            raise ValueError(f"Duplicate scenario id '{sid}' found in scenarios file.")
        seen_ids.add(sid)
        prompt = item.get("prompt")
        if not prompt or not isinstance(prompt, str):
            raise ValueError(f"Scenario '{sid}' missing a valid 'prompt' string.")
        # ensure hint exists (empty string if missing)
        hint = item.get("hint", "")
        validated.append({"id": sid, "prompt": prompt, "hint": hint, **{k: v for k, v in item.items() if k not in {'id','prompt','hint'}}})
    return validated


# Cache loaded scenarios at import time (safe to call again if you need to refresh)
_SCENARIOS: List[Dict] = load_scenarios()


def refresh_scenarios_cache() -> None:
    """Reload scenarios from disk into the module cache (call after editing JSON)."""
    global _SCENARIOS
    _SCENARIOS = load_scenarios()


def all_scenarios() -> List[Dict]:
    """Return a shallow copy of all loaded scenarios."""
    return copy.deepcopy(_SCENARIOS)


def pick_scenario(idx: Optional[int] = None) -> Dict:
    """
    Pick a scenario.

    - If idx is None: returns a random scenario (uniform).
    - If idx is an int: returns scenario at (idx % len(scenarios)).
    - If no scenarios loaded: returns a fallback scenario dict.
    """
    if not _SCENARIOS:
        return {"id": "fallback", "prompt": "You are in a small cafe. React to the scene.", "hint": ""}
    if idx is None:
        return copy.deepcopy(random.choice(_SCENARIOS))
    return copy.deepcopy(_SCENARIOS[idx % len(_SCENARIOS)])


def get_scenario_by_id(sid: str) -> Optional[Dict]:
    """Return a scenario dict by id, or None if not found."""
    for s in _SCENARIOS:
        if s.get("id") == sid:
            return copy.deepcopy(s)
    return None


def pick_unique_scenarios(n: int, seed: Optional[int] = None) -> List[Dict]:
    """
    Choose `n` unique scenarios (without repetition). If n > available, scenarios will be repeated
    only after all have been used (order will be shuffled).

    - seed: optional int to make selection reproducible.
    """
    if n <= 0:
        return []
    if not _SCENARIOS:
        # return n copies of fallback
        return [ {"id": "fallback", "prompt": "You are in a small cafe. React to the scene.", "hint": ""} for _ in range(n) ]

    rng = random.Random(seed)
    pool = _SCENARIOS.copy()
    rng.shuffle(pool)

    selected: List[Dict] = []
    while len(selected) < n:
        take = min(n - len(selected), len(pool))
        # take from pool, deep-copy to avoid mutation issues
        selected.extend(copy.deepcopy(pool[:take]))
        # rotate / reshuffle pool for subsequent rounds
        rng.shuffle(pool)
    return selected


# convenience __all__
__all__ = [
    "SCENARIOS_PATH",
    "load_scenarios",
    "refresh_scenarios_cache",
    "all_scenarios",
    "pick_scenario",
    "pick_unique_scenarios",
    "get_scenario_by_id",
]
