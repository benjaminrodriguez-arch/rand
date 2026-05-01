#!/usr/bin/env python3
"""
Developer tool: pre-fetch 500 real addresses per supported country and save as
data/XX.txt.gz. Run once from the project root before committing to GitHub.

Usage:
    python3 scripts/generate-bundle-data.py
    python3 scripts/generate-bundle-data.py --force
    python3 scripts/generate-bundle-data.py --countries de fr gb au
    python3 scripts/generate-bundle-data.py --count 1000
"""

import sys, os, gzip, json, random, time, argparse, threading
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Configuration (mirrors rand's embedded Python) ────────────────────────────

ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.openstreetmap.fr/api/interpreter',
]

BOXES = {
    'AU': [-39.0, -10.7, 113.3, 153.6],
    'AT': [ 46.4,  49.0,   9.5,  17.2],
    'BE': [ 49.5,  51.5,   2.5,   6.4],
    'BR': [-33.8,   5.3, -73.9, -28.8],
    'CA': [ 42.0,  60.0,-141.0, -52.6],
    'CH': [ 45.8,  47.8,   5.9,  10.5],
    'CZ': [ 48.6,  51.1,  12.1,  18.9],
    'DE': [ 47.3,  55.1,   5.9,  15.0],
    'DK': [ 54.6,  57.8,   8.1,  15.2],
    'ES': [ 36.0,  43.8,  -9.3,   4.3],
    'FI': [ 60.0,  70.1,  20.0,  31.6],
    'FR': [ 41.3,  51.1,  -5.1,   9.6],
    'GB': [ 49.9,  58.7,  -6.4,   1.8],
    'GR': [ 34.8,  41.8,  19.4,  29.6],
    'HU': [ 45.7,  48.6,  16.1,  22.9],
    'IE': [ 51.4,  55.4, -10.5,  -6.0],
    'IT': [ 36.6,  47.1,   6.6,  18.5],
    'JP': [ 31.0,  45.5, 130.0, 145.5],
    'MX': [ 14.5,  32.7,-117.1, -86.7],
    'NL': [ 50.7,  53.6,   3.3,   7.2],
    'NO': [ 57.9,  71.2,   4.5,  31.1],
    'NZ': [-46.6, -34.4, 166.4, 178.6],
    'PL': [ 49.0,  54.9,  14.1,  24.2],
    'PT': [ 36.8,  42.2,  -9.5,  -6.2],
    'RO': [ 43.6,  48.3,  20.3,  30.0],
    'SE': [ 55.3,  69.1,  11.1,  24.2],
    'UA': [ 44.4,  52.4,  22.1,  40.2],
    'ZA': [-34.8, -22.1,  16.5,  32.9],
    # US excluded — bundled separately as data/us.txt
}

HOTSPOTS = {
    'AU': [
        [-34.1, -33.7, 150.6, 151.4],
        [-38.1, -37.6, 144.7, 145.2],
        [-27.7, -27.2, 152.7, 153.2],
        [-32.1, -31.7, 115.7, 116.1],
        [-35.1, -34.7, 138.4, 138.8],
    ],
    'CA': [
        [ 43.5,  43.9,  -79.7, -79.1],
        [ 45.4,  45.7,  -73.9, -73.4],
        [ 49.1,  49.4, -123.3,-122.9],
        [ 51.0,  51.2, -114.3,-113.9],
        [ 45.3,  45.6,  -75.9, -75.5],
    ],
    'BR': [
        [-23.7, -23.3,  -46.8, -46.5],
        [-22.9, -22.7,  -43.4, -43.1],
        [-15.9, -15.6,  -48.1, -47.8],
        [ -3.8,  -3.5,  -38.7, -38.4],
    ],
}

NUMBER_LAST = {
    'AT','BE','BR','CZ','DE','DK','ES','FI','FR','GR',
    'HU','IE','IT','MX','NL','NO','PL','PT','RO','SE','UA','ZA',
}

COUNTRY_NAMES = {
    'AU':'Australia','AT':'Austria','BE':'Belgium','BR':'Brazil',
    'CA':'Canada','CH':'Switzerland','CZ':'Czech Republic','DE':'Germany',
    'DK':'Denmark','ES':'Spain','FI':'Finland','FR':'France',
    'GB':'United Kingdom','GR':'Greece','HU':'Hungary','IE':'Ireland',
    'IT':'Italy','JP':'Japan','MX':'Mexico','NL':'Netherlands',
    'NO':'Norway','NZ':'New Zealand','PL':'Poland','PT':'Portugal',
    'RO':'Romania','SE':'Sweden','UA':'Ukraine','ZA':'South Africa',
}

_ep_idx = 0
_ep_lock = threading.Lock()

def _next_endpoint():
    global _ep_idx
    with _ep_lock:
        ep = ENDPOINTS[_ep_idx % len(ENDPOINTS)]
        _ep_idx += 1
        return ep

