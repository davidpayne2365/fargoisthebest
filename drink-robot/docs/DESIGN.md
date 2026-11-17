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

Every pump a drink needs runs at the same time (`max_simultaneous_pumps: 6`), so a
drink takes as long as its biggest ingredient. Cheap pumps (~100 ml/min) are fine
for spirits, but 135 ml of juice takes ~80 s — so the **3 big juices (orange,
cranberry, pineapple) get fast ~400 ml/min pumps**. Result for the 25 drinks:

| Setup | Average | Slowest | Under 60 s |
|---|---|---|---|
| All cheap pumps | 51 s | 99 s | 17 of 25 |
| Cheap + 3 fast juice pumps (**chosen**) | 27 s | 36 s | 25 of 25 |
| All fast pumps (~$400 more) | 13 s | 25 s | 25 of 25 |

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

### 6. 16 pumps, no fizzy drinks
**16 bottles** (9 spirits/liqueurs + 7 still mixers — see [BOTTLES.md](BOTTLES.md))
make **25 drinks**, and the robot pours 100% of each one. Fizzy mixers foam and go
flat in pumps, so they're **switched off**: no bartender top-ups, and cup-stack mode
works with zero hand work. The fizzy recipes are still in the config (off) in case
we add a CO₂ soda system later. Grenadine pours *after* everything else
(`pour_last`) so a Tequila Sunrise actually looks like a sunrise.

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

1. ~~How many bottles?~~ **Decided: 16**, no fizz. (Start with 8 if budget's tight — the menu adapts.)
2. **Pump speed vs. price.** Start cheap (100 ml/min, ~$10 each) or go straight to ~400 ml/min (~$30–40 each)?
3. **Ice.** Options: bartender scoops ice in before POUR (glass mode); pre-iced cups in the stack (melts); or chill all bottles/juices in a mini-fridge with tubes running out (nicest, more work).
4. **Bottle layout.** Upside-down bottles on a shelf above (gravity helps, but they can siphon when idle!) vs. upright bottles with tubes dipped in (safer — recommended).
5. ~~Carbonated mixers?~~ **Decided: no fizz.** v2 idea: CO₂ keg + solenoid valve so the robot pours soda itself.
11. ~~Gin only made a Gimlet~~ **Decided: swapped gin for amaretto** (+4 drinks).
6. **Juice freshness.** OJ/lime spoil in the tubes over a night — fine for a party, flush after.
7. **Cup sensor?** A $3 IR sensor confirms a cup is there before pouring. Worth adding in v2.
8. **Weight sensor?** A load cell (HX711) under the cup could measure exactly what poured and auto-detect pickup. Cool v3 upgrade.
9. **Lights/sound.** An LED ring around the nozzle that glows green when a drink is ready?
10. **Name.** "DrinkBot" is a placeholder 😄
