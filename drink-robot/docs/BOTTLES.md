# The bottles

**16 bottles on pumps + 5 fizzy mixers poured by hand = 38 drinks.**

## On pumps (16)

| Pump | Bottle | Notes |
|---|---|---|
| 1 | Vodka | The workhorse. Mid-shelf is fine (Tito's, Smirnoff). |
| 2 | Gin | London dry (Tanqueray, Beefeater, Gordon's). |
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

## Poured by hand — keep in a cooler (5)

Cola · Tonic water · Soda water · Ginger beer · Lemon-lime soda (Sprite/7UP)

Out of something? Set `in_stock: false` on it in `config.yaml` and every drink
that needs it disappears from the menu.

## Extras behind the bar (optional)
Bitters (Old Fashioned), oranges for peel, fresh mint (Mojito), maraschino cherries
(Shirley Temple), limes/lemons for wedges, **lots of ice**.

## The 38-drink menu

| Base | Drinks |
|---|---|
| **Vodka** (11) | Screwdriver · Vodka Cranberry · Vodka Soda* · Vodka Tonic* · Moscow Mule* · Madras · Bay Breeze · Sex on the Beach · Cosmopolitan · Lemon Drop · Kamikaze |
| **Gin** (3) | Gin & Tonic* · Tom Collins* · Gimlet |
| **Rum** (9) | Rum & Coke* · Spiced Rum & Coke* · Mojito* · Daiquiri · Rum & Ginger (Stormy)* · Garage Mai Tai · Rum Punch · Coconut Rum & Pineapple · Malibu Bay Breeze |
| **Tequila** (4) | Margarita · Tequila Sunrise · Ranch Water* · Mexican Mule* |
| **Whiskey** (5) | Whiskey & Coke* · Whiskey Ginger* · Whiskey Sour · Old Fashioned · Lynchburg Lemonade* |
| **Mixed** (2) | Long Island Iced Tea* · Fuzzy Navel |
| **No alcohol** (4) | Shirley Temple* · Sunrise · Tropical Cooler · Cran-Orange Cooler |

\* = bartender tops with a fizzy mixer after the robot pours.

Most alcoholic drinks also offer **Light / Regular / Strong**, and drinks with a
pumped mixer offer **No alcohol**.

## Common drinks we *can't* do (yet)
| Drink | Missing | Fix |
|---|---|---|
| White Russian, Mudslide, Piña Colada | Cream / coconut cream | Dairy spoils & clogs tubes — pour by hand |
| Martini, Manhattan, Negroni | Vermouth, Campari | Swap peach schnapps or coconut rum for sweet vermouth |
| Paloma | Grapefruit soda | Add it as a 6th hand-pour mixer |
| Amaretto Sour | Amaretto | Swap it in for peach schnapps |
| Blue Hawaiian, AMF | Blue curaçao | Swap it in for coconut rum |
| Shots (Lemon Drop shot, etc.) | — | Easy to add as recipes — ask! |
| Frozen drinks | Blender | Out of scope 😄 |

To swap a bottle: change that pump's `ingredient` in `config.yaml`, restart, prime and
calibrate that pump. Recipes for the new bottle appear automatically.
