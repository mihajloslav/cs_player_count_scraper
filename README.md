# CS 1.6 Player Count Scraper

This project collects Counter-Strike 1.6 server data from
[GameTracker](https://www.gametracker.com/search/cs/) and calculates the total
number of active players across all servers found in the results.

For every server, the scraper stores:

- rank
- game mode
- server name
- active players and available slots
- country/location
- IP address and port
- current map

The results are saved to `gametracker_servers.csv`, and a summary is printed
to the terminal, including the total number of servers, total slots, and total
active players.

## Requirements

- Python 3.9 or newer
- Internet access
- Chromium, installed through Playwright

## Setup

Create and activate a virtual environment:

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python dependency:

```bash
python -m pip install --upgrade pip
python -m pip install playwright
```

Install the Chromium browser used by Playwright:

```bash
python -m playwright install chromium
```

## Running the scraper

With the virtual environment activated, run:

```bash
python scraper.py
```

The script opens GameTracker in headless Chromium mode, finds all available
result pages, processes them concurrently, and writes the CSV output to:

```text
gametracker_servers.csv
```

The total active player count is printed near the end of the run:

```text
UKUPNO AKTIVNIH IGRAČA: <number>
```

Deactivate the virtual environment when finished:

```bash
deactivate
```

## Configuration

The following values can be adjusted at the top of `scraper.py`:

- `ITEMS_PER_PAGE` - number of servers requested per GameTracker page
- `CONCURRENCY` - maximum number of pages scraped at the same time
- `CSV_FILE` - path or filename for the generated CSV file

## Notes

The total is calculated from the `Active` player count reported by
GameTracker for each scraped server. The result therefore represents a
snapshot taken when the scraper runs. Please use the scraper responsibly and
respect GameTracker's terms of service and any applicable rate limits.
