import re
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.fairprice.com.sg"
SEARCH_URL = "https://www.fairprice.com.sg/search?query="
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
}


def _extract_price(text: str):
    """
    Return the lowest $ price found in text, e.g. "$10.45 $12.65" -> 10.45
    """
    prices = re.findall(r"\$ ?(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    if not prices:
        return None
    return min(float(p) for p in prices)


def _extract_measurement(text: str):
    """
    Tries to detect a pack size / weight from text.
    """
    patterns = [
        r"\b\d+(?:\.\d+)?\s?(?:kg|g|mg|ml|l|L)\b",
        r"\b\d+\s?[xX]\s?\d+(?:\.\d+)?\s?(?:g|kg|ml|l|L)\b",
        r"\b\d+\s?(?:pcs|pc|s)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).replace(" ", "")
    return ""


def search(keywords):
    query = quote(keywords)
    url = f"{SEARCH_URL}{query}"

    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    seen = set()

    # Current FairPrice pages expose product links in anchors.
    for a in soup.select('a[href*="/product/"]'):
        href = a.get("href", "").strip()
        text = " ".join(a.stripped_strings)

        if not href or not text:
            continue

        price = _extract_price(text)
        if price is None:
            continue

        title = re.sub(r"\$ ?\d+(?:\.\d{1,2})?", "", text)
        title = re.sub(r"\s+", " ", title).strip(" -|")

        measurement = _extract_measurement(text)

        full_link = href if href.startswith("http") else BASE_URL + href
        key = (title.lower(), full_link)

        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "price": price,
                "measurement": measurement,
                "link": full_link,
                "supermarket": "ntuc",
            }
        )

    return results