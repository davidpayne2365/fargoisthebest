import os
import time

import pytest

os.environ["DRINKBOT_MOCK"] = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from drinkbot import recipes as R  # noqa: E402
from drinkbot.hardware import PumpBank  # noqa: E402
from drinkbot.server import create_app  # noqa: E402


@pytest.fixture
def cfg():
    return R.load_config(os.path.join(ROOT, "config.yaml"))


@pytest.fixture
def cal(tmp_path):
    return R.Calibration(str(tmp_path / "cal.json"))


def test_every_recipe_plans_at_every_strength(cfg, cal):
    avail = R.available_recipes(cfg)
    assert len(avail) == len(cfg["recipes"])  # default config: everything is loaded
    for r in avail:
        for st in R.allowed_strengths(cfg, r):
            assert R.plan_pour(cfg, r, st, cal)


def test_menu_hides_drinks_without_loaded_ingredients(cfg):
    cfg["pumps"] = [p for p in cfg["pumps"] if p["ingredient"] != "gin"]
    ids = {r["id"] for r in R.available_recipes(cfg)}
    assert "margarita" in ids
    assert "gin_tonic" not in ids and "long_island" not in ids


def test_out_of_stock_hand_pour_hides_drinks(cfg):
    cfg["ingredients"]["cola"]["in_stock"] = False
    ids = {r["id"] for r in R.available_recipes(cfg)}
    assert "rum_coke" not in ids and "long_island" not in ids
    assert "gin_tonic" in ids


def test_top_with_leaves_room_in_glass(cfg, cal):
    r = dict(R.get_recipe(cfg, "gin_tonic"))
    r["ingredients"] = {"gin": 400}
    robot = sum(s["ml"] for s in R.plan_pour(cfg, r, "regular", cal))
    assert robot + 150 <= cfg["glasses"]["highball"]["max_ml"] + 0.5
    extras = R.bartender_extras(cfg, r)
    assert extras["top_with"] == [{"name": "Tonic Water", "ml": 150.0}]


def test_pour_last_gets_later_phase(cfg, cal):
    steps = R.plan_pour(cfg, R.get_recipe(cfg, "tequila_sunrise"), "regular", cal)
    phase = {s["ingredient"]: s["phase"] for s in steps}
    assert phase == {"tequila": 0, "orange_juice": 0, "grenadine": 1}


def test_no_virgin_option_when_robot_pours_only_alcohol(cfg):
    assert "virgin" not in R.allowed_strengths(cfg, R.get_recipe(cfg, "captain_coke"))
    assert R.allowed_strengths(cfg, R.get_recipe(cfg, "shirley_temple")) == ["regular"]


def test_strength_scales_only_alcohol(cfg, cal):
    r = R.get_recipe(cfg, "screwdriver")
    reg = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "regular", cal)}
    strong = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "strong", cal)}
    virgin = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "virgin", cal)}
    assert strong["vodka"] > reg["vodka"]
    assert strong["orange_juice"] == reg["orange_juice"]
    assert "vodka" not in virgin


def test_pour_never_exceeds_glass(cfg, cal):
    r = dict(R.get_recipe(cfg, "margarita"))
    r["ingredients"] = {"tequila": 500, "lime_juice": 500}
    total = sum(s["ml"] for s in R.plan_pour(cfg, r, "regular", cal))
    assert total <= cfg["glasses"]["rocks"]["max_ml"] + 0.5


def test_calibration_changes_seconds(cfg, cal):
    r = R.get_recipe(cfg, "screwdriver")
    before = R.plan_pour(cfg, r, "regular", cal)[0]["seconds"]
    cal.set(1, 3.2)  # vodka pump twice as fast
    after = R.plan_pour(cfg, r, "regular", cal)[0]["seconds"]
    assert after == pytest.approx(before / 2, rel=0.01)


def test_pumpbank_respects_simultaneous_limit():
    pumps = [{"id": i, "gpio": i} for i in range(1, 5)]
    bank = PumpBank(pumps, max_simultaneous=2, mock=True)
    peak = 0

    def cb(_):
        nonlocal peak
        peak = max(peak, sum(d.value for d in bank.outputs.values()))

    assert bank.run([(i, 0.3) for i in range(1, 5)], progress_cb=cb)
    assert peak <= 2
    assert all(d.value == 0 for d in bank.outputs.values())


def test_pumpbank_phases_run_in_order():
    bank = PumpBank([{"id": 1, "gpio": 1}, {"id": 2, "gpio": 2}], max_simultaneous=4, mock=True)
    overlap = False

    def cb(_):
        nonlocal overlap
        if bank.outputs[1].value and bank.outputs[2].value:
            overlap = True

    assert bank.run([(1, 0.3, 0), (2, 0.2, 1)], progress_cb=cb)
    assert not overlap


def test_full_order_flow(tmp_path):
    app = create_app(os.path.join(ROOT, "config.yaml"), str(tmp_path), mock=True)
    c = app.test_client()
    assert c.get("/").status_code == 200

    r = c.post("/api/orders", json={"recipe_id": "kamikaze", "guest": "Sam", "strength": "light"})
    assert r.status_code == 200
    oid, tok = r.json["id"], r.json["token"]
    assert c.get(f"/api/orders/{oid}?t={tok}").json["status"] == "new"
    assert c.get(f"/api/orders/{oid}?t=wrong").status_code == 404

    assert c.get("/api/bar/state").status_code == 401
    c.post("/login", data={"pin": "1234"})
    assert c.post(f"/api/bar/orders/{oid}/approve").status_code == 200

    # speed the fake pumps up so the test is quick
    store = app.config["STORE"]
    o = store.get(oid)
    for s in o["steps"]:
        s["seconds"] = 0.05
    import json
    store.db.execute("UPDATE orders SET steps=? WHERE id=?", (json.dumps(o["steps"]), oid))
    store.db.commit()

    assert c.post(f"/api/bar/orders/{oid}/pour").status_code == 200
    for _ in range(100):
        if c.get(f"/api/orders/{oid}?t={tok}").json["status"] == "ready":
            break
        time.sleep(0.05)
    assert c.get(f"/api/orders/{oid}?t={tok}").json["status"] == "ready"
    rc = c.post("/api/orders", json={"recipe_id": "rum_coke", "guest": "Jo"}).json
    extras = c.get(f"/api/orders/{rc['id']}?t={rc['token']}").json["extras"]
    assert extras["top_with"][0]["name"] == "Cola"
    assert c.post(f"/api/bar/orders/{oid}/picked_up").status_code == 200
    assert c.get(f"/api/orders/{oid}?t={tok}").json["status"] == "done"


def test_emergency_stop_flags_order(tmp_path):
    app = create_app(os.path.join(ROOT, "config.yaml"), str(tmp_path), mock=True)
    c = app.test_client()
    oid = c.post("/api/orders", json={"recipe_id": "screwdriver", "guest": "Al"}).json["id"]
    c.post("/login", data={"pin": "1234"})
    c.post(f"/api/bar/orders/{oid}/approve")
    c.post(f"/api/bar/orders/{oid}/pour")
    time.sleep(0.2)
    c.post("/api/bar/stop")
    time.sleep(0.2)
    o = app.config["STORE"].get(oid)
    assert o["status"] == "queued" and "dump" in o["note"]
    assert app.config["MACHINE"].snapshot()["status"] == "stopped"
