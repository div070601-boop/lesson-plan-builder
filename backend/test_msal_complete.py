"""
Poll for token after user completes device flow.
"""
import msal
import httpx
import json
import base64

CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/common"

app = msal.PublicClientApplication(
    CLIENT_ID, authority=AUTHORITY
)

with open("flow.json", "r") as f:
    flow = json.load(f)

print("Polling for token... (Waiting for you to authenticate in browser)")
result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    print("\nSuccess! Got access token.")
    token = result["access_token"]
    
    # Save the token cache
    with open(".onedrive_token.json", "w") as f:
        json.dump(result, f)
        
    # Test the share link
    SHARE_URL = "https://1drv.ms/f/c/e2665fc4072ad507/IgA284_TEL2lTrzd83mPBWlUAUhzf6gWj4ITo5jaFrPDJk4?e=DNSVzo"
    encoded = base64.urlsafe_b64encode(SHARE_URL.encode()).decode().rstrip('=')
    share_token = f"u!{encoded}"
    
    client = httpx.Client(timeout=20)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    r = client.get(f"https://graph.microsoft.com/v1.0/shares/{share_token}/root/children", headers=headers)
    print(f"\nShare API Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Found {len(data.get('value', []))} items:")
        for item in data.get("value", []):
            print(f"  - {item.get('name')}")
    else:
        print(r.text)
else:
    print("Authentication failed.")
    print(result.get("error"))
    print(result.get("error_description"))
