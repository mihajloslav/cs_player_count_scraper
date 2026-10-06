import asyncio
import csv
from playwright.async_api import async_playwright

BASE_URL = "https://www.gametracker.com/search/cs/"
ITEMS_PER_PAGE = 50
CONCURRENCY = 5
CSV_FILE = "gametracker_servers.csv"


async def scrape_page(browser, page_num, total_pages):
    url = f"{BASE_URL}?searchipp={ITEMS_PER_PAGE}&searchpge={page_num}#search"
    page = await browser.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        await page.wait_for_selector(
            'tr:has(a[href^="/server_info/"])',
            timeout=15_000
        )

        servers = await page.locator(
            'tr:has(a[href^="/server_info/"])'
        ).evaluate_all("""
        rows => {
            const result = [];

            for (const row of rows) {
                const cells = [...row.querySelectorAll("td")];

                // Mora biti server red sa Active/Slots, npr. 31/32
                const ratioCell = cells.find(cell =>
                    /^\\d+\\s*\\/\\s*\\d+$/.test(cell.innerText.trim())
                );

                if (!ratioCell) continue;

                const ratio = ratioCell.innerText.trim().match(
                    /^(\\d+)\\s*\\/\\s*(\\d+)$/
                );

                if (!ratio) continue;

                // ---------------------------------------------------------
                // Rank
                // ---------------------------------------------------------
                const rankText = cells[0]?.innerText.trim() || "";
                const rankMatch = rankText.match(/\\d+/);
                const rank = rankMatch ? Number(rankMatch[0]) : "";

                // ---------------------------------------------------------
                // Game Mode
                // <img ... alt="CS">
                // ---------------------------------------------------------
                const gameImg = row.querySelector(
                    'td:nth-child(2) img[alt]'
                );
                const gm = gameImg
                    ? gameImg.getAttribute("alt").trim()
                    : "";

                // ---------------------------------------------------------
                // Server Name
                // <a href="/server_info/IP:PORT/">NAME</a>
                // ---------------------------------------------------------
                const serverLink = row.querySelector(
                    'a[href^="/server_info/"]'
                );

                if (!serverLink) continue;

                const serverName = serverLink.innerText.trim();

                // ---------------------------------------------------------
                // IP:Port
                // <span class="ip">IP</span>
                // <span class="port">:PORT</span>
                // ---------------------------------------------------------
                const ip = row.querySelector("span.ip");
                const port = row.querySelector("span.port");

                const ipAddress = ip
                    ? ip.innerText.trim()
                    : "";

                const portNumber = port
                    ? port.innerText.trim()
                    : "";

                const ipPort = ipAddress + portNumber;

                // Fallback: ako spanovi nisu pronađeni, uzmi iz server_info
                const href = serverLink.getAttribute("href") || "";
                const hrefMatch = href.match(
                    /\\/server_info\\/([^/]+)\\//
                );

                const finalIpPort = ipPort ||
                    (hrefMatch ? hrefMatch[1] : "");

                // ---------------------------------------------------------
                // Location
                // <a href="/search/cs/PK/">
                //     <img src="/images/flags/pk.gif">
                // </a>
                //
                // Iz "pk.gif" uzimamo "PK"
                // ---------------------------------------------------------
                let location = "";

                const flagLink = row.querySelector(
                    'a[href*="/search/cs/"] img[src*="/images/flags/"]'
                );

                if (flagLink) {
                    const src = flagLink.getAttribute("src") || "";
                    const flagMatch = src.match(
                        /\\/flags\\/([a-zA-Z]{2})\\.gif/i
                    );

                    if (flagMatch) {
                        location = flagMatch[1].toUpperCase();
                    }
                }

                // Fallback: uzmi oznaku države iz href-a
                if (!location) {
                    const locationLink = row.querySelector(
                        'a[href^="/search/cs/"]'
                    );

                    if (locationLink) {
                        const locationHref =
                            locationLink.getAttribute("href") || "";

                        const locationMatch = locationHref.match(
                            /\\/search\\/cs\\/([a-zA-Z]{2})\\//
                        );

                        if (locationMatch) {
                            location =
                                locationMatch[1].toUpperCase();
                        }
                    }
                }

                // ---------------------------------------------------------
                // Server Map
                //
                // Po HTML-u koji si poslao, mapa je poslednji <td>:
                // <td>de_dust2</td>
                //
                // Uzimamo poslednju TD ćeliju.
                // ---------------------------------------------------------
                let serverMap = "";

                if (cells.length > 0) {
                    serverMap = cells[cells.length - 1]
                        .innerText
                        .trim();
                }

                // Ako poslednja ćelija iz nekog razloga nije mapa,
                // pokušaj da nađeš poznat format mape.
                if (!serverMap || serverMap === portNumber) {
                    serverMap = "";

                    for (const cell of cells) {
                        const text = cell.innerText.trim();

                        if (
                            text &&
                            text !== serverName &&
                            text !== ratioCell.innerText.trim() &&
                            text !== ipAddress &&
                            text !== portNumber &&
                            /^[a-zA-Z0-9_][a-zA-Z0-9_-]*$/.test(text)
                        ) {
                            // Izbegni rank i slične kratke vrednosti
                            if (!/^\\d+$/.test(text)) {
                                serverMap = text;
                            }
                        }
                    }
                }

                result.push({
                    rank,
                    gm,
                    server_name: serverName,
                    active: Number(ratio[1]),
                    slots: Number(ratio[2]),
                    location,
                    ip_port: finalIpPort,
                    server_map: serverMap
                });
            }

            return result;
        }
        """)

        active = sum(server["active"] for server in servers)

        print(
            f"[{page_num:>3}/{total_pages}] "
            f"servera: {len(servers):>2} | "
            f"igrača: {active:>4}"
        )

        return servers

    except Exception as e:
        print(f"[{page_num:>3}/{total_pages}] GREŠKA: {e}")
        return []

    finally:
        await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Prva stranica - pronađi ukupan broj stranica.
        page = await browser.new_page()

        first_url = f"{BASE_URL}?searchipp={ITEMS_PER_PAGE}#search"

        print("Otvaram GameTracker...")

        await page.goto(
            first_url,
            wait_until="domcontentloaded",
            timeout=30_000
        )

        await page.wait_for_selector(
            "div.paging",
            timeout=15_000
        )

        page_numbers = await page.locator(
            'div.paging a[href*="searchpge="]'
        ).evaluate_all("""
        links => links.map(link => {
            const match = link.href.match(/searchpge=(\\d+)/);
            return match ? Number(match[1]) : null;
        }).filter(Boolean)
        """)

        total_pages = max(page_numbers) if page_numbers else 1

        print(f"Ukupno stranica: {total_pages}")
        print(f"Servera po stranici: {ITEMS_PER_PAGE}")
        print("-" * 75)

        await page.close()

        # Ograniči broj paralelnih stranica da ne šaljemo previše
        # zahteva GameTracker-u odjednom.
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def worker(page_num):
            async with semaphore:
                return await scrape_page(
                    browser,
                    page_num,
                    total_pages
                )

        page_results = await asyncio.gather(
            *(worker(i) for i in range(1, total_pages + 1))
        )

        # Spoji rezultate svih stranica.
        servers = [
            server
            for page_servers in page_results
            for server in page_servers
        ]

        # Rank je globalni redosled kroz sve stranice.
        # Ako GameTracker rankovi počinju ponovo od 1 na svakoj strani,
        # ovde ih pretvaramo u globalni rank 1, 2, 3...
        for index, server in enumerate(servers, start=1):
            server["rank"] = index

        # -------------------------------------------------------------
        # CSV
        # -------------------------------------------------------------
        with open(
            CSV_FILE,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as f:
            writer = csv.writer(f)

            writer.writerow([
                "Rank",
                "Gm",
                "Server Name",
                "Active",
                "Slots",
                "Location",
                "IP:Port",
                "Server Map"
            ])

            for server in servers:
                writer.writerow([
                    server["rank"],
                    server["gm"],
                    server["server_name"],
                    server["active"],
                    server["slots"],
                    server["location"],
                    server["ip_port"],
                    server["server_map"]
                ])

        total_players = sum(
            server["active"] for server in servers
        )

        total_slots = sum(
            server["slots"] for server in servers
        )

        print("-" * 75)
        print("GOTOVO!")
        print(f"Ukupno servera:             {len(servers)}")
        print(f"Ukupno slotova:             {total_slots}")
        print(f"UKUPNO AKTIVNIH IGRAČA:     {total_players}")
        print(f"CSV fajl:                   {CSV_FILE}")
        print("-" * 75)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
