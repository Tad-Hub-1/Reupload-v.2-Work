#!/usr/bin/env python3
"""
reupload_server_full.py
Standalone reupload server.

Flow:
- On start, choose auth method:
    1) .ROBLOSECURITY cookie
    2) x-api-key (OpenCloud)
  (you input credential; it is stored only in memory / config.json in same folder)
- Server listens on chosen port (suggested random if you accept)
- Endpoint: POST /api/reupload_list
    payload: { "items": [ { "oldId": 123, "name": "Run01", "type": "Animation" }, ... ] }
  Server will process items sequentially: download -> upload -> build results list
- Server responds JSON:
    { "results": [ { "oldId":123, "newId":987, "name":"Run01", "status":"ok" }, ... ] }

WARNING: This is a template. You must supply credentials and maybe tweak endpoints/fields for asset type.
"""

import os, sys, json, random, time, mimetypes
from pathlib import Path
from threading import Thread

try:
    from flask import Flask, request, jsonify
except Exception:
    print("Flask is required. Install: pip install flask requests")
    sys.exit(1)

try:
    import requests
except Exception:
    print("Requests required. Install: pip install requests")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
CFG_PATH = BASE_DIR / "reupload_server_config.json"

# default config template
DEFAULT_CFG = {
    "auth_method": None,      # "roblosecurity" or "x_api_key"
    "roblosecurity": None,
    "x_api_key": None,
    "port": None,
    # endpoints (may need change depending on Roblox API)
    "download_endpoint": "https://apis.roblox.com/asset-delivery-api/v1/assetId/{assetId}",
    "download_fallback": "https://assetdelivery.roblox.com/v1/asset/?id={assetId}",
    "upload_endpoint": "https://apis.roblox.com/assets/v1/assets"
}

# load or create config
if CFG_PATH.exists():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
else:
    cfg = DEFAULT_CFG.copy()
    CFG_PATH.write_text(json.dumps(DEFAULT_CFG, indent=2), encoding="utf-8")
    print("[INFO] Created config template at", CFG_PATH)

# CLI: choose auth method and port
def cli_setup():
    print("=== Reupload Server Setup ===")
    print("Choose auth method:")
    print("  1) .ROBLOSECURITY cookie (less recommended)")
    print("  2) x-api-key (OpenCloud) (recommended)")
    while True:
        choice = input("Choice (1/2): ").strip()
        if choice in ("1","2"):
            break
    if choice == "1":
        cfg["auth_method"] = "roblosecurity"
        val = input("Enter .ROBLOSECURITY cookie (paste then Enter): ").strip()
        cfg["roblosecurity"] = val
    else:
        cfg["auth_method"] = "x_api_key"
        val = input("Enter x-api-key (OpenCloud): ").strip()
        cfg["x_api_key"] = val

    # port
    suggested = random.randint(20000, 40000)
    p = input(f"Enter port to run server on (or press Enter to use {suggested}): ").strip()
    try:
        cfg["port"] = int(p) if p else suggested
    except:
        cfg["port"] = suggested

    # save config locally (permissions: user only recommended)
    try:
        CFG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("[INFO] Config saved to", CFG_PATH)
    except Exception as e:
        print("[WARN] Could not save config:", e)

    print(f"Server will listen on http://localhost:{cfg['port']}")
    print("Please copy this port into the Plugin's port field in Roblox Studio.")
    print("Starting server...")

# helper: build headers
def build_headers():
    headers = {"User-Agent": "AssetReuploaderServer/1.0"}
    if cfg.get("auth_method") == "x_api_key" and cfg.get("x_api_key"):
        headers["x-api-key"] = cfg["x_api_key"]
    if cfg.get("auth_method") == "roblosecurity" and cfg.get("roblosecurity"):
        headers["Cookie"] = f".ROBLOSECURITY={cfg['roblosecurity']}"
    return headers

# guess mime
def guess_mime(filename):
    t,_ = mimetypes.guess_type(filename)
    return t or "application/octet-stream"

