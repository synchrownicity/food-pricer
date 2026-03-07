import re
import requests
from bs4 import BeautifulSoup
import re
from rapidfuzz import fuzz


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
}

# Stable entry pages that visibly contain products today.
CANDIDATE_URLS = [
    "https://coldstorage.com.sg/",
    "https://coldstorage.com.sg/category/100015-100184-101103/1.html?order=6&perpage=36&view=grid",
    "https://coldstorage.com.sg/category/100015-100186-101111/1.html?order=6&perpage=36&view=grid",
]


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_price(text: str):
    # Handles "$8 .90" and "$8.90"
    cleaned = text.replace(" .", ".").replace(". ", ".")
    matches = re.findall(r"\$ ?(\d+(?:\.\d{1,2})?)", cleaned.replace(",", ""))
    if not matches:
        return None
    return min(float(x) for x in matches)


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

def _keyword_match(text: str, keywords: str, threshold: int = 90) -> bool:
    """
    Returns True if ANY keyword token matches the product text closely enough.

    Behaviour:
    - OR matching: only one query word needs to match
    - Fuzzy matching: allows small spelling differences / word variations
    - Case-insensitive

    Example:
    keywords = "baby diapers"
    -> matches if either "baby" or "diapers" fuzzily matches the text
    """
    text_l = text.lower().strip()
    keyword_tokens = [w for w in re.split(r"\s+", keywords.lower().strip()) if w]

    if not text_l or not keyword_tokens:
        return False

    for token in keyword_tokens:
        # Check token against full product title
        if fuzz.partial_ratio(token, text_l) >= threshold:
            return True

    return False

def _parse_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    products = []

    for a in soup.find_all("a", href=True):
        text = _normalize_spaces(" ".join(a.stripped_strings))
        href = a["href"].strip()

        if not text:
            continue

        price = _extract_price(text)
        measurement = _extract_measurement(text)

        # We only care about anchors that look like products.
        if price is None:
            continue

        if not any(unit in text.lower() for unit in ["kg", "g", "ml", "l", "delivery only", "find similar", "add to cart"]):
            continue

        title = text
        title = re.sub(r"Buy \d+ for \$\d+(?:\.\d+)?", "", title, flags=re.IGNORECASE)
        title = re.sub(r"Sold Out", "", title, flags=re.IGNORECASE)
        title = re.sub(r"Delivery only", "", title, flags=re.IGNORECASE)
        title = re.sub(r"Find Similar", "", title, flags=re.IGNORECASE)
        title = re.sub(r"Add to Cart", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\$ ?\d+(?:\s?\.\s?\d{1,2})?", "", title)
        title = _normalize_spaces(title)

        if not title:
            continue

        if href.startswith("/"):
            href = "https://coldstorage.com.sg" + href
        elif not href.startswith("http"):
            href = "https://coldstorage.com.sg/" + href.lstrip("/")

        products.append(
            {
                "title": title,
                "price": price,
                "measurement": measurement,
                "link": href,
                "supermarket": "cold-storage",
            }
        )

    return products


def search(keywords):
    results = []
    seen = set()

    for url in CANDIDATE_URLS:
        try:
            page_results = _parse_page(url)
        except Exception as e:
            print(f"[WARN] Cold Storage page failed: {url} -> {e}")
            continue

        for item in page_results:
            if not _keyword_match(item["title"], keywords):
                continue

            key = (item["title"].lower(), item["link"])
            if key in seen:
                continue
            seen.add(key)
            results.append(item)

    return results