import json
import random
import re
import string
import time
from typing import Any, Dict
from bs4 import BeautifulSoup
import websocket

from curl_cffi import requests as cf_requests
from curl_cffi.requests import Session


BASE_URL = "https://shengsiong.com.sg"
WS_BASE = "wss://shengsiong.com.sg/sockjs"
BASE_IMG = "https://ssecomm.s3-ap-southeast-1.amazonaws.com/products/lg/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
}

# Module-level session — shared between HTTP cookie fetch and WS connection
_session = Session(impersonate="chrome120")
_session.headers.update(HEADERS)


def _random_server_id() -> str:
    return str(random.randint(0, 999)).zfill(3)


def _random_session_id(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _make_product_link(slug: str) -> str:
    return f"{BASE_URL}/product/{slug}"


def _build_method_payload(query: str, page: int = 1, page_size: int = 24) -> Dict[str, Any]:
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


def _send_sockjs_frame(ws, payload: Dict[str, Any]) -> None:
    frame = json.dumps([json.dumps(payload)])
    ws.send(frame)


def _warm_session() -> None:
    """Hit the homepage so _session holds valid Incapsula cookies before WS connect."""
    resp = _session.get(BASE_URL, timeout=20)
    resp.raise_for_status()
    print("[SS] cookies:", "; ".join(f"{k}={v}" for k, v in _session.cookies.get_dict().items()))


def _search_inner(query: str, page: int, page_size: int, timeout: float):
    _warm_session()

    cookie_str = "; ".join(f"{k}={v}" for k, v in _session.cookies.get_dict().items())

    server_id = _random_server_id()
    session_id = _random_session_id()
    ws_url = f"{WS_BASE}/{server_id}/{session_id}/websocket"
    print("[SS] opening websocket:", ws_url)

    ws = websocket.create_connection(
        ws_url,
        timeout=timeout,
        header=[
            f"Origin: {BASE_URL}",
            f"User-Agent: {HEADERS['User-Agent']}",
            f"Cookie: {cookie_str}",
        ],
    )

    try:
        target_method_id = "1"

        # 1) Wait for SockJS open frame
        start = time.time()
        while time.time() - start < timeout:
            raw = ws.recv()
            if raw == "o":
                break
        else:
            raise TimeoutError("Did not receive SockJS open frame.")

        # 2) Send Meteor DDP connect
        _send_sockjs_frame(ws, {
            "msg": "connect",
            "version": "1",
            "support": ["1", "pre2", "pre1"],
        })

        # 3) Wait for DDP connected ack
        start = time.time()
        connected = False
        while time.time() - start < timeout:
            raw = ws.recv()
            if raw == "h":
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

        print("[SS] websocket connected")

        # 4) Send search method
        _send_sockjs_frame(ws, _build_method_payload(query, page=page, page_size=page_size))

        # 5) Wait for result
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
                if data.get("msg") == "result" and data.get("id") == target_method_id:
                    products = data.get("result", []) or []
                    cleaned = [
                        _format_result(item)
                        for item in products
                        if item.get("listingOnEcomm", False)
                    ]
                    print("[SS] cleaned found:", len(cleaned))
                    return cleaned

        return []

    finally:
        try:
            ws.close()
        except Exception:
            pass


def search(keywords: str, page: int = 1, page_size: int = 24, timeout: float = 20.0):
    query = keywords.strip()
    print("[SS] query:", query)

    if not query:
        return []

    print("[SS] starting search", query)

    for attempt in range(2):
        try:
            return _search_inner(query, page, page_size, timeout)
        except Exception as e:
            if attempt == 1:
                raise
            print(f"[SS] attempt {attempt + 1} failed ({e}), retrying...")
            time.sleep(1)


### Helper functions

def _extract_image(item, link):
    img_key = item.get("imgKey")
    if img_key:
        return f"{BASE_IMG}{img_key}.0.jpg"
    return _fetch_image_from_page(link)


def _fetch_image_from_page(link):
    try:
        resp = cf_requests.get(link, impersonate="chrome120", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        img = soup.find("img")
        if img:
            return img.get("src") or img.get("data-src") or ""
    except Exception:
        return ""
    return ""