def _pick_subbox(cc):
    if cc in HOTSPOTS:
        s0, n0, w0, e0 = random.choice(HOTSPOTS[cc])
    else:
        min_lat, max_lat, min_lon, max_lon = BOXES[cc]
        slat = min(1.0, max_lat - min_lat)
        slon = min(1.0, max_lon - min_lon)
        s0 = random.uniform(min_lat, max_lat - slat)
        n0 = s0 + slat
        w0 = random.uniform(min_lon, max_lon - slon)
        e0 = w0 + slon
    return round(s0, 4), round(n0, 4), round(w0, 4), round(e0, 4)

def _fetch_one_batch(cc, want):
    s, n, w, e = _pick_subbox(cc)
    query = (f'[out:json][timeout:20];'
             f'nwr({s},{w},{n},{e})'
             f'["addr:housenumber"]["addr:street"];'
             f'out center {want * 5};')
    endpoint = _next_endpoint()
    data = urllib.parse.urlencode({'data': query}).encode()
    req = urllib.request.Request(endpoint, data=data,
          headers={'User-Agent': 'rand-bundle-generator/1.0'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        result = json.load(resp)
    elements = result.get('elements', [])
    random.shuffle(elements)
    country_name = COUNTRY_NAMES.get(cc, cc)
    addresses = []
    for el in elements:
        tags = el.get('tags', {})
        street = tags.get('addr:street', '').strip()
        num    = tags.get('addr:housenumber', '').strip()
        if not all([street, num]):
            continue
        city = (tags.get('addr:city') or tags.get('addr:suburb')
                or tags.get('addr:town') or tags.get('addr:village') or '').strip()
        postcode = tags.get('addr:postcode', '').strip()
        if not city:
            continue
        street_line = f"{street} {num}" if cc in NUMBER_LAST else f"{num} {street}"
        location = f"{city}, {postcode}" if postcode else city
        addresses.append(f"{street_line}, {location}, {country_name}")
        if len(addresses) >= want:
            break
    return addresses

def fetch_country(cc, count):
    workers = min(5, max(1, (count + 49) // 50))
    per_worker = max(20, (count + workers - 1) // workers)

    collected = []
    seen = set()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetch_one_batch, cc, per_worker) for _ in range(workers)]
        for future in as_completed(futures):
            try:
                for addr in future.result():
                    if addr not in seen:
                        seen.add(addr)
                        collected.append(addr)
            except Exception as e:
                print(f'    warning: {e}', file=sys.stderr)

    retries = 0
    while len(collected) < count and retries < 4:
        retries += 1
        try:
            for addr in _fetch_one_batch(cc, count - len(collected)):
                if addr not in seen:
                    seen.add(addr)
                    collected.append(addr)
        except Exception as e:
            print(f'    retry {retries} failed: {e}', file=sys.stderr)
            time.sleep(2)

    return collected[:count]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pre-fetch bundled address data for rand (developer tool)'
    )
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing .txt.gz files')
    parser.add_argument('--count', type=int, default=500,
                        help='Addresses per country (default: 500)')
    parser.add_argument('--countries', nargs='+',
                        help='Specific country codes (default: all 28)')
    args = parser.parse_args()

    out_dir = Path(__file__).parent.parent / 'data'
    out_dir.mkdir(exist_ok=True)

    targets = [c.upper() for c in args.countries] if args.countries \
              else sorted(BOXES.keys())

    print(f'Generating bundles: {len(targets)} countries × {args.count} addresses\n')

    ok = fail = skip = 0
    for cc in targets:
        if cc not in BOXES:
            print(f'  {cc}: unknown country code, skipping')
            continue

        out_file = out_dir / f'{cc.lower()}.txt.gz'
        if out_file.exists() and not args.force:
            size = out_file.stat().st_size
            print(f'  {cc}: skip (exists, {size}B) — use --force to regenerate')
            skip += 1
            continue

        print(f'  {cc}: fetching {args.count} addresses...', end='', flush=True)
        try:
            addrs = fetch_country(cc, args.count)
            random.shuffle(addrs)
            with gzip.open(out_file, 'wt', encoding='utf-8') as f:
                f.write('\n'.join(addrs) + '\n')
            size = out_file.stat().st_size
            print(f' ✓ {len(addrs)} addresses ({size:,}B compressed)')
            ok += 1
        except Exception as e:
            print(f' ✗ failed: {e}')
            fail += 1

        time.sleep(1)

    print(f'\nDone: {ok} generated, {skip} skipped, {fail} failed.')
    if ok > 0:
        total = sum(
            (out_dir / f'{cc.lower()}.txt.gz').stat().st_size
            for cc in targets
            if (out_dir / f'{cc.lower()}.txt.gz').exists()
        )
        print(f'Total compressed size of data/: {total:,}B ({total//1024}KB)')

if __name__ == '__main__':
    main()
