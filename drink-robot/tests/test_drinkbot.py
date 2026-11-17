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
def fizzy_cfg(cfg):
    """Config with the (default-off) fizzy mixers switched back on."""
    for v in cfg["ingredients"].values():
        if v.get("hand_pour"):
            v["in_stock"] = True
    return cfg


@pytest.fixture
def cal(tmp_path):
    return R.Calibration(str(tmp_path / "cal.json"))


def test_default_menu_has_no_fizzy_drinks(cfg):
    avail = R.available_recipes(cfg)
    assert avail and all(not r.get("top_with") for r in avail)
    ids = {r["id"] for r in avail}
    assert "margarita" in ids and "rum_coke" not in ids
    assert "amaretto_sour" in ids and "gimlet" not in ids
    assert len(avail) == 28


def test_every_recipe_plans_at_every_strength(fizzy_cfg, cal):
    cfg = fizzy_cfg
    avail = R.available_recipes(cfg)
    missing = [r for r in cfg["recipes"] if r not in avail]
    assert all({"gin", "spiced_rum"} & set(r["ingredients"]) for r in missing)  # not on a pump
    for r in avail:
        for st in R.allowed_strengths(cfg, r):
            assert R.plan_pour(cfg, r, st, cal)


def test_menu_hides_drinks_without_loaded_ingredients(fizzy_cfg):
    cfg = fizzy_cfg
    cfg["pumps"] = [p for p in cfg["pumps"] if p["ingredient"] != "tequila"]
    ids = {r["id"] for r in R.available_recipes(cfg)}
    assert "screwdriver" in ids
    assert "margarita" not in ids and "tequila_sunrise" not in ids


def test_out_of_stock_hand_pour_hides_drinks(fizzy_cfg):
    cfg = fizzy_cfg
    cfg["ingredients"]["cola"]["in_stock"] = False
    ids = {r["id"] for r in R.available_recipes(cfg)}
    assert "rum_coke" not in ids and "whiskey_coke" not in ids
    assert "vodka_tonic" in ids


def test_top_with_leaves_room_in_glass(fizzy_cfg, cal):
    cfg = fizzy_cfg
    r = dict(R.get_recipe(cfg, "vodka_tonic"))
    r["ingredients"] = {"vodka": 400}
    robot = sum(s["ml"] for s in R.plan_pour(cfg, r, "regular", cal))
    assert robot + 150 <= cfg["glasses"]["highball"]["max_ml"] + 0.5
    extras = R.bartender_extras(cfg, r)
    assert extras["top_with"] == [{"name": "Tonic Water", "ml": 150.0}]


def test_pour_last_gets_later_phase(cfg, cal):
    steps = R.plan_pour(cfg, R.get_recipe(cfg, "tequila_sunrise"), "regular", cal)
    phase = {s["ingredient"]: s["phase"] for s in steps}
    assert phase == {"tequila": 0, "orange_syrup": 0, "water": 0, "grenadine": 1}


def test_no_virgin_option_when_robot_pours_only_alcohol(fizzy_cfg):
    cfg = fizzy_cfg
    assert "virgin" not in R.allowed_strengths(cfg, R.get_recipe(cfg, "whiskey_coke"))
    assert R.allowed_strengths(cfg, R.get_recipe(cfg, "shirley_temple")) == ["regular"]


def test_strength_scales_only_alcohol(cfg, cal):
    r = R.get_recipe(cfg, "screwdriver")
    reg = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "regular", cal)}
    strong = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "strong", cal)}
    virgin = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, r, "virgin", cal)}
    assert strong["vodka"] > reg["vodka"]
    assert strong["orange_syrup"] == reg["orange_syrup"] and strong["water"] == reg["water"]
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
    # fizzy drinks are off by default, so ordering one is refused
    assert c.post("/api/orders", json={"recipe_id": "rum_coke", "guest": "Jo"}).status_code == 400
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


def test_every_drink_has_picture_spec(fizzy_cfg):
    for r in R.available_recipes(fizzy_cfg):
        art = R.art_spec(fizzy_cfg, r)
        assert art["glass"] in fizzy_cfg["glasses"]
        assert art["garnish"] in R.GARNISHES
        assert art["layers"] and all(layer["color"].startswith("#") for layer in art["layers"])
    sunrise = R.art_spec(fizzy_cfg, R.get_recipe(fizzy_cfg, "tequila_sunrise"))
    assert any(layer["last"] for layer in sunrise["layers"]) and sunrise["garnish"] == "cherry"


class FakeSerial:
    def __init__(self, port, baud, timeout=1):
        self.port, self.written = port, []

    def write(self, b):
        self.written.append(bytes(b))

    def flush(self):
        pass

    def close(self):
        pass


def test_usb_relay_driver_sends_lcus_commands():
    pumps = [{"id": i, "gpio": i} for i in (1, 9)]
    boards = []

    def factory(port, baud, timeout=1):
        s = FakeSerial(port, baud)
        boards.append(s)
        return s

    bank = PumpBank(pumps, mock=False, driver="usb_relay",
                    usb_relay={"ports": ["COM3", "COM4"]}, serial_factory=factory)
    boards[0].written.clear(); boards[1].written.clear()
    assert bank.run([(1, 0.05), (9, 0.05)])
    assert bytes([0xA0, 1, 1, 0xA2]) in boards[0].written and bytes([0xA0, 1, 0, 0xA1]) in boards[0].written
    assert bytes([0xA0, 1, 1, 0xA2]) in boards[1].written  # pump 9 -> board 2, relay 1


def test_usb_relay_needs_enough_boards():
    with pytest.raises(ValueError):
        PumpBank([{"id": 9, "gpio": 9}], mock=False, driver="usb_relay",
                 usb_relay={"ports": ["COM3"]}, serial_factory=FakeSerial)


def test_mvp_config_extends_base(tmp_path):
    cfg = R.load_config(os.path.join(ROOT, "config.mvp.yaml"))
    assert len(cfg["pumps"]) == 8 and cfg["pump_driver"] == "usb_relay"
    names = {r["name"] for r in R.available_recipes(cfg)}
    assert len(names) == 10 and {"Screwdriver", "Whiskey Sour", "Godfather"} <= names
    cfg["pump_driver"] = "mock"  # app boots with it
    app = create_app(os.path.join(ROOT, "config.mvp.yaml"), str(tmp_path), mock=True)
    assert app.test_client().get("/").status_code == 200


def test_juice_is_made_from_syrup_and_water(cfg, cal):
    steps = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, R.get_recipe(cfg, "screwdriver"), "regular", cal)}
    assert steps == {"vodka": 45.0, "orange_syrup": 22.5, "water": 112.5}  # 135 ml "juice" = 1:5


def test_real_juice_on_a_pump_wins_over_syrup(cfg, cal):
    cfg["pumps"][10]["ingredient"] = "orange_juice"  # swap the orange syrup pump for real juice
    steps = {s["ingredient"]: s["ml"] for s in R.plan_pour(cfg, R.get_recipe(cfg, "screwdriver"), "regular", cal)}
    assert steps == {"vodka": 45.0, "orange_juice": 135.0}


def test_nothing_perishable_on_default_pumps(cfg):
    perishable = {"orange_juice", "cranberry_juice", "pineapple_juice", "lime_juice", "lemon_juice"}
    assert not perishable & {p["ingredient"] for p in cfg["pumps"]}