# download helpers (best-effort)
def download_asset(asset_id):
    # try primary endpoint
    url = cfg["download_endpoint"].format(assetId=asset_id)
    headers = build_headers()
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    except Exception as e:
        return False, f"Download error: {e}"
    if r.status_code >= 400:
        # fallback
        fb = cfg.get("download_fallback").format(assetId=asset_id)
        try:
            r2 = requests.get(fb, headers=headers, timeout=12, allow_redirects=True)
            if r2.status_code >= 400:
                return False, f"Download failed primary {r.status_code} and fallback {r2.status_code}. primary_text={r.text[:300]}"
            r = r2
        except Exception as e:
            return False, f"Download fallback error: {e}"
    # content
    filename = None
    cd = r.headers.get("Content-Disposition")
    if cd and "filename=" in cd:
        filename = cd.split("filename=")[-1].strip(' "')
    if not filename:
        # infer ext from content-type
        ct = r.headers.get("Content-Type","")
        ext = ""
        if "mpeg" in ct or "audio" in ct:
            ext = ".mp3"
        elif "xml" in ct:
            ext = ".rbxm"
        filename = f"asset_{asset_id}{ext}"
    return True, {"bytes": r.content, "filename": filename, "status": r.status_code, "headers": dict(r.headers)}

# upload helper (multipart with 'request' and 'fileContent')
def upload_asset(file_bytes, filename, displayName, assetType):
    url = cfg["upload_endpoint"]
    headers = build_headers()
    # build request payload - you may need to adapt fields for proper assetType and creation context
    request_payload = {
        "assetType": assetType,   # e.g. "Animation" or "Audio" - may require numeric id in real API
        "displayName": displayName,
        "description": f"Reuploaded by AssetReuploaderServer at {time.ctime()}",
        "creationContext": {}
    }
    files = {
        "request": (None, json.dumps(request_payload), "application/json"),
        "fileContent": (filename, file_bytes, guess_mime(filename))
    }
    try:
        r = requests.post(url, headers=headers, files=files, timeout=30)
    except Exception as e:
        return False, f"Upload request failed: {e}"
    if r.status_code >= 400:
        return False, f"Upload failed {r.status_code}: {r.text[:600]}"
    try:
        return True, r.json()
    except Exception:
        return False, f"Upload returned non-json: {r.text[:600]}"

# process list sequentially
def process_list(items):
    results = []
    for idx, item in enumerate(items):
        oldId = item.get("oldId")
        name = item.get("name") or f"item_{idx}"
        typ = item.get("type") or "Animation"
        print(f"[{idx+1}/{len(items)}] Processing {typ} {oldId} -> {name}")
        ok, data = download_asset(oldId)
        if not ok:
            print("[ERR] Download failed:", data)
            results.append({"oldId": oldId, "newId": None, "status": "download_failed", "error": data, "name": name})
            continue
        bytes_ = data["bytes"]
        filename = data["filename"]
        # choose assetType parameter for upload API - adapt as needed
        upload_type = "Animation" if typ.lower().startswith("anim") else "Audio" if typ.lower().startswith("sound") else "Model"
        ok2, res = upload_asset(bytes_, filename, displayName=name, assetType=upload_type)
        if not ok2:
            print("[ERR] Upload failed:", res)
            results.append({"oldId": oldId, "newId": None, "status": "upload_failed", "error": res, "name": name})
            continue
        # try to parse new asset id
        new_id = None
        if isinstance(res, dict):
            # common fields may vary by API version
            new_id = res.get("assetId") or res.get("id") or res.get("data", {}).get("assetId")
        results.append({"oldId": oldId, "newId": new_id, "status": "ok" if new_id else "ok_no_id", "response": res, "name": name})
        print(f"[OK] {oldId} -> {new_id}")
        # small delay to avoid rate limit
        time.sleep(0.4)
    return results

# Flask server
app = Flask("asset_reupload_server")

@app.route("/api/reupload_list", methods=["POST"])
def api_reupload_list():
    payload = request.get_json(force=True, silent=True)
    if not payload or "items" not in payload:
        return jsonify({"error": "Invalid payload, 'items' missing"}), 400
    items = payload["items"]
    # process sync (could be heavy) — return results when done
    results = process_list(items)
    return jsonify({"results": results, "count": len(results)}), 200

@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"pong": True})

# main
if __name__ == "__main__":
    cli_setup()
    port = int(cfg.get("port", 9229))
    print("Server listening on port", port)
    # run in main thread
    app.run(host="0.0.0.0", port=port)
