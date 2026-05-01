#!/usr/bin/env python3
"""
Generate data/us.txt from OpenStreetMap via the Overpass API.
Real, government-sourced addresses. Free, no auth required.

Usage:
    python3 scripts/generate-us-data.py
    python3 scripts/generate-us-data.py --count 50000
    python3 scripts/generate-us-data.py --count 10000 --per-state 300
"""

import urllib.request
import urllib.parse
import json
import time
import random
import argparse
import os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

US_STATES = [
    ("AL", "US-AL"), ("AK", "US-AK"), ("AZ", "US-AZ"), ("AR", "US-AR"),
    ("CA", "US-CA"), ("CO", "US-CO"), ("CT", "US-CT"), ("DE", "US-DE"),
    ("FL", "US-FL"), ("GA", "US-GA"), ("HI", "US-HI"), ("ID", "US-ID"),
    ("IL", "US-IL"), ("IN", "US-IN"), ("IA", "US-IA"), ("KS", "US-KS"),
    ("KY", "US-KY"), ("LA", "US-LA"), ("ME", "US-ME"), ("MD", "US-MD"),
    ("MA", "US-MA"), ("MI", "US-MI"), ("MN", "US-MN"), ("MS", "US-MS"),
    ("MO", "US-MO"), ("MT", "US-MT"), ("NE", "US-NE"), ("NV", "US-NV"),
    ("NH", "US-NH"), ("NJ", "US-NJ"), ("NM", "US-NM"), ("NY", "US-NY"),
    ("NC", "US-NC"), ("ND", "US-ND"), ("OH", "US-OH"), ("OK", "US-OK"),
    ("OR", "US-OR"), ("PA", "US-PA"), ("RI", "US-RI"), ("SC", "US-SC"),
    ("SD", "US-SD"), ("TN", "US-TN"), ("TX", "US-TX"), ("UT", "US-UT"),
    ("VT", "US-VT"), ("VA", "US-VA"), ("WA", "US-WA"), ("WV", "US-WV"),
    ("WI", "US-WI"), ("WY", "US-WY"),
]

def fetch_state(abbr, iso, limit):
    query = f"""
[out:json][timeout:60];
area["ISO3166-2"="{iso}"]->.state;
node["addr:housenumber"]["addr:street"]["addr:city"]["addr:postcode"](area.state);
out {limit};
"""
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
                                  headers={"User-Agent": "rand-address-generator/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r).get("elements", [])

def parse_address(el, state_abbr):
    t = el.get("tags", {})
    num    = t.get("addr:housenumber", "").strip()
    street = t.get("addr:street", "").strip()
    unit   = t.get("addr:unit", "").strip()
    city   = t.get("addr:city", "").strip()
    state  = t.get("addr:state", state_abbr).strip() or state_abbr
    zip_   = t.get("addr:postcode", "").strip()[:5]  # strip ZIP+4

    if not (num and street and city and zip_):
        return None

    street_line = f"{num} {street}"
    if unit:
        street_line = f"{street_line} {unit}"

    return f"{street_line}, {city}, {state} {zip_}, United States"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50000,
                        help="Total addresses to collect (default: 50000)")
    parser.add_argument("--per-state", type=int, default=0,
                        help="Max per state (default: auto-calculated)")
    args = parser.parse_args()

    target = args.count
    per_state = args.per_state or max(200, (target // len(US_STATES)) + 100)

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "us.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    all_addresses = set()
    states = list(US_STATES)
    random.shuffle(states)  # vary starting point each run

    print(f"Collecting {target:,} US addresses from OpenStreetMap...")
    print(f"Querying {len(states)} states, up to {per_state} each\n")

    for i, (abbr, iso) in enumerate(states):
        if len(all_addresses) >= target:
            break

        try:
            elements = fetch_state(abbr, iso, per_state)
            before = len(all_addresses)
            for el in elements:
                addr = parse_address(el, abbr)
                if addr:
                    all_addresses.add(addr)
            gained = len(all_addresses) - before
            print(f"  [{i+1:2}/{len(states)}] {abbr}: +{gained:4} → {len(all_addresses):,} total")
        except Exception as e:
            print(f"  [{i+1:2}/{len(states)}] {abbr}: failed ({e})")

        # Respectful rate limiting — Overpass asks for a pause between requests
        time.sleep(2)

    result = list(all_addresses)[:target]
    random.shuffle(result)

    with open(out_path, "w") as f:
        f.write("\n".join(result) + "\n")

    print(f"\nWrote {len(result):,} addresses to data/us.txt")

if __name__ == "__main__":
    main()
