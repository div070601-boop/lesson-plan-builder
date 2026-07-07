"""Test Microsoft Graph shares API with the new OneDrive link."""
import httpx
import base64
import json

SHARE_URL = "https://1drv.ms/f/c/e2665fc4072ad507/IgA284_TEL2lTrzd83mPBWlUAUhzf6gWj4ITo5jaFrPDJk4?e=DNSVzo"

# Encode share URL to Graph share token
encoded = base64.urlsafe_b64encode(SHARE_URL.encode()).decode().rstrip('=')
share_token = f"u!{encoded}"

client = httpx.Client(follow_redirects=True, timeout=20)
headers = {"Accept": "application/json"}

# 1. Try root item
print("=== Graph: Get root item ===")
r = client.get(f"https://api.onedrive.com/v1.0/shares/{share_token}/root", headers=headers)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  Name: {d.get('name')}")
    print(f"  Type: {'folder' if 'folder' in d else 'file'}")
    if 'folder' in d:
        print(f"  Children: {d['folder'].get('childCount')}")
else:
    print(f"  {r.text[:300]}")

# 2. Try children
print("\n=== Graph: List children ===")
r2 = client.get(f"https://api.onedrive.com/v1.0/shares/{share_token}/root/children", headers=headers)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    items = r2.json().get("value", [])
    print(f"Found {len(items)} items:\n")
    for item in items:
        is_dir = "folder" in item
        name = item.get("name", "?")
        size = item.get("size", 0)
        children = item.get("folder", {}).get("childCount", 0) if is_dir else None
        dl = item.get("@content.downloadUrl", "")
        print(f"  {'[DIR]' if is_dir else '[FILE]'} {name}")
        print(f"       Size: {size:,} bytes" + (f"  | {children} children" if children else ""))
        if dl:
            print(f"       Download: {dl[:80]}...")
        print()
else:
    print(f"  {r2.text[:500]}")

# 3. If there are subfolders, try to list their children too
if r2.status_code == 200:
    for item in items:
        if "folder" in item and item["folder"].get("childCount", 0) > 0:
            item_id = item["id"]
            name = item["name"]
            print(f"\n=== Subfolder: {name} ===")
            r3 = client.get(
                f"https://api.onedrive.com/v1.0/shares/{share_token}/root:/{name}:/children",
                headers=headers
            )
            if r3.status_code != 200:
                # Try alternate path
                r3 = client.get(
                    f"https://api.onedrive.com/v1.0/shares/{share_token}/items/{item_id}/children",
                    headers=headers
                )
            print(f"Status: {r3.status_code}")
            if r3.status_code == 200:
                sub_items = r3.json().get("value", [])
                for si in sub_items:
                    si_dir = "folder" in si
                    si_name = si.get("name", "?")
                    si_size = si.get("size", 0)
                    print(f"  {'[DIR]' if si_dir else '[FILE]'} {si_name}  ({si_size:,} bytes)")
            else:
                print(f"  {r3.text[:200]}")
