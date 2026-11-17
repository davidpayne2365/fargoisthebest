# The bottles

**16 bottles, all on pumps → 25 drinks. No fizzy mixers.** The robot makes 100% of
every drink, so the bartender only hands the cup over (perfect for cup-stack mode).

## On pumps (16)

| Pump | Bottle | Notes |
|---|---|---|
| 1 | Vodka | The workhorse. Mid-shelf is fine (Tito's, Smirnoff). |
| 2 | Amaretto | Disaronno, or a cheaper store brand — it's mixed anyway. |
| 3 | White rum | Bacardi or similar. |
| 4 | Spiced rum | Captain Morgan / Kraken. |
| 5 | Coconut rum | Malibu. |
| 6 | Tequila | Blanco / silver (100% agave is worth it). |
| 7 | Whiskey | Bourbon or Tennessee (Jack, Jim Beam, Maker's). |
| 8 | Triple sec | Orange liqueur (Cointreau if you're fancy). |
| 9 | Peach schnapps | For Sex on the Beach / Fuzzy Navel. |
| 10 | Lime juice | Bottled 100% juice works; fresh is better. Refrigerate. |
| 11 | Lemon juice | Same. |
| 12 | Simple syrup | 1 cup sugar + 1 cup hot water, stir, cool. Keeps weeks in the fridge. |
| 13 | Orange juice | Pulp-free! Pulp clogs tubes. |
| 14 | Cranberry juice | Cranberry *cocktail* (Ocean Spray). |
| 15 | Pineapple juice | Canned/bottled. |
| 16 | Grenadine | Pours last in Sunrise drinks so it sinks. |

## The 25-drink menu

| Base | Drinks |
|---|---|
| **Vodka** (8) | Screwdriver · Vodka Cranberry · Madras · Bay Breeze · Sex on the Beach · Cosmopolitan · Lemon Drop · Kamikaze |
| **Rum** (5) | Daiquiri · Garage Mai Tai · Rum Punch · Coconut Rum & Pineapple · Malibu Bay Breeze |
| **Tequila** (2) | Margarita · Tequila Sunrise |
| **Whiskey** (2) | Whiskey Sour · Old Fashioned (bartender adds a dash of bitters if you have them — optional) |
| **Amaretto** (4) | Amaretto Sour (with a splash of whiskey) · Godfather (whiskey + amaretto) · Amaretto Sunrise · Amaretto Cranberry |
| **Other** (1) | Fuzzy Navel |
| **No alcohol** (3) | Sunrise · Tropical Cooler · Cran-Orange Cooler |

Most alcoholic drinks also offer **Light / Regular / Strong**, and ones with juice
offer **No alcohol**.

## Extras behind the bar (optional)
Ice (lots), limes/oranges for garnish, bitters for the Old Fashioned.

## Want fizzy drinks back later?
The 5 fizzy mixers (cola, tonic, soda water, ginger beer, lemon-lime) and their 16
recipes are still in `config.yaml`, just switched off. Change `in_stock: false` →
`true` on any of them and those drinks return (Rum & Coke, Vodka Tonic, Moscow Mule,
Whiskey & Coke, …) — the bartender screen then says "top with ~150 ml Cola".
The proper v2 fix is a CO₂ keg + solenoid valve so the robot pours soda itself.

## Future swap ideas
Gin was swapped for amaretto (gin only made a Gimlet without tonic). Its recipes are
still in the config — put gin back on a pump and they return. Other ideas:

| Swap … for | Adds |
|---|---|
| Coconut rum → Midori (melon) | Midori Sour, Melon Ball, Japanese Slipper |
| Any → Blue curaçao | Blue Margarita, Blue Kamikaze, Electric Lemonade |
| Any → Sweet vermouth | Manhattan (goes stale in weeks unless refrigerated) |

## Common drinks we *can't* do
| Drink | Why |
|---|---|
| Anything with soda (Rum & Coke, G&T, Mule, Long Island…) | Fizz switched off — see above |
| White Russian, Mudslide, Piña Colada | Cream spoils & clogs tubes |
| Gin drinks (Gimlet, Martini, Negroni) | Gin swapped out for amaretto |
| Manhattan | Needs sweet vermouth |
| Frozen drinks | Needs a blender 😄 |

To swap a bottle: change that pump's `ingredient` in `config.yaml`, restart, prime and
calibrate that pump. Recipes for the new bottle appear automatically.
