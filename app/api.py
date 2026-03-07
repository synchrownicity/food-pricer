import flask
from flask import request, jsonify
from app.ntuc import search as searchNTUC
from app.cold_storage import search as searchColdStorage
from app.sheng_siong import search as searchShengSiong

app = flask.Flask(__name__)
app.config["DEBUG"] = True


def _safe_search(fn, query):
    try:
        return fn(query)
    except Exception as e:
        print(f"[WARN] scraper failed: {fn.__name__}: {e}")
        return []


@app.route("/", methods=["POST"])
def queryAll():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"results": [], "error": "Missing 'query' in JSON body"}), 400

    results_cold_storage = _safe_search(searchColdStorage, query)
    results_ntuc = _safe_search(searchNTUC, query)
    results_sheng_siong = _safe_search(searchShengSiong, query)

    results_combined = results_cold_storage + results_ntuc + results_sheng_siong
    return jsonify({"results": results_combined})


@app.route("/ntuc/", methods=["POST"])
def queryNTUC():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"results": [], "error": "Missing 'query' in JSON body"}), 400

    return jsonify({"results": _safe_search(searchNTUC, query)})


@app.route("/cold-storage/", methods=["POST"])
def queryColdStorage():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"results": [], "error": "Missing 'query' in JSON body"}), 400

    return jsonify({"results": _safe_search(searchColdStorage, query)})


@app.route("/sheng-siong/", methods=["POST"])
def queryShengSiong():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"results": [], "error": "Missing 'query' in JSON body"}), 400

    return jsonify({"results": _safe_search(searchShengSiong, query)})