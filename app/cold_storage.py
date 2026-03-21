import requests
import re
from urllib.parse import quote

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-SG,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://coldstorage.com.sg",
    "Referer": "https://coldstorage.com.sg/",
}

SEARCH_URL = "https://coldstorage.com.sg/api/item/searchTemplateData"


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


def _build_payload(keyword: str, page_num: int = 1, page_size: int = 20) -> dict:
    return {
        "comm": {
            "dmTenantId": 10,
            "venderId": 12,
            "businessCode": 1,
            "origin": 26,
            "pickUpStoreId": "",
            "shipmentType": 1,
            "storeId": 550989,
            "superweb-locale": "en_US",
        },
        "param": {
            "businessCode": 1,
            "categoryType": 1,
            "erpStoreId": 550989,
            "filterProperties": [],
            "keyword": keyword,
            "pageNum": str(page_num),
            "pageSize": page_size,
            "sortKey": 0,
            "sortRule": 0,
            "venderId": 12,
        },
    }


def _normalise_price(value):
    if value in (None, "", "null"):
        return None

    try:
        price = float(value)
    except (TypeError, ValueError):
        return None

    # Convert cents → dollars AND format to 2dp
    return round(price / 100, 2)


def _pick_price(item: dict):
    for key in ["onlinePromotionPrice", "onlinePrice", "warePrice", "offlinePrice"]:
        price = _normalise_price(item.get(key))
        if price is not None:
            return price
    return None


def _build_search_link(keyword: str) -> str:
    return f"https://coldstorage.com.sg/search?keyword={quote(keyword)}"


def search(keywords: str, max_pages: int = 1):
    results = []
    seen = set()

    for page in range(1, max_pages + 1):
        payload = _build_payload(keywords, page_num=page, page_size=20)

        resp = requests.post(SEARCH_URL, json=payload, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", {}).get("productList", [])
        if not items:
            break

        for item in items:
            title = (item.get("wareName") or "").strip()
            price = _pick_price(item)

            if not title:
                continue

            key = (str(item.get("wareId")), str(item.get("sku")))
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "title": title,
                "price": price,
                "measurement": _extract_measurement(title),
                "link": _build_search_link(title),
                "image": item.get("wareImg"),   # 👈 ADD THIS
                "supermarket": "cold-storage",
            })

    return results