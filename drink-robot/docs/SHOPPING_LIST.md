# Shopping list

Prices are rough USD (2026), Amazon/AliExpress/Adafruit-type sources. Search terms
in quotes are what to type in. **Total ≈ $330–750** for the 16-bottle build, mostly depending on pump choice.
You can start with fewer pumps and add more later — drinks appear on the menu
automatically as their bottles get a pump.

## Core electronics
| Qty | Item | Search for | ~$ |
|---|---|---|---|
| 1 | Raspberry Pi 4 (2 GB+) **or** Pi 5 (2 GB+) | "Raspberry Pi 4 Model B 2GB" | 45–60 |
| 1 | Official Pi power supply (USB-C, 5 V 3 A for Pi 4 / 5 A for Pi 5) | "Raspberry Pi official power supply" | 8–12 |
| 1 | microSD card 32 GB (A1/A2) | "SanDisk 32GB microSD A1" | 8 |
| 13 + 3 | 12 V peristaltic pumps, food-grade silicone tube — **cheap ones for spirits/syrups, 3 fast ones for orange, cranberry & pineapple** (juice is the slow part: this alone takes the slowest drink from ~99 s to ~36 s) | budget: "12V peristaltic pump 100ml/min" · faster: "Kamoer KPHM400 12V" or "12V peristaltic pump 400ml/min" | 16×10 = 160 · or 16×35 = 560 |
| 16 | MOSFET switch modules, 3.3 V logic compatible | "D4184 MOSFET module" or "IRLZ44N MOSFET module" (two 10-packs) | 20 |
| 16 | Flyback diodes (one per pump) | "1N5819 Schottky diode" or "1N4007" (pack of 50) | 5 |
| 1 | 12 V DC power supply, **10 A** (enough for 4+ pumps at once with headroom) | "12V 10A power supply" (brick with barrel jack, or enclosed LED-strip PSU) | 20 |
| 1 | Barrel-jack-to-screw-terminal adapter (if brick PSU) | "DC barrel jack female screw terminal" | 5 |
| 1 | Big red **E-stop** mushroom switch (latching, normally closed) | "emergency stop button 22mm NC" | 8 |
| 1 | Inline fuse holder + 10 A fuse for the 12 V line | "inline blade fuse holder 10A" | 5 |
| 1 | GPIO screw-terminal breakout/HAT (makes 16 signal wires sane) | "Raspberry Pi GPIO screw terminal HAT" | 12 |
| 1 | Wire kit: Dupont female jumper wires + 18–20 AWG red/black hookup wire | "dupont jumper wire female" + "20 AWG silicone wire red black" | 15 |
| 1 | Lever connectors / terminal strips for 12 V and GND distribution | "Wago 221" or "terminal block bus bar" | 10 |
| 1 | Project box for the electronics (keep it ABOVE the spill zone) | "ABS project box 200x120" | 10 |

## Bottles & mixers
See [BOTTLES.md](BOTTLES.md) for the full list of 16 bottles.

## Fluid path
| Qty | Item | Search for | ~$ |
|---|---|---|---|
| ~12 m | Food-grade silicone tubing that **matches your pump's tube size** (check pump listing, often 2×4 mm or 3×5 mm ID×OD) | "food grade silicone tubing 3mm ID" | 10 |
| 1 set | Barbed connectors/joiners in that size | "barbed tube connector 3mm food grade" | 6 |
| 16 | Bottle caps / pour spouts the tube can pass through (drill a tube hole **and** a small air hole) | "liquor pour spout" or spare caps | 8 |
| 16 | Small stainless weights to keep tube ends at the bottom of each bottle | "stainless steel tube weight" or a short stainless straw section | 8 |
| 1 | Nozzle block — 3D-print one, or drill 16 holes (two rings of 8) in a piece of HDPE cutting board | "HDPE cutting board" | 10 |
| 1 | Drip tray with grate | "bar drip tray" | 10 |

## Frame
| Item | ~$ |
|---|---|
| ¾" plywood (4'×4' — 16 bottles is ~4 ft wide in one row, or two 2-ft rows) + 2×2s, screws, wood glue, polyurethane/paint so spills wipe off | 30–40 |
| Or: aluminium extrusion 2020 kit (cleaner, pricier) | 50–80 |

## Optional / later
| Item | Why | ~$ |
|---|---|---|
| IR obstacle sensor module ("FC-51 IR obstacle sensor") | Detects a cup before pouring | 3 |
| Old tablet/phone + stand | Bartender screen | 0 |
| HX711 + 5 kg load cell | v3: weigh pours, auto-detect pickup | 10 |
| WS2812 LED ring | Glows when a drink's ready | 8 |
| Mini fridge | Cold juice/booze, tubes run out the door seal | — |

## Why MOSFETs instead of a relay board?
The classic "8-channel relay module" works, but most are **active-low**: on many Pi
pins they switch **ON while the Pi is booting**, and they don't fully switch off from
the Pi's 3.3 V signal unless you rewire the JD-VCC jumper. MOSFET modules are
active-high (off by default), silent, never wear out, and run happily from 3.3 V.
If you already own a relay board, see the note at the end of WIRING.md.
