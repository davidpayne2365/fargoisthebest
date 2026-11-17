# Test with real pumps on your laptop (before buying a Pi)

A laptop has no pins to switch pumps, so a **USB relay board** sits in between:

```
Laptop ──USB──► USB relay board ──switches 12 V──► pumps ──tubes──► cup
                         ▲
              12 V power supply
```

The same relay board plugs into the Pi later, so nothing is wasted.

## Buy for the laptop test (~$110–150 for 8 pumps)

| Qty | Item | What to check in the listing |
|---|---|---|
| 1 | 8-channel **USB relay board**, "LCUS-8" / CH340 type | Says "USB control", "CH340" or "LCUS", and shows serial commands like `A0 01 01 A2`. Avoid "HID" boards. Check whether it needs extra power (some take 5 V or 12 V on a screw terminal) |
| 8 | 12 V peristaltic pumps, food-grade silicone tube | 12 V DC, "food grade". Note the tube size (e.g. 2×4 mm or 3×5 mm) |
| 1 | 12 V power supply, 5–10 A, barrel plug | Plus a barrel-jack-to-screw-terminal adapter |
| ~5 m | Food-grade silicone tubing | **Same inner/outer size as the pump's tube** |
| 8 | 1N5819 or 1N4007 diodes | One across each pump (optional but kind to the relays) |
| — | Hookup wire (18–20 AWG), Wago lever connectors | |

16 pumps = two relay boards. Start with 8.

## Wiring one pump

```
12 V supply (+) ──► relay COM ─(relay closes)─► relay NO ──► pump (+) red
12 V supply (−) ──────────────────────────────────────────► pump (−) black
Diode across the pump: stripe end on pump (+)
```
Daisy-chain 12 V (+) to every relay's COM. Pump 1 → relay 1, pump 2 → relay 2, …

## Software (Windows or Mac)

1. Install **Python 3** from python.org (Windows: tick "Add Python to PATH").
2. Install the **CH340 driver** if the board isn't detected (Windows/Mac; search "CH340 driver").
3. Get the code: `git clone -b claude/diy-drink-robot-xno9yt https://github.com/davidpayne2365/fargoisthebest.git`
   (or GitHub → Code → Download ZIP on that branch), then open a terminal in `fargoisthebest/drink-robot`.
4. Set up:
   ```
   python -m venv .venv
   .venv\Scripts\activate          (Windows)
   source .venv/bin/activate       (Mac)
   pip install -r requirements.txt
   ```
5. Find the board: `python -m drinkbot.relaytest` → note the port (e.g. `COM3` or `/dev/cu.usbserial-110`).
6. Click test (no pumps needed): `python -m drinkbot.relaytest COM3` → you should hear relays 1–8 click.
7. Edit `config.yaml`:
   ```yaml
   pump_driver: usb_relay
   usb_relay:
     ports: ["COM3"]
   ```
   and set `ingredient:` on pumps 1–8 to what's actually connected. Pumps 9–16 need a 2nd board; for now
   delete them from the list (or the app will ask for a 2nd port).
8. Run it: `python -m drinkbot` → open http://localhost:8080 (guest) and http://localhost:8080/bar (PIN 1234).
   Phones on the same Wi-Fi can use `http://<laptop-ip>:8080` (allow Python through the firewall).
9. Test with **water** first: Admin → Prime, then Calibrate each pump (10 s into a measuring cup).

When the Pi arrives, either keep the relay board (`pump_driver: usb_relay`, port `/dev/ttyUSB0`) or
move to MOSFET modules (`pump_driver: gpio`, see WIRING.md).
