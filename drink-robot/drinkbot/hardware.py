"""Hardware layer: pumps and the optional cup sensor.

Pump drivers (config.yaml -> pump_driver):
  gpio      : Raspberry Pi pins -> MOSFET modules (the final build)
  usb_relay : a USB relay board (LCUS / CH340 type) -> works from a laptop
              (Windows, Mac, Linux) or a Pi
  mock      : no hardware, pumps are simulated

GPIO falls back to MOCK automatically when gpiozero isn't installed (e.g. on a
laptop), and DRINKBOT_MOCK=1 forces mock for every driver.
"""
import logging
import os
import threading
import time

log = logging.getLogger("drinkbot.hw")


def want_mock():
    if os.environ.get("DRINKBOT_MOCK") == "1":
        return True
    try:
        import gpiozero  # noqa: F401
        return False
    except ImportError:
        return True


class _MockOutput:
    def __init__(self, pin):
        self.pin = pin
        self.value = 0

    def on(self):
        self.value = 1
        log.info("[mock] GPIO %s ON", self.pin)

    def off(self):
        if self.value:
            log.info("[mock] GPIO %s off", self.pin)
        self.value = 0

    def close(self):
        pass


class UsbRelayBoard:
    """One LCUS-style USB relay board (CH340 serial chip, up to 8 relays).

    Protocol: 4 bytes per command -> 0xA0, channel (1-8), state (0/1), checksum.
    """

    def __init__(self, port, baud=9600, serial_factory=None):
        if serial_factory is None:
            import serial  # pyserial
            serial_factory = serial.Serial
        self.port = port
        self.ser = serial_factory(port, baud, timeout=1)
        self.lock = threading.Lock()

    def set(self, channel, on):
        state = 1 if on else 0
        cmd = bytes([0xA0, channel, state, (0xA0 + channel + state) & 0xFF])
        with self.lock:
            self.ser.write(cmd)
            self.ser.flush()
        time.sleep(0.005)  # these boards drop commands sent back-to-back

    def close(self):
        self.ser.close()


class _RelayOutput:
    def __init__(self, board, channel):
        self.board, self.channel, self.value = board, channel, 0

    def on(self):
        self.board.set(self.channel, True)
        self.value = 1

    def off(self):
        self.board.set(self.channel, False)
        self.value = 0

    def close(self):
        pass


def relay_location(n):
    """Relay number 1..N -> (board index, channel 1-8). Relays 9-16 are on the 2nd board."""
    return (n - 1) // 8, (n - 1) % 8 + 1


class PumpBank:
    def __init__(self, pumps_cfg, max_simultaneous=4, max_seconds=180, mock=None,
                 driver="gpio", usb_relay=None, serial_factory=None):
        if mock is None:
            if os.environ.get("DRINKBOT_MOCK") == "1" or driver == "mock":
                mock = True
            elif driver == "gpio":
                mock = want_mock()
            else:
                mock = False
        self.mock = mock
        self.driver = "mock" if mock else driver
        self.max_simultaneous = max(1, int(max_simultaneous))
        self.max_seconds = float(max_seconds)
        self._stop = threading.Event()
        self._lock = threading.Lock()  # one run at a time
        self.outputs = {}
        self.boards = []
        if self.driver == "usb_relay":
            cfg = usb_relay or {}
            ports = cfg.get("ports") or []
            if not ports:
                raise ValueError("pump_driver is usb_relay but usb_relay.ports is empty in config.yaml")
            self.boards = [UsbRelayBoard(p, cfg.get("baud", 9600), serial_factory) for p in ports]
        for p in pumps_cfg:
            if self.mock:
                dev = _MockOutput(p.get("relay", p["id"]) if driver == "usb_relay" else p["gpio"])
            elif self.driver == "usb_relay":
                b, ch = relay_location(int(p.get("relay", p["id"])))
                if b >= len(self.boards):
                    raise ValueError(f"Pump {p['id']} needs relay board #{b + 1} — add its port to usb_relay.ports")
                dev = _RelayOutput(self.boards[b], ch)
            elif self.driver == "gpio":
                from gpiozero import OutputDevice
                dev = OutputDevice(p["gpio"], active_high=not p.get("active_low", False),
                                   initial_value=False)
            else:
                raise ValueError(f"Unknown pump_driver {self.driver!r}")
            self.outputs[p["id"]] = dev
        self.all_off()

    @property
    def busy(self):
        return self._lock.locked()

    def all_off(self):
        for dev in self.outputs.values():
            try:
                dev.off()
            except Exception:  # never let one bad pin stop the others turning off
                log.exception("failed to switch off pump")

    def stop(self):
        """Emergency stop: abort the current run and kill every pump."""
        self._stop.set()
        self.all_off()

    def run(self, jobs, progress_cb=None):
        """Run pumps. jobs = [(pump_id, seconds), ...] or [(pump_id, seconds, phase), ...].

        Phases run in order (phase 1 starts only after every phase-0 pump has
        stopped). Within a phase the longest jobs start first and at most
        max_simultaneous run at once. Blocks until finished.
        Returns True if completed, False if stopped.
        """
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Pumps are already running")
        try:
            self._stop.clear()
            merged = {}  # (phase, pid) -> seconds
            for job in jobs:
                pid, sec = job[0], float(job[1])
                phase = int(job[2]) if len(job) > 2 else 0
                if pid not in self.outputs:
                    raise ValueError(f"Unknown pump {pid}")
                merged[(phase, pid)] = merged.get((phase, pid), 0.0) + sec
            phases = {}
            for (phase, pid), sec in merged.items():
                if sec > 0:
                    phases.setdefault(phase, []).append((pid, min(sec, self.max_seconds)))
            total = sum(sec for p in phases.values() for _, sec in p) or 1.0
            done = 0.0
            last_report = 0.0

            for phase in sorted(phases):
                pending = sorted(phases[phase], key=lambda j: -j[1])
                active = {}  # pid -> (start, duration)
                while pending or active:
                    if self._stop.is_set():
                        return False
                    now = time.monotonic()
                    for pid, (start, dur) in list(active.items()):
                        if now - start >= dur:
                            self.outputs[pid].off()
                            done += dur
                            del active[pid]
                    while pending and len(active) < self.max_simultaneous:
                        pid, dur = pending.pop(0)
                        self.outputs[pid].on()
                        active[pid] = (time.monotonic(), dur)
                    if progress_cb and now - last_report > 0.25:
                        partial = sum(min(now - s, d) for s, d in active.values())
                        progress_cb(min(1.0, (done + partial) / total))
                        last_report = now
                    self._stop.wait(0.01)
            if progress_cb:
                progress_cb(1.0)
            return True
        finally:
            self.all_off()
            self._lock.release()

    def close(self):
        self.all_off()
        for dev in self.outputs.values():
            dev.close()
        for b in self.boards:
            b.close()


class CupSensor:
    """present() -> True / False, or None when no sensor is configured."""

    def __init__(self, gpio=None, active_low=True, mock=None):
        self.dev = None
        self.mock = want_mock() if mock is None else mock
        self.mock_present = True
        if gpio is not None and not self.mock:
            from gpiozero import DigitalInputDevice
            if active_low:
                self.dev = DigitalInputDevice(gpio, pull_up=True)
            else:
                self.dev = DigitalInputDevice(gpio, pull_up=False)
        self.configured = gpio is not None

    def present(self):
        if not self.configured:
            return None
        if self.dev is None:
            return self.mock_present
        return bool(self.dev.is_active)
