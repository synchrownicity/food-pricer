import json
import random
import re
import string
import time
from typing import Any, Dict, List
from bs4 import BeautifulSoup

import requests
import websocket


BASE_URL = "https://shengsiong.com.sg"
WS_BASE = "wss://shengsiong.com.sg/sockjs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
}


def _random_server_id() -> str:
    # SockJS commonly uses a 3-digit-ish server id in the URL
    return str(random.randint(0, 999)).zfill(3)


def _random_session_id(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _make_product_link(slug: str) -> str:
    # Adjust this if Sheng Siong uses a different product route later
    return f"{BASE_URL}/product/{slug}"


def _build_method_payload(query: str, page: int = 1, page_size: int = 24) -> Dict[str, Any]:
    """
    Build the DDP method call you discovered from DevTools.
    """
    return {
        "msg": "method",
        "id": "1",
        "method": "Products.getByAllSlugs",
        "params": [
            {
                "categoryFilter": {"slugs": []},
                "campaignPageFilter": {"slug": "", "category": {"slug": ""}},
                "shoppingListFilter": {
                    "slug": "",
                    "category": {"slug": ""},
                    "search": {"slug": ""},
                    "showKeptForLater": False,
                },
                "searchFilter": {
                    "slug": query.lower().strip(),
                    "category": {"slug": ""},
                },
            },
            {
                "brands": {"slugs": []},
                "prices": {"slugs": []},
                "countryOfOrigins": {"slugs": []},
                "dietaryHabits": {"slugs": []},
                "tags": {"slugs": []},
                "sortBy": {"slug": ""},
            },
            page,
            page_size,
        ],
    }


def _format_result(item):
    brand = _normalize_spaces(item.get("brand", ""))
    name = _normalize_spaces(item.get("name", ""))
    title = _normalize_spaces(f"{brand} {name}").strip()

    measurement = item.get("packSize", "") or ""
    slug = item.get("slug", "") or ""
    link = _make_product_link(slug) if slug else BASE_URL

    image = _extract_image(item, link)

    return {
        "title": title,
        "price": round(float(item.get("price", 0)), 2),
        "measurement": measurement,
        "link": link,
        "image": image,
        "supermarket": "sheng-siong",
    }


def _extract_cookies() -> str:
    """
    Hit the homepage first so we get the anti-bot / session cookies
    needed for the websocket handshake.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    resp = session.get(BASE_URL, timeout=20)
    resp.raise_for_status()

    return "; ".join(f"{k}={v}" for k, v in session.cookies.get_dict().items())


def _send_sockjs_frame(ws: websocket.WebSocket, payload: Dict[str, Any]) -> None:
    """
    SockJS websocket transport expects messages wrapped in a JSON array string.
    Example:
    ["{\"msg\":\"connect\",\"version\":\"1\",\"support\":[\"1\",\"pre2\",\"pre1\"]}"]
    """
    frame = json.dumps([json.dumps(payload)])
    ws.send(frame)


def search(keywords: str, page: int = 1, page_size: int = 24, timeout: float = 12.0) -> List[Dict[str, Any]]:
    """
    Query Sheng Siong via Meteor DDP over SockJS websocket.

    Returns results in the same schema as your other scrapers.
    """
    query = keywords.strip()
    if not query:
        return []

    cookie_header = _extract_cookies()

    server_id = _random_server_id()
    session_id = _random_session_id()
    ws_url = f"{WS_BASE}/{server_id}/{session_id}/websocket"

    ws = websocket.create_connection(
        ws_url,
        timeout=timeout,
        header=[
            f"Origin: {BASE_URL}",
            f"User-Agent: {HEADERS['User-Agent']}",
            f"Cookie: {cookie_header}",
        ],
    )

    try:
        target_method_id = "1"

        # 1) Wait for SockJS open frame: usually "o"
        start = time.time()
        while time.time() - start < timeout:
            raw = ws.recv()
            if raw == "o":
                break
        else:
            raise TimeoutError("Did not receive SockJS open frame.")

        # 2) Send Meteor DDP connect message
        connect_payload = {
            "msg": "connect",
            "version": "1",
            "support": ["1", "pre2", "pre1"],
        }
        _send_sockjs_frame(ws, connect_payload)

        # 3) Wait for DDP connected acknowledgement
        start = time.time()
        connected = False
        while time.time() - start < timeout:
            raw = ws.recv()

            if raw == "h":
                # SockJS heartbeat
                continue

            if raw.startswith("a"):
                try:
                    messages = json.loads(raw[1:])
                except Exception:
                    continue

                for msg in messages:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    if data.get("msg") == "connected":
                        connected = True
                        break

            if connected:
                break

        if not connected:
            raise TimeoutError("Did not receive DDP connected message.")

        # 4) Send the actual product search method you discovered
        method_payload = _build_method_payload(query, page=page, page_size=page_size)
        _send_sockjs_frame(ws, method_payload)

        # 5) Wait for the matching result id
        start = time.time()
        while time.time() - start < timeout:
            raw = ws.recv()

            if raw == "h":
                continue

            if not raw.startswith("a"):
                continue

            try:
                messages = json.loads(raw[1:])
            except Exception:
                continue

            for msg in messages:
                try:
                    data = json.loads(msg)
                except Exception:
                    continue

                # We only care about the result for our method call
                if data.get("msg") == "result" and data.get("id") == target_method_id:
                    products = data.get("result", []) or []

                    cleaned = []
                    for item in products:
                        # Only keep live ecommerce listings
                        if not item.get("listingOnEcomm", False):
                            continue

                        cleaned.append(_format_result(item))

                    return cleaned

        return []

    finally:
        try:
            ws.close()
        except Exception:
            pass

### Helper function
def _extract_image(item, link):
    # try fast method first
    img_key = item.get("imgKey")
    if img_key:
        return f"{BASE_IMG}{img_key}.0.jpg"

    # fallback to scraping product page
    return _fetch_image_from_page(link)

BASE_IMG = "https://ssecomm.s3-ap-southeast-1.amazonaws.com/products/lg/"

def _fetch_image_from_page(link):
    try:
        resp = requests.get(link, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        img = soup.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            return src

    except Exception:
        return ""

    return ""