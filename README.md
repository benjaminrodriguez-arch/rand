# rand

A macOS terminal command that outputs a real, navigable random address and copies it to your clipboard. Works fully offline after install — no API key, no account.

```
┌─ Random Address ──────────────────────┐
│  1847 Elm Street                      │
│  Austin, TX 78701                     │
│  United States                        │
└───────────────────────────────────────┘
(copied to clipboard)
```

## Requirements

- macOS
- Python 3 (pre-installed on macOS)

## Install

```sh
git clone https://github.com/your-username/rand.git
cd rand
./install.sh
```

That's it. US addresses work immediately. All other countries have bundled reserve data ready to activate instantly — no internet needed.

## Usage

```sh
rand                    # Random US address
rand -de                # Germany
rand -fr                # France
rand -XX                # Any supported country code
rand -list              # Show all 29 supported countries and their status
rand -download de 100   # Activate 100 German addresses (instant, from reserve)
rand -h                 # Show help
```

## Adding countries

Every supported country ships with ~500 bundled addresses. Activating them requires no internet:

```sh
rand -download au 100   # Activate 100 Australian addresses instantly
rand -au                # Use it
```

If you request more than the bundled reserve has, `rand` fetches the remainder from OpenStreetMap automatically:

```sh
rand -download de 1000  # Uses all 500 from reserve, fetches 500 more online
```

## Supported countries (29)

Austria, Australia, Belgium, Brazil, Canada, Switzerland, Czech Republic, Germany, Denmark, Spain, Finland, France, United Kingdom, Greece, Hungary, Ireland, Italy, Japan, Mexico, Netherlands, Norway, New Zealand, Poland, Portugal, Romania, Sweden, Ukraine, United States, South Africa

Run `rand -list` to see which are active, which have reserve data ready, and how many addresses remain.

## How it works

- **US**: ~200 real addresses bundled and shuffled at install. Ready immediately.
- **Other countries**: ~500 addresses per country bundled as compressed reserves (`data/XX.txt.gz`, total ~137 KB). Run `rand -download XX N` to activate N addresses instantly from reserve.
- **Cycling**: addresses are served sequentially from a local file. When fewer than 50 remain, new addresses are fetched from OpenStreetMap in the background.
- **Pointer file**: each country has a pointer file (`~/.rand-self/XX_ptr`) tracking the current position. Atomic writes prevent race conditions under concurrent use.
- **Data source**: all addresses are real locations from [OpenStreetMap](https://www.openstreetmap.org/) via the [Overpass API](https://overpass-api.de/).

## State directory

All runtime data lives in `~/.rand-self/` and is not tracked by git:

```
~/.rand-self/
  us_data.txt       active US pool
  us_ptr            current position
  de_reserve.txt    bundled reserve for Germany (pre-install)
  de_data.txt       active German pool (created on first -download)
  de_ptr
  ...
```

## Uninstall

```sh
rm /usr/local/bin/rand
rm -rf ~/.rand-self
```

## Developer scripts

Regenerate all country bundles (requires internet, ~5 min):

```sh
python3 scripts/generate-bundle-data.py   # rebuilds data/*.txt.gz
python3 scripts/generate-us-data.py       # rebuilds data/us.txt
```
