#!/usr/bin/env python3
"""Make printable QR codes: one to join Wi-Fi, one to open the menu.

  python3 scripts/make_qr.py                       # menu QR from config.yaml
  python3 scripts/make_qr.py --wifi "GarageBar" "password123"
"""
import argparse
import os
import sys

import qrcode
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--wifi", nargs=2, metavar=("SSID", "PASSWORD"), help="also make a Wi-Fi join QR")
ap.add_argument("--out", default=ROOT)
a = ap.parse_args()

cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml")))
qrcode.make(cfg["guest_url"], box_size=12, border=2).save(os.path.join(a.out, "qr-menu.png"))
print("wrote qr-menu.png ->", cfg["guest_url"])

if a.wifi:
    ssid, pw = (s.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace(":", "\\:") for s in a.wifi)
    qrcode.make(f"WIFI:T:WPA;S:{ssid};P:{pw};;", box_size=12, border=2).save(os.path.join(a.out, "qr-wifi.png"))
    print("wrote qr-wifi.png")
sys.exit(0)
