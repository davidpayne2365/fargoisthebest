#!/usr/bin/env python3
"""Build the static demo website (no Pi needed) from config.yaml.

  python3 scripts/build_site.py            # -> site/dist/index.html + drinks.html

The output is plain HTML you can host anywhere (Netlify, GitHub Pages) or open
from disk. The robot is simulated; the menu, prices and pictures come straight
from config.yaml, so rebuild after changing recipes.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from drinkbot import recipes as R  # noqa: E402

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700'
         '&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap">')


def drink_data(cfg):
    cal = R.Calibration(os.path.join(ROOT, "data", "calibration.json"))
    out = []
    for r in R.available_recipes(cfg):
        plans = {}
        for st in R.allowed_strengths(cfg, r):
            steps = R.plan_pour(cfg, r, st, cal)
            plans[st] = {"steps": [{"n": s["name"], "ml": s["ml"], "last": s["phase"] == 1} for s in steps],
                         "sec": R.estimate_seconds(cfg, steps), "price": R.price_for(cfg, r, st)}
        out.append({"id": r["id"], "name": r["name"], "desc": r.get("description", ""),
                    "glass": cfg["glasses"][r["glass"]]["name"], "price": r.get("price", 0),
                    "tags": R.display_ingredients(cfg, r), "groups": R.menu_groups(cfg, r),
                    "plans": plans, "finish": r.get("finish", ""), "art": R.art_spec(cfg, r),
                    "photo": R.photo_info(r["id"])})
    return out


def page(title, body, css, js, full=True):
    head = f"<title>{title}</title>\n"
    if full:
        return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
                "<meta name=\"theme-color\" content=\"#14110f\">\n" + head + FONTS +
                f"\n<style>\n{css}</style>\n<script>\n{js}</script>\n</head>\n<body>\n{body}\n</body>\n</html>\n")
    # body-only variant (for hosts that add their own <html>/<head>, e.g. a claude.ai artifact)
    return (head + '<meta name="claude:viewport-fit-sides" content="cover">\n' + FONTS +
            f"\n<style>\n{css}</style>\n<script>\n{js}</script>\n{body}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "site", "dist"))
    ap.add_argument("--fragment", help="also write a single body-only demo page here")
    ap.add_argument("--drinks-url", default="drinks.html", help="link from the demo to the drink list")
    ap.add_argument("--photo-base", default="", help="URL prefix for photos in the --fragment page")
    a = ap.parse_args()

    cfg = R.load_config(os.path.join(ROOT, "config.yaml"))
    data = json.dumps(drink_data(cfg), separators=(",", ":")).replace("</", "<\\/")
    count = str(len(R.available_recipes(cfg)))
    read = lambda p: open(os.path.join(ROOT, p)).read()  # noqa: E731
    css, js = read("site/site.css"), read("drinkbot/static/drinkart.js")
    demo = read("site/demo.body.html").replace("__DRINKS__", data).replace("__COUNT__", count)
    drinks = read("site/drinks.body.html").replace("__DRINKS__", data).replace("__DEMO_URL__", "index.html")

    os.makedirs(a.out, exist_ok=True)
    if os.path.isdir(R.PHOTO_DIR):
        shutil.copytree(R.PHOTO_DIR, os.path.join(a.out, "photos"), dirs_exist_ok=True)
    with open(os.path.join(a.out, "index.html"), "w") as f:
        f.write(page("DrinkBot Demo", demo.replace("__DRINKS_URL__", "drinks.html").replace("__PHOTO_BASE__", ""), css, js))
    with open(os.path.join(a.out, "drinks.html"), "w") as f:
        f.write(page("Garage Bar Drinks", drinks, css, js))
    print("wrote", a.out, f"({count} drinks)")
    if a.fragment:
        with open(a.fragment, "w") as f:
            frag = demo.replace("__DRINKS_URL__", a.drinks_url).replace("__PHOTO_BASE__", a.photo_base)
            f.write(page("DrinkBot Demo", frag, css, js, full=False))
        print("wrote", a.fragment)


if __name__ == "__main__":
    main()
