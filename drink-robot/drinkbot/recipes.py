"""Config loading, menu filtering and pour planning (pure logic, no hardware)."""
import json
import os

import yaml

STRENGTHS = {
    "virgin": 0.0,
    "light": 0.75,
    "regular": 1.0,
    "strong": 1.25,
}


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    ids = [p["id"] for p in cfg["pumps"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate pump ids in config")
    pins = [p["gpio"] for p in cfg["pumps"]]
    if len(pins) != len(set(pins)):
        raise ValueError("Two pumps share a GPIO pin in config")
    for p in cfg["pumps"]:
        if p.get("ingredient") and p["ingredient"] not in cfg["ingredients"]:
            raise ValueError(f"Pump {p['id']} uses unknown ingredient {p['ingredient']!r}")
    for r in cfg["recipes"]:
        if r["glass"] not in cfg["glasses"]:
            raise ValueError(f"Recipe {r['id']} uses unknown glass {r['glass']!r}")
        for ing in r["ingredients"]:
            if ing not in cfg["ingredients"]:
                raise ValueError(f"Recipe {r['id']} uses unknown ingredient {ing!r}")
    return cfg


class Calibration:
    """Per-pump ml/sec overrides measured from the Admin page (kept out of config.yaml)."""

    def __init__(self, path):
        self.path = path
        self.values = {}
        if os.path.exists(path):
            with open(path) as f:
                self.values = {int(k): float(v) for k, v in json.load(f).items()}

    def ml_per_sec(self, pump):
        return self.values.get(pump["id"], float(pump["ml_per_sec"]))

    def set(self, pump_id, value):
        self.values[int(pump_id)] = float(value)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.values, f, indent=2)


def pump_for(cfg, ingredient):
    for p in cfg["pumps"]:
        if p.get("ingredient") == ingredient:
            return p
    return None


def loaded_ingredients(cfg):
    return {p["ingredient"] for p in cfg["pumps"] if p.get("ingredient")}


def is_alcoholic(cfg, recipe):
    return any(cfg["ingredients"][i].get("alcoholic") for i in recipe["ingredients"])


def available_recipes(cfg):
    loaded = loaded_ingredients(cfg)
    return [r for r in cfg["recipes"] if set(r["ingredients"]) <= loaded]


def get_recipe(cfg, recipe_id):
    for r in available_recipes(cfg):
        if r["id"] == recipe_id:
            return r
    return None


def allowed_strengths(cfg, recipe):
    if not is_alcoholic(cfg, recipe):
        return ["regular"]
    has_mixer = any(not cfg["ingredients"][i].get("alcoholic") for i in recipe["ingredients"])
    out = []
    if has_mixer:
        out.append("virgin")
    out += ["light", "regular"]
    if cfg.get("allow_strong", True):
        out.append("strong")
    return out


def glass_for(cfg, recipe):
    """In stack mode every drink goes in the stack cup."""
    key = cfg.get("stack_cup") if cfg.get("cup_mode") == "stack" else recipe["glass"]
    g = cfg["glasses"][key]
    return key, g


def price_for(cfg, recipe, strength):
    price = float(recipe.get("price", 0))
    if strength == "strong":
        price += float(cfg.get("strong_surcharge", 0))
    return round(price, 2)


def plan_pour(cfg, recipe, strength, calibration):
    """Return a list of steps: {ingredient, name, pump_id, ml, seconds}.

    - alcoholic ingredients are scaled by the strength multiplier
    - the whole drink is scaled down to fit the glass and max_pour_ml
    """
    if strength not in allowed_strengths(cfg, recipe):
        raise ValueError(f"Strength {strength!r} not allowed for {recipe['id']}")
    mult = STRENGTHS[strength]

    amounts = {}
    for ing, ml in recipe["ingredients"].items():
        alc = cfg["ingredients"][ing].get("alcoholic")
        amounts[ing] = float(ml) * (mult if alc else 1.0)

    _, glass = glass_for(cfg, recipe)
    limit = min(float(glass["max_ml"]), float(cfg.get("max_pour_ml", 300)))
    total = sum(amounts.values())
    if total > limit:
        scale = limit / total
        amounts = {k: v * scale for k, v in amounts.items()}

    steps = []
    for ing, ml in amounts.items():
        if ml <= 0.5:
            continue
        pump = pump_for(cfg, ing)
        if pump is None:
            raise ValueError(f"No pump loaded with {ing}")
        rate = calibration.ml_per_sec(pump)
        seconds = ml / rate
        if seconds > cfg.get("max_pump_seconds", 180):
            raise ValueError(f"{ing} would run {seconds:.0f}s — check calibration")
        steps.append({
            "ingredient": ing,
            "name": cfg["ingredients"][ing]["name"],
            "pump_id": pump["id"],
            "ml": round(ml, 1),
            "seconds": round(seconds, 2),
        })
    return steps


def estimate_seconds(cfg, steps):
    """Rough wall-clock time for a pour given the simultaneous-pump limit."""
    n = max(1, int(cfg.get("max_simultaneous_pumps", 4)))
    lanes = [0.0] * n
    for s in sorted((st["seconds"] for st in steps), reverse=True):
        i = lanes.index(min(lanes))
        lanes[i] += s
    return round(max(lanes), 1)
