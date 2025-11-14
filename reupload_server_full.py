#!/usr/bin/env python3
"""
reupload_server_full.py (with credential verification)
(อัปเดต: เพิ่มการพิมพ์สีเขียว)
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

# =================================================================
# [NEW] 1. เพิ่มการ Import และรัน colorama
# =================================================================
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True) # <-- ทำให้สีกลับมาเป็นปกติอัตโนมัติ
except Exception:
    print("Colorama is recommended for colored output: pip install colorama")
    # สร้าง Class ปลอมไว้ ถ้าหากไม่ได้ติดตั้ง colorama
    class DummyFore: __getattr__ = lambda self, name: ""
    Fore = DummyFore()
# =================================================================


BASE_DIR = Path(__file__).parent if '__file__' in locals() else Path.cwd()
CFG_PATH = BASE_DIR / "reupload_server_config.json"

DEFAULT_CFG = {
    "auth_method": None,
    "roblosecurity": None,
    "x_api_key": None,
    "port": None,
    "user_id": None, 
    "download_endpoint": "https://apis.roblox.com/asset-delivery-api/v1/assetId/{assetId}",
    "download_fallback": "https://assetdelivery.roblox.com/v1/asset/?id={assetId}",
    "upload_endpoint": "https://apis.roblox.com/assets/v1/assets"
}

# (โค้ดส่วน โหลด config, สร้าง headers, verify_auth, cli_setup, 
#  guess_mime, download_asset, upload_asset... ทั้งหมดเหมือนเดิม)

# === โหลด config ===
if CFG_PATH.exists():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    if "user_id" not in cfg:
        cfg["user_id"] = None
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
            r = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=10)  
            if r.status_code == 200:
                user_json = r.json()
                user = user_json.get("name", "?")
                user_id = user_json.get("id")
                if not user_id:
                    print(f"[ERR] .ROBLOSECURITY valid, but could not retrieve user ID.")
                    return False
                cfg['user_id'] = user_id 
                print(f"[OK] .ROBLOSECURITY valid ✅ (Logged in as {user}, ID: {user_id})")  
                return True  
            else:  
                print(f"[ERR] Invalid .ROBLOSECURITY cookie ❌ (HTTP {r.status_code})")  
                return False  
        elif cfg["auth_method"] == "x_api_key":  
            cfg['user_id'] = None 
            r = requests.get("https://apis.roblox.com/cloud/v2/universes", headers=headers, timeout=10)  
            if r.status_code in (200, 403, 404):
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

# =================================================================
# [NEW] 2. สร้างฟังก์ชันพิมพ์ข้อความสีเขียว
# =================================================================
def print_success_location(newId):
    """
    พิมพ์ข้อความสีเขียว พร้อมลิงก์ที่ถูกต้องตาม auth_method
    """
    dashboard_url = ""
    if cfg.get("auth_method") == "roblosecurity":
        # ถ้าใช้ Cookie, มันจะไปที่ "My Creations"
        dashboard_url = f"https://create.roblox.com/dashboard/creations/configure?id={newId}"
    else:
        # ถ้าใช้ API Key, มันจะไปที่ "Group Creations"
        # เราไม่รู้ Group ID, แต่เราลิงก์ไปที่หน้า Asset ตรงๆ ได้
        dashboard_url = f"https://www.roblox.com/library/{newId}/"
    
    # พิมพ์ข้อความสีเขียว
    print(Fore.GREEN + f"    -> Asset is ready. Configure it at: {dashboard_url}")
# =================================================================


def find_existing_asset(displayName, assetType):
    if cfg.get("auth_method") != "roblosecurity" or not cfg.get("user_id"):
        return False, None
    userId = cfg["user_id"]
    headers = build_headers()
    cursor = ""
    url_template = f"https://economy.roblox.com/v2/users/{userId}/assets/creations?assetTypes={assetType}&limit=100"
    
    while True: 
        url = url_template
        if cursor:
            url += f"&cursor={cursor}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"[WARN] Inventory check failed (HTTP {r.status_code}). Skipping check.")
                return False, None
            data = r.json()
            if not data.get("data"):
                return False, None 
            for item in data["data"]:
                if item.get("name") == displayName:
                    description = item.get("description", "")
                    if description.startswith("Reuploaded at "): 
                        asset_id = item.get("assetId")
                        if asset_id:
                            print(f"[OK] Found matching asset: {displayName} -> {asset_id}")
                            return True, asset_id
            cursor = data.get("nextPageCursor")
            if not cursor:
                break 
        except Exception as e:
            print(f"[WARN] Inventory check error: {e}. Skipping check.")
            return False, None
    return False, None


def process_single(item):
    oldId = item.get("oldId")
    name = item.get("name", f"item_{oldId}")
    assetType = item.get("type", "Animation")
    check_existing = item.get("check_existing", False) 
    
    if check_existing:
        found, existing_id = find_existing_asset(name, assetType)
        if found:
            print(f"[SKIP] Using existing asset {existing_id} for {name}.")
            # =================================================================
            # [NEW] 3. เรียกใช้ฟังก์ชันพิมพ์สีเขียว (จุดที่ 1: ตอน Skip)
            # =================================================================
            print_success_location(existing_id)
            return {"oldId": oldId, "newId": existing_id, "status": "ok", "name": name, "skipped": True}

    print(f"[+] Processing (New Upload) {oldId} -> {name} (Type: {assetType})")
    
    ok, data = download_asset(oldId)
    if not ok:
        print(f"[ERR] Download failed for {oldId}: {data}")
        return {"oldId": oldId, "status": "download_failed", "error": data, "name": name}
        
    ok2, res = upload_asset(data["bytes"], data["filename"], name, assetType)
    
    if not ok2:
        print(f"[ERR] Upload failed for {oldId}: {res}")
        return {"oldId": oldId, "status": "upload_failed", "error": res, "name": name}
    
    newId = res.get("assetId")
    if not newId:
        print(f"[ERR] Upload succeeded but no assetId found for {oldId}.")
        return {"oldId": oldId, "status": "upload_failed", "error": "No assetId in response", "name": name}

    print(f"[OK] Reupload success: {oldId} -> {newId}")
    # =================================================================
    # [NEW] 3. เรียกใช้ฟังก์ชันพิมพ์สีเขียว (จุดที่ 2: ตอน Upload สำเร็จ)
    # =================================================================
    print_success_location(newId)
    return {"oldId": oldId, "newId": newId, "status": "ok", "name": name}


def process_list(items):
    results = []
    for idx, item in enumerate(items):
        result = process_single(item)
        results.append(result)
        time.sleep(0.3) 
    return results

# === Flask server === (เหมือนเดิม)

app = Flask("asset_reupload_server")

@app.route("/api/reupload_single", methods=["POST"])
def api_reupload_single():
    payload = request.get_json(force=True, silent=True)
    if not payload or "oldId" not in payload:
        return jsonify({"error": "Invalid payload, missing oldId"}), 400
    
    result = process_single(payload)
    return jsonify(result)

@app.route("/api/reupload_list", methods=["POST"])
def api_reupload_list():
    payload = request.get_json(force=True, silent=True)
    if not payload or "items" not in payload:
        return jsonify({"error": "Invalid payload"}), 400
    return jsonify({"results": process_list(payload["items"])})

@app.route("/api/ping")
def ping():
    return jsonify({"pong": True})

# === Main === (เหมือนเดิม)
if __name__ == "__main__":
    cli_setup()
    port = int(cfg.get("port", 9229))
    print(f"[READY] Server listening on port {port}")
    app.run(host="0.0.0.0", port=port)
