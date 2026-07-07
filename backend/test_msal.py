"""
Test MSAL Device Code Flow with a Public Client ID.
This avoids needing an Azure App Registration.
"""
import msal
import httpx
import json
import base64
import time

# Azure CLI Public Client ID
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Files.Read.All", "Sites.Read.All"]

app = msal.PublicClientApplication(
    CLIENT_ID, authority=AUTHORITY
)

# Initiate Device Code Flow
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    print("Failed to create device flow. Err: %s" % json.dumps(flow, indent=4))
    exit(1)

with open("auth_message.txt", "w") as f:
    f.write(flow["message"])
print("Auth message written to auth_message.txt")

# We will stop here to let the user authenticate, then run a second script to get the token.
with open("flow.json", "w") as f:
    json.dump(flow, f)

