"""
Interactive Browser Flow for Microsoft Graph API.
Since this code runs on your local machine, it will pop open a browser window
for you to log in, and capture the token automatically!
"""
import msal
import httpx
import json
import base64

# User's Custom App Registration Client ID
CLIENT_ID = "ac28569b-b562-42a6-86d0-5126a1975641"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Files.Read.All", "Sites.Read.All"]

cache = msal.SerializableTokenCache()
app = msal.PublicClientApplication(
    CLIENT_ID, authority=AUTHORITY, token_cache=cache
)

print("Starting Interactive Login... Please check your browser!")

# This will open a browser window on your machine
result = app.acquire_token_interactive(scopes=SCOPES)

if "access_token" in result:
    print("\nSuccess! Got access token.")
    token = result["access_token"]
    
    # Save the token cache
    with open(".onedrive_token.json", "w") as f:
        f.write(app.token_cache.serialize())
        
    # Test the share link
    SHARE_URL = "https://1drv.ms/f/c/e2665fc4072ad507/IgA284_TEL2lTrzd83mPBWlUAUhzf6gWj4ITo5jaFrPDJk4?e=DNSVzo"
    encoded = base64.urlsafe_b64encode(SHARE_URL.encode()).decode().rstrip('=')
    share_token = f"u!{encoded}"
    
    client = httpx.Client(timeout=20)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    print("\nFetching files from OneDrive...")
    r = client.get(f"https://graph.microsoft.com/v1.0/shares/{share_token}/root/children", headers=headers)
    print(f"Share API Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"\nFound {len(data.get('value', []))} items in the folder:")
        for item in data.get("value", []):
            print(f"  - {item.get('name')}")
    else:
        print(r.text)
else:
    print("Authentication failed.")
    print(result.get("error"))
    print(result.get("error_description"))
