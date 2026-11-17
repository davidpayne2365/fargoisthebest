"""The robot's brain: pours one order at a time in a background thread."""
import logging
import threading
import time

log = logging.getLogger("drinkbot.machine")


class Machine:
    def __init__(self, cfg, store, pumps, cup_sensor):
        self.cfg = cfg
        self.store = store
        self.pumps = pumps
        self.cup = cup_sensor
        self.lock = threading.Lock()
        self.state = {"status": "idle", "order_id": None, "label": "", "progress": 0.0,
                      "message": "", "since": time.time()}

    # ---------- state helpers ----------
    def snapshot(self):
        with self.lock:
            s = dict(self.state)
        s["cup_present"] = self.cup.present()
        s["mock"] = self.pumps.mock
        return s

    def _set(self, **kw):
        with self.lock:
            self.state.update(kw)
            self.state["since"] = time.time()

    @property
    def busy(self):
        return self.pumps.busy or self.state["status"] == "pouring"

    def _cup_ok(self):
        present = self.cup.present()
        return present is None or present

    # ---------- orders ----------
    def start_order(self, order_id):
        order = self.store.get(order_id)
        if not order or order["status"] != "queued":
            return False, "Order is not queued"
        if self.busy:
            return False, "Robot is busy"
        if not self._cup_ok():
            return False, "No cup detected under the nozzle"
        jobs = [(s["pump_id"], s["seconds"]) for s in order["steps"]]
        self.store.set_status(order_id, "pouring", note="")
        self._set(status="pouring", order_id=order_id, progress=0.0,
                  label=f"#{order_id} {order['recipe_name']} for {order['guest']}", message="")
        threading.Thread(target=self._pour, args=(order_id, jobs), daemon=True).start()
        return True, "Pouring"

    def _pour(self, order_id, jobs):
        try:
            ok = self.pumps.run(jobs, progress_cb=lambda p: self._set_progress(p))
        except Exception as e:  # hardware problem
            log.exception("pour failed")
            self.store.set_status(order_id, "queued", note=f"Pour failed: {e} — dump cup before re-pouring")
            self._set(status="error", order_id=None, message=str(e))
            return
        if ok:
            self.store.set_status(order_id, "ready")
            self._set(status="idle", order_id=None, progress=0.0, label="", message="")
        else:
            self.store.set_status(order_id, "queued", note="Stopped mid-pour — dump the cup before re-pouring")
            self._set(status="stopped", order_id=None, progress=0.0, label="",
                      message="Emergency stop pressed")

    def _set_progress(self, p):
        with self.lock:
            self.state["progress"] = round(p, 3)

    def maybe_autostart(self):
        """Stack mode: if the top cup is free, start the next drink on its own."""
        if self.cfg.get("cup_mode") != "stack" or not self.cfg.get("auto_pour_in_stack_mode"):
            return
        if self.busy:
            return
        if any(o["status"] == "ready" for o in self.store.active()):
            return  # top cup still full — wait for pickup
        nxt = self.store.next_queued()
        if nxt and not nxt["note"]:  # never auto-repour an interrupted drink
            self.start_order(nxt["id"])

    # ---------- maintenance ----------
    def run_maintenance(self, jobs, label):
        if self.busy:
            return False, "Robot is busy"
        self._set(status="pouring", order_id=None, progress=0.0, label=label, message="")

        def work():
            try:
                ok = self.pumps.run(jobs, progress_cb=self._set_progress)
                self._set(status="idle" if ok else "stopped", label="", progress=0.0,
                          message="" if ok else "Emergency stop pressed")
            except Exception as e:
                log.exception("maintenance failed")
                self._set(status="error", label="", message=str(e))

        threading.Thread(target=work, daemon=True).start()
        return True, "Started"

    def emergency_stop(self):
        # The pour thread notices the stop, flips state to 'stopped' and
        # flags the half-poured order so it is never silently re-poured.
        self.pumps.stop()

    def clear_error(self):
        if not self.busy:
            self._set(status="idle", message="")
