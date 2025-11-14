#!/usr/bin/env python3
"""
reupload_server_full.py (with credential verification)
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

DEFAULT_CFG = {
    "auth_method": None,
    "roblosecurity": None,
    "x_api_key": None,
    "port": None,
    "download_endpoint": "https://apis.roblox.com/asset-delivery-api/v1/assetId/{assetId}",
    "download_fallback": "https://assetdelivery.roblox.com/v1/asset/?id={assetId}",
    "upload_endpoint": "https://apis.roblox.com/assets/v1/assets"
}

# === โหลด config ===
if CFG_PATH.exists():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
else:
    cfg = DEFAULT_CFG.copy()
    CFG_PATH.write_text(json.dumps(DEFAULT_CFG, indent=2), encoding="utf-8")
    print("[INFO] Created config template at", CFG_PATH)

# === สร้าง headers ===
def build_headers():
    headers = {"User-Agent": "AssetReuploaderServer/1.0"}
    if cfg.get("auth_method") == "x_api_key" and cfg.get("x_api_key"):
        headers["x-api-key"] = cfg["x_api_key"]
    if cfg.get("auth_method") == "roblosecurity" and cfg.get("roblosecurity"):
        headers["Cookie"] = f".ROBLOSECURITY={cfg['roblosecurity']}"
    return headers

# === ตรวจสอบ Credential ===
def verify_auth():
    headers = build_headers()
    print("[INFO] Checking authentication validity...")

    try:
        if cfg["auth_method"] == "roblosecurity":
            # ทดสอบโดยเรียก Roblox user API
            r = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=10)
            if r.status_code == 200:
                user = r.json().get("name", "?")
                print(f"[OK] .ROBLOSECURITY valid ✅ (Logged in as {user})")
                return True
            else:
                print(f"[ERR] Invalid .ROBLOSECURITY cookie ❌ (HTTP {r.status_code})")
                return False

        elif cfg["auth_method"] == "x_api_key":
            # ทดสอบโดยเรียก OpenCloud endpoint ที่ต้องใช้ key
            r = requests.get("https://apis.roblox.com/cloud/v2/universes", headers=headers, timeout=10)
            if r.status_code in (200, 403, 404):  # ถ้าได้ตอบกลับ แสดงว่า key ใช้งานได้ระดับหนึ่ง
                print(f"[OK] x-api-key appears valid ✅ (HTTP {r.status_code})")
                return True
            else:
                print(f"[ERR] Invalid x-api-key ❌ (HTTP {r.status_code})")
                return False
        else:
            print("[ERR] Unknown auth method.")
            return False
    except Exception as e:
        print(f"[ERR] Auth check failed: {e}")
        return False

# === Setup ===
def cli_setup():
    print("=== Reupload Server Setup ===")
    print("Choose auth method:")
    print("  1) .ROBLOSECURITY cookie")
    print("  2) x-api-key (OpenCloud)")
    while True:
        choice = input("Choice (1/2): ").strip()
        if choice in ("1", "2"):
            break

    if choice == "1":
        cfg["auth_method"] = "roblosecurity"
        val = input("Enter .ROBLOSECURITY cookie: ").strip()
        cfg["roblosecurity"] = val
    else:
        cfg["auth_method"] = "x_api_key"
        val = input("Enter x-api-key (OpenCloud): ").strip()
        cfg["x_api_key"] = val

    suggested = random.randint(20000, 40000)
    p = input(f"Enter port to run server on (or press Enter to use {suggested}): ").strip()
    try:
        cfg["port"] = int(p) if p else suggested
    except:
        cfg["port"] = suggested

    # ตรวจสอบ Credential ก่อนเปิดพอร์ต
    print("\n[STEP] Verifying credentials...")
    if not verify_auth():
        print("[FATAL] Authentication failed. Please check your .ROBLOSECURITY or x-api-key.")
        sys.exit(1)

    CFG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"\n[INFO] Auth verified successfully ✅")
    print(f"[INFO] Config saved at {CFG_PATH}")
    print(f"[INFO] Server will listen on http://localhost:{cfg['port']}\n")

# === ตัวช่วยอื่น ===
def guess_mime(filename):
    t,_ = mimetypes.guess_type(filename)
    return t or "application/octet-stream"

def download_asset(asset_id):
    url = cfg["download_endpoint"].format(assetId=asset_id)
    headers = build_headers()
    try:
        r = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        return False, f"Download error: {e}"
    if r.status_code >= 400:
        fb = cfg["download_fallback"].format(assetId=asset_id)
        r2 = requests.get(fb, headers=headers, timeout=10)
        if r2.status_code >= 400:
            return False, f"Download failed {r.status_code} + fallback {r2.status_code}"
        r = r2
    return True, {"bytes": r.content, "filename": f"asset_{asset_id}.rbxm"}

def upload_asset(file_bytes, filename, displayName, assetType):
    url = cfg["upload_endpoint"]
    headers = build_headers()
    request_payload = {
        "assetType": assetType,
        "displayName": displayName,
        "description": f"Reuploaded at {time.ctime()}",
        "creationContext": {}
    }
    files = {
        "request": (None, json.dumps(request_payload), "application/json"),
        "fileContent": (filename, file_bytes, guess_mime(filename))
    }
    r = requests.post(url, headers=headers, files=files, timeout=30)
    if r.status_code >= 400:
        return False, f"Upload failed {r.status_code}: {r.text[:300]}"
    return True, r.json()

# === Process ===
def process_list(items):
    results = []
    for idx, item in enumerate(items):
        oldId = item.get("oldId")
        name = item.get("name", f"item_{idx}")
        print(f"[{idx+1}/{len(items)}] Processing {oldId} -> {name}")
        ok, data = download_asset(oldId)
        if not ok:
            results.append({"oldId": oldId, "status": "download_failed"})
            continue
        ok2, res = upload_asset(data["bytes"], data["filename"], name, "Animation")
        results.append({"oldId": oldId, "status": "ok" if ok2 else "upload_failed"})
        time.sleep(0.3)
    return results

# === Flask server ===
app = Flask("asset_reupload_server")

@app.route("/api/reupload_list", methods=["POST"])
def api_reupload_list():
    payload = request.get_json(force=True, silent=True)
    if not payload or "items" not in payload:
        return jsonify({"error": "Invalid payload"}), 400
    return jsonify({"results": process_list(payload["items"])})

@app.route("/api/ping")
def ping():
    return jsonify({"pong": True})

# === Main ===
if __name__ == "__main__":
    cli_setup()
    port = int(cfg.get("port", 9229))
    print(f"[READY] Server listening on port {port}")
    app.run(host="0.0.0.0", port=port)
