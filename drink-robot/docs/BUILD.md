# Build guide

## Phase 0 — Prove it on the bench (1 evening)
1. Run the app on your laptop in mock mode (see README) and play with it on your phone.
2. Flash the Pi (below), wire **one** pump + one MOSFET, and pump water from a glass.
3. Calibrate it. Pour 3 "drinks" of water and measure — you should be within a few ml.

## Phase 1 — Set up the Raspberry Pi
1. Install **Raspberry Pi Imager** on your computer → choose *Raspberry Pi OS Lite (64-bit)*.
2. Click the ⚙ / "Edit settings":
   * hostname: **`drinkbot`**  (gives you `http://drinkbot.local:8080`)
   * enable SSH, set username/password
   * enter your home Wi-Fi
3. Boot the Pi, then from your computer: `ssh <user>@drinkbot.local`
4. Get the code onto it:
   ```bash
   sudo apt-get install -y git
   git clone https://github.com/<you>/<repo>.git
   cd <repo>/drink-robot        # or just drink-robot if it's its own repo
   bash scripts/install.sh
   ```
5. On your phone (same Wi-Fi) open `http://drinkbot.local:8080`. 🎉
   If `.local` doesn't resolve on someone's phone, find the Pi's IP with
   `hostname -I`, give it a reserved IP in your router, and put that IP in
   `guest_url` in `config.yaml`.

**Party Wi-Fi option:** guests must be on the same network as the Pi. Easiest is
a guest network on your router. Or make the Pi its own hotspot:
`sudo nmcli device wifi hotspot ssid DrinkBot password cheers1234` (then the Pi
is at `http://10.42.0.1:8080`). Print a Wi-Fi QR with
`python3 scripts/make_qr.py --wifi DrinkBot cheers1234`.

## Phase 2 — Frame
A simple layout that works:
```
   ┌───────────────────────────────────────┐
   │  [bottle][bottle][bottle][bottle] ... │  ← 2 rows × 8 bottles, upright, tubes dip in
   │  [bottle][bottle][bottle][bottle] ... │    (back row raised ~10 cm so labels show)
   ├───────────────────────────────────────┤
   │  pump pump pump pump pump pump pump   │  ← pumps on the back panel, above cup height
   │  [electronics box]           ║        │
   │                     tubes ══►║ nozzle │
   │                              ▼        │
   │                           [ cup ]     │
   │                      [ drip tray ]    │
   └───────────────────────────────────────┘
```
* Keep **electronics above and behind** the liquid, never under the bottles.
* **Pumps above the bottles' liquid level? Fine** — peristaltic pumps self-prime.
  Avoid bottles mounted *above* the nozzle (upside down): they can siphon through
  an idle pump tube.
* Nozzle: tube ends **pointing straight down, ~2 cm above the cup rim**, all 16 within
  a ~3 cm circle (two rings of 8) so a narrow glass catches everything.
* Put a small cooler/mini-fridge next to the bar for the 5 fizzy mixers.
* Mark the cup spot on the drip tray (a small 3D-printed or wooden "U" stop) so the
  cup is always centered.
* Seal the wood (polyurethane) — it will get sticky.

## Phase 3 — Wire it
Follow [WIRING.md](WIRING.md). Test every channel with the Admin page **before**
connecting liquid.

## Phase 4 — Load, prime, calibrate
1. Edit `config.yaml` so each pump's `ingredient` matches the bottle on it.
   `sudo systemctl restart drinkbot`
2. **Admin → Prime**: tap 5s on each pump until liquid reaches the nozzle.
3. **Admin → Calibrate**: cup under the nozzle, *Run 10s*, measure the ml (a kitchen
   scale in grams is easiest — ≈1 g/ml for juice/syrup; spirits are ~0.95 g/ml, close
   enough), type it in, *Save*. Do this per pump — syrup pumps slower than vodka.
4. Make yourself a test drink. Adjust recipes to taste in `config.yaml`.

## Phase 5 — Party mode
* Print the QR from `/qr` (or `python3 scripts/make_qr.py`) and stick it on the bar.
* Bartender opens `/bar` on a tablet, logs in, taps **Enable sound alerts**.
* Choose `cup_mode` and `payment_mode` in `config.yaml`.

## Cleaning (every time you use it)
1. Bottles off. Intake tubes into a jug of **warm water** → Admin → **Run all 45s**.
2. Repeat with a little dish soap, then plain water again.
3. Tubes in the air → **Run all 20s** to push out the water.
4. Every few months, replace the pump's silicone tube sections (they wear).

## Troubleshooting
| Symptom | Fix |
|---|---|
| Page says MOCK MODE on the Pi | `gpiozero` isn't visible: re-run `scripts/install.sh` (venv must use `--system-site-packages`) |
| Pump runs backwards | Swap its two motor wires |
| A pump runs at boot | Wrong pin / relay board active-low issue — see WIRING.md |
| Drinks too weak/strong | Re-calibrate that pump; check the tube end is at the bottom of the bottle |
| Pump hums but doesn't pump | Tube not seated in the roller, or 12 V supply too weak — lower `max_simultaneous_pumps` |
| Logs | `journalctl -u drinkbot -f` |
