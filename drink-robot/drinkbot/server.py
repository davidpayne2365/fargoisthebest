"""Flask web app: guest menu, bartender screen, admin/maintenance."""
import functools
import io
import logging
import os
import secrets

from flask import (Flask, abort, jsonify, redirect, render_template, request, send_file,
                   session, url_for)

from . import recipes as R
from .hardware import CupSensor, PumpBank
from .machine import Machine
from .orders import OrderStore

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def create_app(config_path=None, data_dir=None, mock=None):
    config_path = config_path or os.environ.get("DRINKBOT_CONFIG", os.path.join(ROOT, "config.yaml"))
    data_dir = data_dir or os.environ.get("DRINKBOT_DATA", os.path.join(ROOT, "data"))
    os.makedirs(data_dir, exist_ok=True)

    cfg = R.load_config(config_path)
    calibration = R.Calibration(os.path.join(data_dir, "calibration.json"))
    store = OrderStore(os.path.join(data_dir, "orders.db"))
    pumps = PumpBank(cfg["pumps"], cfg.get("max_simultaneous_pumps", 4),
                     cfg.get("max_pump_seconds", 180), mock=mock)
    cs = cfg.get("cup_sensor") or {}
    cup = CupSensor(cs.get("gpio"), cs.get("active_low", True), mock=mock)
    machine = Machine(cfg, store, pumps, cup)

    app = Flask(__name__, template_folder=os.path.join(HERE, "templates"),
                static_folder=os.path.join(HERE, "static"))
    key_file = os.path.join(data_dir, "secret.key")
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
    app.secret_key = open(key_file).read().strip()
    app.config.update(DRINKBOT=cfg, MACHINE=machine, STORE=store, PUMPS=pumps)

    def money(v):
        return f"{cfg.get('currency_symbol', '$')}{v:,.2f}"

    @app.context_processor
    def inject():
        return {"cfg": cfg, "money": money}

    def bartender_required(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            if not session.get("bartender"):
                if request.path.startswith("/api/"):
                    return jsonify(error="login required"), 401
                return redirect(url_for("login", next=request.path))
            return fn(*a, **kw)
        return wrapper

    def order_public(o):
        return {
            "id": o["id"], "guest": o["guest"], "recipe": o["recipe_name"],
            "glass": o["glass_name"], "glass_key": o["glass_key"], "strength": o["strength"],
            "price": o["price"], "status": o["status"], "note": o["note"],
            "steps": o["steps"], "created": o["created"], "extras": o["extras"],
            "position": store.queue_position(o["id"]),
            "est_seconds": R.estimate_seconds(cfg, o["steps"]),
        }

    # ------------------------------------------------------------------ guest
    @app.get("/")
    def menu():
        drinks = []
        for r in R.available_recipes(cfg):
            gkey, g = R.glass_for(cfg, r)
            drinks.append({
                "id": r["id"], "name": r["name"], "description": r.get("description", ""),
                "glass": g["name"], "price": r.get("price", 0),
                "ingredients": R.display_ingredients(cfg, r),
                "strengths": R.allowed_strengths(cfg, r),
                "alcoholic": R.is_alcoholic(cfg, r),
                "groups": R.menu_groups(cfg, r),
            })
        order = ["Vodka", "Gin", "Rum", "Tequila", "Whiskey", "Amaretto", "Other", "No alcohol"]
        present = {g for d in drinks for g in d["groups"]}
        tabs = [g for g in order if g in present] + sorted(present - set(order))
        return render_template("menu.html", drinks=drinks, tabs=tabs)

    @app.post("/api/orders")
    def place_order():
        data = request.get_json(force=True, silent=True) or {}
        recipe = R.get_recipe(cfg, data.get("recipe_id", ""))
        if not recipe:
            return jsonify(error="That drink isn't available"), 400
        guest = (data.get("guest") or "").strip()[:30]
        if not guest:
            return jsonify(error="Please enter your name"), 400
        strength = data.get("strength", "regular")
        try:
            steps = R.plan_pour(cfg, recipe, strength, calibration)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        gkey, g = R.glass_for(cfg, recipe)
        status = "queued" if cfg.get("payment_mode", "tab") == "none" else "new"
        o = store.create(guest, recipe, gkey, g["name"], strength, steps,
                         R.price_for(cfg, recipe, strength), status,
                         extras=R.bartender_extras(cfg, recipe))
        machine.maybe_autostart()
        return jsonify(id=o["id"], token=o["token"],
                       url=url_for("order_page", order_id=o["id"], t=o["token"]))

    def _guest_order(order_id):
        o = store.get(order_id)
        if not o or request.args.get("t") != o["token"]:
            abort(404)
        return o

    @app.get("/order/<int:order_id>")
    def order_page(order_id):
        o = _guest_order(order_id)
        venmo = None
        if cfg.get("payment_mode") == "venmo" and cfg.get("venmo_handle"):
            venmo = (f"https://venmo.com/{cfg['venmo_handle']}?txn=pay&amount={o['price']:.2f}"
                     f"&note=Drink%20%23{o['id']}")
        return render_template("order.html", order=o, venmo=venmo)

    @app.get("/api/orders/<int:order_id>")
    def order_status(order_id):
        o = _guest_order(order_id)
        return jsonify(order_public(o))

    # ------------------------------------------------------------------ bartender
    @app.route("/login", methods=["GET", "POST"])
    def login():
        err = None
        if request.method == "POST":
            if secrets.compare_digest(request.form.get("pin", ""), str(cfg.get("bartender_pin", ""))):
                session["bartender"] = True
                session.permanent = True
                nxt = request.args.get("next", "/bar")
                return redirect(nxt if nxt.startswith("/") else "/bar")
            err = "Wrong PIN"
        return render_template("login.html", error=err)

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect("/")

    @app.get("/bar")
    @bartender_required
    def bar():
        return render_template("bar.html")

    @app.get("/api/bar/state")
    @bartender_required
    def bar_state():
        return jsonify(machine=machine.snapshot(),
                       orders=[order_public(o) for o in store.active()],
                       cup_mode=cfg.get("cup_mode", "glass"),
                       payment_mode=cfg.get("payment_mode", "tab"))

    def _bar_action(order_id, allowed, new_status):
        o = store.get(order_id)
        if not o:
            return jsonify(error="No such order"), 404
        if o["status"] not in allowed:
            return jsonify(error=f"Order is {o['status']}"), 409
        store.set_status(order_id, new_status)
        machine.maybe_autostart()
        return jsonify(ok=True)

    @app.post("/api/bar/orders/<int:order_id>/approve")
    @bartender_required
    def approve(order_id):
        return _bar_action(order_id, ("new",), "queued")

    @app.post("/api/bar/orders/<int:order_id>/cancel")
    @bartender_required
    def cancel(order_id):
        return _bar_action(order_id, ("new", "queued", "ready"), "cancelled")

    @app.post("/api/bar/orders/<int:order_id>/picked_up")
    @bartender_required
    def picked_up(order_id):
        return _bar_action(order_id, ("ready",), "done")

    @app.post("/api/bar/orders/<int:order_id>/pour")
    @bartender_required
    def pour(order_id):
        o = store.get(order_id)
        if o and o["status"] == "queued" and o["note"]:
            store.set_status(order_id, "queued", note="")  # bartender confirmed cup was dumped
        ok, msg = machine.start_order(order_id)
        return (jsonify(ok=True), 200) if ok else (jsonify(error=msg), 409)

    @app.post("/api/bar/stop")
    @bartender_required
    def stop():
        machine.emergency_stop()
        return jsonify(ok=True)

    @app.post("/api/bar/clear")
    @bartender_required
    def clear():
        machine.clear_error()
        return jsonify(ok=True)

    # ------------------------------------------------------------------ admin
    @app.get("/admin")
    @bartender_required
    def admin():
        rows = []
        for p in cfg["pumps"]:
            ing = p.get("ingredient")
            rows.append({"id": p["id"], "gpio": p["gpio"],
                         "ingredient": cfg["ingredients"][ing]["name"] if ing else "(empty)",
                         "ml_per_sec": round(calibration.ml_per_sec(p), 3)})
        return render_template("admin.html", pumps=rows, history=store.recent(30))

    def _pump(pid):
        for p in cfg["pumps"]:
            if p["id"] == pid:
                return p
        abort(404)

    @app.post("/api/admin/run")
    @bartender_required
    def admin_run():
        """Run one pump (prime / calibrate) or all pumps (clean) for N seconds."""
        data = request.get_json(force=True, silent=True) or {}
        seconds = max(0.1, min(float(data.get("seconds", 2)), 60.0))
        if data.get("pump_id") == "all":
            jobs = [(p["id"], seconds) for p in cfg["pumps"]]
            label = f"Running all pumps {seconds:g}s"
        else:
            p = _pump(int(data.get("pump_id", 0)))
            jobs = [(p["id"], seconds)]
            label = f"Pump {p['id']} for {seconds:g}s"
        ok, msg = machine.run_maintenance(jobs, label)
        return (jsonify(ok=True), 200) if ok else (jsonify(error=msg), 409)

    @app.post("/api/admin/calibrate")
    @bartender_required
    def admin_calibrate():
        data = request.get_json(force=True, silent=True) or {}
        p = _pump(int(data.get("pump_id", 0)))
        seconds = float(data.get("seconds", 0))
        measured = float(data.get("measured_ml", 0))
        if seconds <= 0 or measured <= 0:
            return jsonify(error="Enter the seconds run and ml measured"), 400
        rate = measured / seconds
        calibration.set(p["id"], rate)
        return jsonify(ok=True, ml_per_sec=round(rate, 3))

    @app.get("/qr")
    @bartender_required
    def qr_page():
        return render_template("qr.html")

    @app.get("/qr.png")
    def qr_png():
        import qrcode
        img = qrcode.make(cfg["guest_url"], box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")

    return app


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    app = create_app()
    cfg = app.config["DRINKBOT"]
    port = int(os.environ.get("PORT", cfg.get("port", 8080)))
    mode = "MOCK (no GPIO)" if app.config["PUMPS"].mock else "REAL GPIO"
    logging.getLogger("drinkbot").info("DrinkBot starting on port %s — %s", port, mode)
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        app.run(host="0.0.0.0", port=port, threaded=True)
    finally:
        app.config["PUMPS"].close()
