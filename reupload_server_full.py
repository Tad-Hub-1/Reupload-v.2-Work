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

# สลับ __file__ เป็น 'file' เพื่อให้เข้ากับโค้ดเดิมของคุณ
BASE_DIR = Path(__file__).parent if '__file__' in locals() else Path.cwd()
CFG_PATH = BASE_DIR / "reupload_server_config.json"

DEFAULT_CFG = {
    "auth_method": None,
    "roblosecurity": None,
    "x_api_key": None,
    "port": None,
    "user_id": None, # [NEW] เพิ่ม field สำหรับเก็บ User ID
    "download_endpoint": "https://apis.roblox.com/asset-delivery-api/v1/assetId/{assetId}",
    "download_fallback": "https://assetdelivery.roblox.com/v1/asset/?id={assetId}",
    "upload_endpoint": "https://apis.roblox.com/assets/v1/assets"
}

# === โหลด config ===

if CFG_PATH.exists():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    # ตรวจสอบว่ามี key ใหม่หรือยัง
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
            # [MODIFIED] แก้ไขให้ดึง User ID ด้วย
            r = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=10)  
            if r.status_code == 200:
                user_json = r.json()
                user = user_json.get("name", "?")
                user_id = user_json.get("id")
                if not user_id:
                    print(f"[ERR] .ROBLOSECURITY valid, but could not retrieve user ID.")
                    return False
                cfg['user_id'] = user_id # เก็บ User ID ไว้ใน config
                print(f"[OK] .ROBLOSECURITY valid ✅ (Logged in as {user}, ID: {user_id})")  
                return True  
            else:  
                print(f"[ERR] Invalid .ROBLOSECURITY cookie ❌ (HTTP {r.status_code})")  
                return False  

        elif cfg["auth_method"] == "x_api_key":  
            cfg['user_id'] = None # x-api-key ไม่สามารถใช้ user_id ได้
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
# (ฟังก์ชัน cli_setup() ไม่มีการเปลี่ยนแปลง... สามารถใช้โค้ดเดิมได้)
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
    # [CONFIRMED] ใช้ description format ตามที่ผู้ใช้ต้องการ
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

## ----------------------------------------------------------------
## [NEW] ฟังก์ชันสำหรับค้นหา Asset ที่มีอยู่
## ----------------------------------------------------------------
def find_existing_asset(displayName, assetType):
    """
    ค้นหาคลังของผู้ใช้เพื่อหา Asset ที่มีชื่อและ Description ตรงกัน
    ทำงานเฉพาะเมื่อใช้ .ROBLOSECURITY เท่านั้น
    """
    if cfg.get("auth_method") != "roblosecurity" or not cfg.get("user_id"):
        if cfg.get("auth_method") == "x_api_key":
            # แจ้งเตือนแค่ครั้งแรกๆ (ถ้าจำเป็น) แต่การข้ามไปเงียบๆ ดีกว่า
            pass # print("[INFO] Asset check skipped (only supported for .ROBLOSECURITY auth).")
        return False, None

    # print(f"[INFO] Checking inventory for existing asset named: {displayName}")
    
    userId = cfg["user_id"]
    headers = build_headers()
    cursor = ""
    # ใช้ API ค้นหาคลัง (Creations)
    url_template = f"https://economy.roblox.com/v2/users/{userId}/assets/creations?assetTypes={assetType}&limit=100"
    
    while True: # วน Loop สำหรับ Pagination
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
                return False, None # ไม่เจอ

            for item in data["data"]:
                # 1. เช็คชื่อ
                if item.get("name") == displayName:
                    # 2. เช็ค Description
                    description = item.get("description", "")
                    # [IMPORTANT] เราเช็คว่า "ขึ้นต้นด้วย" ไม่ใช่ "ตรงกันเป๊ะ"
                    # เพราะเวลาที่ reupload จะไม่ตรงกัน
                    if description.startswith("Reuploaded at "): 
                        asset_id = item.get("assetId")
                        if asset_id:
                            print(f"[OK] Found matching asset: {displayName} -> {asset_id}")
                            return True, asset_id
            
            cursor = data.get("nextPageCursor")
            if not cursor:
                break # นี่คือหน้าสุดท้าย
                
        except Exception as e:
            print(f"[WARN] Inventory check error: {e}. Skipping check.")
            return False, None
    
    # วนครบทุกหน้าแล้ว ไม่เจอ
    return False, None

## ----------------------------------------------------------------
## [MODIFIED] แก้ไข process_single ให้เช็คก่อน
## ----------------------------------------------------------------
def process_single(item):
    oldId = item.get("oldId")
    name = item.get("name", f"item_{oldId}")
    assetType = item.get("type", "Animation")
    
    # ----------------------------------------------------------------
    # [NEW] ตรวจสอบว่ามี Asset นี้อยู่แล้วหรือยัง
    # ----------------------------------------------------------------
    found, existing_id = find_existing_asset(name, assetType)
    if found:
        print(f"[SKIP] Using existing asset {existing_id} for {name}.")
        # ส่ง ID ที่หาเจอ กลับไปแทน ID ที่อัปโหลดใหม่
        return {"oldId": oldId, "newId": existing_id, "status": "ok", "name": name, "skipped": True}
    # ----------------------------------------------------------------

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
    return {"oldId": oldId, "newId": newId, "status": "ok", "name": name}


def process_list(items):
    results = []
    for idx, item in enumerate(items):
        result = process_single(item)
        results.append(result)
        time.sleep(0.3) 
    return results

# === Flask server ===

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

# === Main ===

if __name__ == "__main__":
    cli_setup()
    port = int(cfg.get("port", 9229))
    print(f"[READY] Server listening on port {port}")
    app.run(host="0.0.0.0", port=port)
