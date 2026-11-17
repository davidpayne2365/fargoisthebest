# Wiring

> ⚡ Only **12 V DC** goes anywhere near liquid. The 12 V supply's mains (wall)
> side stays in its enclosure, away from the bar. Never open a mains PSU.

## Big picture

```
 WALL ──► [12 V 10 A PSU] ──► [10 A fuse] ──► [E-STOP (NC)] ──► 12 V+ bus ──┬──► Pump 1 (+)
                     │                                                     ├──► Pump 2 (+)
                     │                                                     └──► ... Pump 8 (+)
                     └── 12 V− (GND) ───────────────────────────────────► GND bus

 Pump N (−) ──► MOSFET module N  OUT−      MOSFET module N  OUT+ ◄── 12 V+ bus  (if module has OUT+, else not needed)
                MOSFET module N  VIN+/VIN− ◄── 12 V+ bus / GND bus
                MOSFET module N  SIG/PWM   ◄── Pi GPIO (see table)
                MOSFET module N  GND       ◄── Pi GND   ← COMMON GROUND, essential

 WALL ──► [Official Pi PSU] ──► Raspberry Pi
```

Hitting the E-stop cuts power to **every pump** no matter what the software is doing.
The Pi stays on, so the app just shows the pour as stopped.

## Pin map (matches `config.yaml`)

| Pump | GPIO (BCM) | Physical pin on Pi header |
|---|---|---|
| 1 | GPIO 17 | 11 |
| 2 | GPIO 27 | 13 |
| 3 | GPIO 22 | 15 |
| 4 | GPIO 23 | 16 |
| 5 | GPIO 24 | 18 |
| 6 | GPIO 25 | 22 |
| 7 | GPIO 12 | 32 |
| 8 | GPIO 13 | 33 |
| GND (to every MOSFET module's signal GND) | GND | 6, 9, 14, 20, 25, 30, 34 or 39 |
| *(optional)* cup sensor OUT | GPIO 16 | 36 |
| *(optional)* cup sensor VCC | 3.3 V | 1 |

Pin 1 is the corner pin nearest the microSD card side with the square pad — look up
"Raspberry Pi pinout" (or run `pinout` on the Pi) to be sure.

All eight pump pins are pulled **down** while the Pi boots, so active-high MOSFET
modules stay **off** until the software takes over. Don't move pumps to GPIO 0–8:
those are pulled **up** at boot and would run the pump while the Pi starts.

## One pump channel, close up

```
              12 V+ ─────────────┬──────────────── Pump (+) red
                                 │
                            ┌────┴────┐  flyback diode: stripe (cathode) toward 12 V+
                            │  1N5819 │
                            └────┬────┘
                                 │
  MOSFET module "OUT−" / "LOAD−" ┴──────────────── Pump (−) black
  MOSFET module "VIN−"/"GND"  ───────────────────── 12 V GND bus
  MOSFET module "SIG"/"TRIG"  ───────────────────── Pi GPIO (e.g. 17)
  MOSFET module signal "GND"  ───────────────────── Pi GND
```

Label names vary by module — read the silkscreen. What matters: **load side** goes
between pump(−) and 12 V ground; **trigger side** gets the Pi GPIO and Pi GND.

**Pump direction:** if a pump sucks the wrong way, swap its two motor wires.

## Optional cup sensor (FC-51 IR module)
VCC → 3.3 V (pin 1), GND → GND, OUT → GPIO 16. Point it sideways at where the
cup sits. Then set in `config.yaml`:
```yaml
cup_sensor: { gpio: 16, active_low: true }
```

## Test before connecting pumps
1. Install the software, open **Admin**, tap a pump's **2s** button.
2. The MOSFET module's LED should light for 2 s. Check all 8.
3. Now connect pumps + 12 V and repeat with water.

## Using a relay board instead
Set `active_low: true` on every pump in `config.yaml`, and on the board **remove the
JD-VCC jumper**: board VCC → Pi **3.3 V**, JD-VCC → Pi **5 V**, GND → GND. Then the
relays switch fully off from the Pi's 3.3 V. Expect some clicking. Pumps may briefly
run during boot — keep the E-stop pressed until the app is up, or use the MOSFETs.
