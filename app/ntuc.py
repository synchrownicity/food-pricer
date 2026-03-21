import re
import json
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


def _extract_measurement(text: str):
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
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []

    data = json.loads(script.string)

    layouts = data["props"]["pageProps"]["data"]["data"]["page"]["layouts"]

    product_collection = None
    for layout in layouts:
        if layout.get("name") == "ProductCollection":
            product_collection = layout.get("value", {}).get("collection", {})
            break

    if not product_collection:
        return []

    products = product_collection.get("product", [])
    results = []
    seen = set()

    for item in products:
        title = (item.get("name") or "").strip()
        price = item.get("final_price")
        slug = item.get("slug") or ""
        images = item.get("images") or []
        metadata = item.get("metaData") or {}

        if not title:
            continue

        image = images[0] if images else ""
        measurement = metadata.get("DisplayUnit") or _extract_measurement(title)
        link = f"{BASE_URL}/product/{slug}" if slug else ""

        key = (title.lower(), link)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "price": round(float(price), 2) if price is not None else None,
                "measurement": measurement,
                "link": link,
                "image": image,
                "supermarket": "ntuc",
            }
        )

    return results