import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, parse_qs, urlparse
import re

BASE_URL = "https://coldstorage.com.sg"


def _extract_measurement(text: str) -> str:
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


def _extract_image_url(img_tag):
    if not img_tag:
        return None

    src = img_tag.get("src", "")

    # extract the real image from ?url=...
    parsed = urlparse(src)
    query = parse_qs(parsed.query)

    if "url" in query:
        return unquote(query["url"][0])

    return None


def search(keyword: str):
    url = f"{BASE_URL}/search?q={keyword}"

    resp = requests.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    results = []

    # find all product cards
    products = soup.find_all("div", class_=lambda x: x and "product-item" in x)

    for product in products:
        # link + title
        a_tag = product.find("a", href=True)
        if not a_tag:
            continue

        link = urljoin(BASE_URL, a_tag["href"])

        # title
        title_tag = product.find("p")
        title = title_tag.get_text(strip=True) if title_tag else None

        # price
        price_tag = product.find("div", string=lambda x: x and "$" in x)
        price = None
        if price_tag:
            try:
                price = float(price_tag.text.replace("$", "").strip())
            except:
                pass

        # image
        img_tag = product.find("img")
        image = _extract_image_url(img_tag)

        if not title:
            continue

        results.append({
            "title": title,
            "price": price,
            "measurement": _extract_measurement(title),
            "link": link,
            "image": image,
            "supermarket": "cold-storage",
        })

    return {"results": results}