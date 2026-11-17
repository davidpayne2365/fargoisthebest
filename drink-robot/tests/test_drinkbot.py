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


def test_menu_hides_drinks_without_loaded_ingredients(cfg):
    ids = {r["id"] for r in R.available_recipes(cfg)}
    assert "margarita" in ids
    assert "gin_tonic" not in ids  # no gin/tonic pump


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
