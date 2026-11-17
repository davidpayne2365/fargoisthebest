# Design decisions (and what's still up for debate)

## ✅ Decided — with reasoning

### 1. Brain: Raspberry Pi (not a phone, not an Arduino)
| Option | Verdict |
|---|---|
| **Raspberry Pi 4/5** | ✅ Runs the web server, database and GPIO in one box. Linux, Wi-Fi, Python. Huge community. |
| Pi Zero 2 W | ✅ Also works (cheaper, slower to set up). Fine if you already have one. |
| ESP32 / Arduino | ❌ Great at switching pumps, painful at hosting a nice web app + order queue. |
| Old phone | ❌ Phones can't switch pumps without extra hardware. **Use the old phone/tablet as the bartender screen instead.** |

### 2. Pumps: peristaltic, one per bottle
Peristaltic pumps squeeze a silicone tube — **liquid never touches the motor**
(food-safe, easy to clean), they self-prime, they don't drip much when they stop,
and the amount poured is very repeatable for a given run time. That's why the
software pours by **time**, with a per-pump **calibration** (ml per second).

Trade-off: cheap ones are slow (~100 ml/min). The software runs up to 4 pumps
at once, so a 200 ml drink takes ~30–60 s. Upgrade to ~400 ml/min pumps later if
that's annoying (only `ml_per_sec` changes).

### 3. Ordering flow: guests order, **bartender approves and presses POUR**
You asked "guest orders & pays vs bartender places it — whichever is more
reliable." The answer is a hybrid:

1. Guest scans QR → picks drink + strength + name → **Order**.
2. Bartender screen beeps → bartender taps **Paid / Approve** (cash/tab/Venmo, and a
   chance to check ID or cut someone off). Set `payment_mode: none` to skip this.
3. Screen says **"Put a HIGHBALL glass under the nozzle"** → bartender taps **POUR**.
4. Guest's phone buzzes "Ready!" → bartender hands it over → **Picked up**.

Why a human presses POUR: the #1 way a drink robot fails is pouring onto an
empty drip tray or into an already-full cup. One tap from a person who can see
the cup removes that whole class of failures. (An optional cup sensor adds a
second check.)

### 4. Cups: both of your ideas are supported (`cup_mode` in config)
* **`glass`** (default) — the app tells the bartender which glass each drink wants.
  Classier, but the bartender has to swap glasses.
* **`stack`** — a stack of identical party cups sits under the nozzle; the robot fills
  the **top** cup; the bartender lifts it off when the app says READY. Every drink
  goes in the same cup. Turn on `auto_pour_in_stack_mode` and the robot starts the
  next drink by itself as soon as the previous one is marked *Picked up* — fastest
  for parties. It refuses to pour while a ready drink is still sitting on top.

### 5. No shaking / stirring
Recipes were picked to be "build" drinks that mix fine just from the streams
landing together (several pumps run simultaneously). Shaken classics like the
margarita/daiquiri are fine served over ice — or give it a quick swirl.

### 6. 16 pumps, fizzy mixers poured by hand
To cover the most-ordered drinks we went to **16 bottles** (9 spirits/liqueurs + 7
still mixers — see [BOTTLES.md](BOTTLES.md)). Fizzy mixers (cola, tonic, soda, ginger
beer, lemon-lime) foam and go flat in pumps, so they stay cold in a cooler and the
bartender screen says **"After the robot: top with ~150 ml Cola"**. Grenadine can be
set to pour *after* everything else (`pour_last`) so a Tequila Sunrise actually looks
like a sunrise.

### 7. Payments: no card processing
Real card payments need internet, HTTPS, a Stripe account and a business — overkill
for a garage. Modes: `none` (free), `tab` (bartender approves, settle in cash),
`venmo` (guest gets a Venmo link with the amount pre-filled; bartender approves
when it lands).

### 8. Safety built into the software
* Hard caps: `max_pour_ml`, per-glass `max_ml`, `max_pump_seconds`.
* **STOP** button on every bartender screen kills all pumps instantly.
* A drink stopped mid-pour (or interrupted by a power cut) is flagged
  *"dump the cup before re-pouring"* and is **never** auto-repoured.
* All pumps are switched off on startup, on shutdown, and after every pour.
* PIN-protected bartender/admin pages.
* **Plus** a physical E-stop switch on the 12 V line (see WIRING) — never rely on software alone.

## ❓ Open questions to scheme on

1. ~~How many bottles?~~ **Decided: 16** + 5 hand-poured fizzy mixers. (Start with 8 if budget's tight — the menu adapts.)
2. **Pump speed vs. price.** Start cheap (100 ml/min, ~$10 each) or go straight to ~400 ml/min (~$30–40 each)?
3. **Ice.** Options: bartender scoops ice in before POUR (glass mode); pre-iced cups in the stack (melts); or chill all bottles/juices in a mini-fridge with tubes running out (nicest, more work).
4. **Bottle layout.** Upside-down bottles on a shelf above (gravity helps, but they can siphon when idle!) vs. upright bottles with tubes dipped in (safer — recommended).
5. ~~Carbonated mixers?~~ **Decided: hand-poured** top-ups. v3 idea: a CO₂ soda gun with solenoid valves.
6. **Juice freshness.** OJ/lime spoil in the tubes over a night — fine for a party, flush after.
7. **Cup sensor?** A $3 IR sensor confirms a cup is there before pouring. Worth adding in v2.
8. **Weight sensor?** A load cell (HX711) under the cup could measure exactly what poured and auto-detect pickup. Cool v3 upgrade.
9. **Lights/sound.** An LED ring around the nozzle that glows green when a drink is ready?
10. **Name.** "DrinkBot" is a placeholder 😄
