# 🍹 DrinkBot — a garage cocktail robot

A just-for-fun home build: bottles → tubes → pumps → one nozzle. Guests scan a
QR code, pick a drink on their phone, and the bartender's screen says
**"Put a ROCKS glass under the nozzle → POUR"**. The robot pours it, the guest's
phone buzzes, the bartender hands it over.

```
 Guest phone ──Wi-Fi──►  Raspberry Pi (this code)  ──GPIO──► MOSFET boards ──12 V──► 8 pumps ──tubes──► nozzle ──► cup
 Bartender tablet ─────►   web app + order queue
```

| Doc | What's in it |
|---|---|
| [docs/DESIGN.md](docs/DESIGN.md) | Decisions made, why, and **open questions to scheme on** |
| [docs/SHOPPING_LIST.md](docs/SHOPPING_LIST.md) | What to buy (~$200–330) |
| [docs/WIRING.md](docs/WIRING.md) | How to connect it all together |
| [docs/BUILD.md](docs/BUILD.md) | Step-by-step: frame, Pi setup, install, calibrate, clean |

## Try it on your laptop right now (no hardware needed)

```bash
cd drink-robot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DRINKBOT_MOCK=1 python -m drinkbot
```

* Guest menu: <http://localhost:8080/>
* Bartender screen: <http://localhost:8080/bar> (PIN `1234` — change it in `config.yaml`)
* Admin (prime / calibrate / clean): <http://localhost:8080/admin>
* Printable QR code: <http://localhost:8080/qr>

Run the tests: `pytest -q`

## On the Raspberry Pi

```bash
git clone <your repo> drink-robot && cd drink-robot
bash scripts/install.sh        # installs deps + starts at boot
```

## What you'll edit

Everything lives in **`config.yaml`**: which bottle is on which pump, recipes
(in ml), glass sizes, the bartender PIN, payment mode (`none` / `tab` / `venmo`),
and cup mode (`glass` or `stack`). Drinks only show on the menu when all of
their ingredients are on a pump.

## Code map

```
drinkbot/
  recipes.py    config loading, menu filtering, pour planning (ml → pump seconds)
  hardware.py   GPIO pumps + cup sensor (auto mock mode off-Pi)
  machine.py    pours one order at a time in a background thread, e-stop
  orders.py     SQLite order queue (survives restarts)
  server.py     Flask routes: guest, bartender, admin
  templates/    phone-first pages
```

⚠️ Hobby project, not for sale or public use. Booze + electricity + strangers is a
bad mix — keep it to friends, keep 12 V away from spills, and keep a hand on the
STOP button.
