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
    seen = set()
    for r in cfg["recipes"]:
        if r["id"] in seen:
            raise ValueError(f"Duplicate recipe id {r['id']!r}")
        seen.add(r["id"])
        if r["glass"] not in cfg["glasses"]:
            raise ValueError(f"Recipe {r['id']} uses unknown glass {r['glass']!r}")
        for ing in r["ingredients"]:
            if ing not in cfg["ingredients"]:
                raise ValueError(f"Recipe {r['id']} uses unknown ingredient {ing!r}")
            if cfg["ingredients"][ing].get("hand_pour"):
                raise ValueError(f"Recipe {r['id']}: {ing} is hand-poured — put it under top_with")
        for ing in (r.get("top_with") or {}):
            if not cfg["ingredients"].get(ing, {}).get("hand_pour"):
                raise ValueError(f"Recipe {r['id']}: top_with {ing!r} must be a hand_pour ingredient")
        for ing in r.get("pour_last") or []:
            if ing not in r["ingredients"]:
                raise ValueError(f"Recipe {r['id']}: pour_last {ing!r} isn't in its ingredients")
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


def hand_stock(cfg):
    """Hand-poured (fizzy) ingredients the bartender has on hand."""
    return {k for k, v in cfg["ingredients"].items()
            if v.get("hand_pour") and v.get("in_stock", True)}


def available_recipes(cfg):
    loaded = loaded_ingredients(cfg)
    stock = hand_stock(cfg)
    return [r for r in cfg["recipes"]
            if set(r["ingredients"]) <= loaded and set(r.get("top_with") or {}) <= stock]


def bartender_extras(cfg, recipe):
    """What the bartender adds by hand after the robot pours."""
    top = [{"name": cfg["ingredients"][k]["name"], "ml": float(v)}
           for k, v in (recipe.get("top_with") or {}).items()]
    return {"top_with": top, "finish": recipe.get("finish", "")}


def menu_groups(cfg, recipe):
    """Filter tabs for the menu: base spirits, 'Other', or 'No alcohol'."""
    if not is_alcoholic(cfg, recipe):
        return ["No alcohol"]
    groups = []
    for i in recipe["ingredients"]:
        g = cfg["ingredients"][i].get("group")
        if g and g not in groups:
            groups.append(g)
    return groups or ["Other"]


GARNISHES = ("lime", "lemon", "orange", "cherry", "pineapple", "none")


def art_spec(cfg, recipe):
    """Everything static/drinkart.js needs to draw a picture of this drink."""
    glass_key, _ = glass_for(cfg, recipe)
    last = set(recipe.get("pour_last") or [])
    layers = []
    for ing, ml in list(recipe["ingredients"].items()) + list((recipe.get("top_with") or {}).items()):
        info = cfg["ingredients"][ing]
        layers.append({"color": info.get("color", "#eeeeee"), "tint": float(info.get("tint", 0.1)),
                       "ml": float(ml), "last": ing in last})
    garnish = recipe.get("garnish")
    if garnish not in GARNISHES:
        ings = set(recipe["ingredients"])
        if "grenadine" in last or (ings == {"grenadine"}):
            garnish = "cherry"
        elif "pineapple_juice" in ings and "orange_juice" not in ings:
            garnish = "pineapple"
        elif "orange_juice" in ings:
            garnish = "orange"
        elif "lime_juice" in ings:
            garnish = "lime"
        elif "lemon_juice" in ings:
            garnish = "lemon"
        else:
            garnish = "none"
    return {"glass": glass_key, "layers": layers, "garnish": garnish}


PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "photos")


def photo_info(recipe_id):
    """{'file': 'photos/x.jpg', 'credit': {...}} if a real photo exists for this drink, else None."""
    path = os.path.join(PHOTO_DIR, f"{recipe_id}.jpg")
    if not os.path.exists(path):
        return None
    credits = {}
    cpath = os.path.join(PHOTO_DIR, "credits.json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            credits = json.load(f)
    return {"file": f"photos/{recipe_id}.jpg", "credit": credits.get(recipe_id)}


def display_ingredients(cfg, recipe):
    names = [cfg["ingredients"][i]["name"] for i in recipe["ingredients"]]
    return names + [cfg["ingredients"][i]["name"] for i in (recipe.get("top_with") or {})]


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
    - the robot's part is scaled down so robot + hand top-up fits the glass,
      and the robot never pours more than max_pour_ml
    - pour_last ingredients get phase 1 (they start after everything else)
    """
    if strength not in allowed_strengths(cfg, recipe):
        raise ValueError(f"Strength {strength!r} not allowed for {recipe['id']}")
    mult = STRENGTHS[strength]

    amounts = {}
    for ing, ml in recipe["ingredients"].items():
        alc = cfg["ingredients"][ing].get("alcoholic")
        amounts[ing] = float(ml) * (mult if alc else 1.0)

    _, glass = glass_for(cfg, recipe)
    top_ml = sum(float(v) for v in (recipe.get("top_with") or {}).values())
    limit = min(float(glass["max_ml"]) - top_ml, float(cfg.get("max_pour_ml", 300)))
    if limit <= 0:
        raise ValueError(f"{recipe['id']}: top_with alone overfills the {glass['name']}")
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
            "phase": 1 if ing in (recipe.get("pour_last") or []) else 0,
        })
    return steps


def estimate_seconds(cfg, steps):
    """Rough wall-clock time for a pour given the simultaneous-pump limit."""
    n = max(1, int(cfg.get("max_simultaneous_pumps", 4)))
    total = 0.0
    for phase in sorted({st.get("phase", 0) for st in steps}):
        lanes = [0.0] * n
        for s in sorted((st["seconds"] for st in steps if st.get("phase", 0) == phase), reverse=True):
            i = lanes.index(min(lanes))
            lanes[i] += s
        total += max(lanes)
    return round(total, 1)
