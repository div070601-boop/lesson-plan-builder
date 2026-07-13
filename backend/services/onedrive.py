"""
OneDrive Service — Microsoft Graph API integration for accessing shared folders.
Supports both authenticated Graph API access and local filesystem fallback.

Usage:
  - With Graph credentials: Connects to OneDrive shared folders via Microsoft Graph API
  - Without credentials: Indexes PPTX files from the local `library/` folder
"""

import httpx
import base64
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from config import settings


class OneDriveItem:
    """Represents a file or folder from OneDrive or local filesystem."""

    def __init__(
        self,
        name: str,
        path: str,
        is_folder: bool = False,
        size: int = 0,
        child_count: int = 0,
        download_url: Optional[str] = None,
        item_id: Optional[str] = None,
        modified_at: Optional[str] = None,
    ):
        self.name = name
        self.path = path
        self.is_folder = is_folder
        self.size = size
        self.child_count = child_count
        self.download_url = download_url
        self.item_id = item_id
        self.modified_at = modified_at

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "is_folder": self.is_folder,
            "size": self.size,
            "child_count": self.child_count,
            "download_url": self.download_url,
            "item_id": self.item_id,
            "modified_at": self.modified_at,
        }


def _encode_share_url(share_url: str) -> str:
    """Encode a OneDrive share URL into a Graph API share token.
    See: https://learn.microsoft.com/en-us/graph/api/shares-get
    """
    encoded = base64.urlsafe_b64encode(share_url.encode()).decode().rstrip("=")
    return f"u!{encoded}"


class OneDriveService:
    """Access OneDrive shared folders via Microsoft Graph API."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

    def __init__(self):
        self.client_id = settings.ms_graph_client_id
        self.client_secret = settings.ms_graph_client_secret
        self.tenant_id = settings.ms_graph_tenant_id or "consumers"
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        """Check if OneDrive credentials are configured (client_id is set)."""
        return bool(self.client_id)

    @property
    def has_active_session(self) -> bool:
        """Check if there's a cached OAuth user token (from 'Connect OneDrive')."""
        if not self.client_id:
            return False
        # Check Supabase first
        from services.database import supabase
        if supabase:
            try:
                res = supabase.table("settings").select("value").eq("key", "onedrive_token_cache").execute()
                if len(res.data) > 0 and res.data[0].get("value"):
                    return True
            except Exception:
                pass
        # Fallback: check local file
        return os.path.exists(".onedrive_token.json")

    def _get_msal_app(self, cache=None):
        import msal
        if self.client_secret:
            return msal.ConfidentialClientApplication(
                self.client_id,
                client_credential=self.client_secret,
                authority="https://login.microsoftonline.com/common",
                token_cache=cache
            )
        return msal.PublicClientApplication(
            self.client_id, 
            authority="https://login.microsoftonline.com/common",
            token_cache=cache
        )

    def _load_cache_from_db(self):
        import msal
        cache = msal.SerializableTokenCache()
        # Try Supabase first
        from services.database import supabase
        if supabase:
            try:
                res = supabase.table("settings").select("value").eq("key", "onedrive_token_cache").execute()
                if res.data and res.data[0].get("value"):
                    cache.deserialize(res.data[0]["value"])
                    return cache
            except Exception:
                pass
        # Fallback: local file
        if os.path.exists(".onedrive_token.json"):
            with open(".onedrive_token.json", "r") as f:
                cache.deserialize(f.read())
        return cache

    def _save_cache_to_db(self, cache):
        if cache.has_state_changed:
            from services.database import supabase
            if supabase:
                supabase.table("settings").upsert({
                    "key": "onedrive_token_cache", 
                    "value": cache.serialize()
                }).execute()

    async def _get_access_token(self) -> str:
        """Get an OAuth2 access token. Tries cached user token first, then client credentials flow."""
        import logging
        logger = logging.getLogger(__name__)

        # Strategy 1: Try cached user token (from "Connect OneDrive" OAuth flow)
        cache = self._load_cache_from_db()
        app = self._get_msal_app(cache)
        
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(["Files.Read.All", "Sites.Read.All"], account=accounts[0])
            if result and "access_token" in result:
                self._save_cache_to_db(cache)
                logger.info("Token acquired via cached user session.")
                return result["access_token"]
            logger.warning(f"Silent token acquisition failed: {result.get('error_description') if result else 'no result'}")

        # Strategy 2: Try client credentials flow (app-only, no user login needed)
        if self.client_secret:
            logger.info("No cached user token. Trying client credentials flow...")
            app_cc = self._get_msal_app()
            result = app_cc.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            if result and "access_token" in result:
                logger.info("Token acquired via client credentials flow.")
                return result["access_token"]
            logger.error(f"Client credentials flow failed: {result.get('error_description') if result else 'no result'}")

        raise RuntimeError(
            "Could not acquire OneDrive access token. "
            "Either click 'Connect OneDrive' in the Admin Panel to authenticate, "
            "or ensure your Azure app has Application permissions (Files.Read.All) for client credentials flow."
        )

    def get_auth_url(self, redirect_uri: str) -> str:
        """Get the Microsoft login URL for OAuth web flow."""
        app = self._get_msal_app()
        flow = app.initiate_auth_code_flow(
            scopes=["Files.Read.All", "Sites.Read.All"],
            redirect_uri=redirect_uri
        )
        # Persist flow to file and Supabase so it survives server/container restarts
        with open("flow.json", "w") as f:
            json.dump(flow, f)
        from services.database import supabase
        if supabase:
            try:
                supabase.table("settings").upsert({
                    "key": "onedrive_auth_flow",
                    "value": json.dumps(flow)
                }).execute()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not save auth flow to Supabase: {e}")
        return flow["auth_uri"]

    def acquire_token_by_auth_code(self, query_params: dict, redirect_uri: str) -> dict:
        """Exchange the auth code for a token and save to Supabase."""
        import msal
        import logging
        logger = logging.getLogger(__name__)

        # Load the flow from file or Supabase
        flow = None
        flow_path = Path("flow.json")
        if flow_path.exists():
            with open(flow_path, "r") as f:
                flow = json.load(f)
        
        if not flow:
            from services.database import supabase
            if supabase:
                try:
                    res = supabase.table("settings").select("value").eq("key", "onedrive_auth_flow").execute()
                    if res.data and res.data[0].get("value"):
                        flow = json.loads(res.data[0]["value"])
                except Exception as e:
                    logger.warning(f"Could not load auth flow from Supabase: {e}")

        if not flow:
            raise ValueError("Auth flow not found in file or Supabase. Please click 'Connect OneDrive' again.")

        # Create a token cache so MSAL writes the tokens into it
        cache = msal.SerializableTokenCache()

        # MUST use the same app (same client_id + authority + secret) and pass the cache
        app = self._get_msal_app(cache=cache)

        result = app.acquire_token_by_auth_code_flow(flow, query_params)

        if "error" in result:
            logger.error(f"MSAL Error: {result}")
            raise RuntimeError(f"Failed to acquire token: {result.get('error_description', result.get('error'))}")

        # Save token cache to Supabase
        from services.database import supabase
        if supabase:
            try:
                supabase.table("settings").upsert({
                    "key": "onedrive_token_cache",
                    "value": cache.serialize()
                }).execute()
                logger.info("OneDrive token cache saved to Supabase.")
            except Exception as e:
                logger.error(f"Failed to save token cache to Supabase: {e}")
                # Fallback: save to local file
                with open(".onedrive_token.json", "w") as f:
                    f.write(cache.serialize())
                logger.info("Token cache saved to local file as fallback.")
        else:
            # No Supabase, save locally
            with open(".onedrive_token.json", "w") as f:
                f.write(cache.serialize())

        # Clean up flow file and Supabase entry
        flow_path.unlink(missing_ok=True)
        if supabase:
            try:
                supabase.table("settings").delete().eq("key", "onedrive_auth_flow").execute()
            except Exception:
                pass

        return result

    async def list_shared_folder(self, share_url: str) -> list[OneDriveItem]:
        """List all items in a shared OneDrive folder."""
        if not self.is_configured:
            raise RuntimeError("OneDrive is not configured. Set MS_GRAPH_CLIENT_ID and MS_GRAPH_CLIENT_SECRET in .env")

        token = await self._get_access_token()
        share_token = _encode_share_url(share_url)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{self.GRAPH_BASE}/shares/{share_token}/driveItem/children",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

        items = []
        for item_data in response.json().get("value", []):
            items.append(OneDriveItem(
                name=item_data.get("name", ""),
                path=item_data.get("parentReference", {}).get("path", "") + "/" + item_data.get("name", ""),
                is_folder="folder" in item_data,
                size=item_data.get("size", 0),
                child_count=item_data.get("folder", {}).get("childCount", 0) if "folder" in item_data else 0,
                download_url=item_data.get("@microsoft.graph.downloadUrl"),
                item_id=item_data.get("id"),
                modified_at=item_data.get("lastModifiedDateTime"),
            ))
        return items

    async def list_subfolder(self, share_url: str, item_id: str) -> list[OneDriveItem]:
        """List children of a subfolder within a shared folder."""
        if not self.is_configured:
            raise RuntimeError("OneDrive is not configured.")

        token = await self._get_access_token()
        share_token = _encode_share_url(share_url)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{self.GRAPH_BASE}/shares/{share_token}/items/{item_id}/children",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

        items = []
        for item_data in response.json().get("value", []):
            items.append(OneDriveItem(
                name=item_data.get("name", ""),
                path=item_data.get("parentReference", {}).get("path", "") + "/" + item_data.get("name", ""),
                is_folder="folder" in item_data,
                size=item_data.get("size", 0),
                child_count=item_data.get("folder", {}).get("childCount", 0) if "folder" in item_data else 0,
                download_url=item_data.get("@microsoft.graph.downloadUrl"),
                item_id=item_data.get("id"),
                modified_at=item_data.get("lastModifiedDateTime"),
            ))
        return items

    async def download_file(self, share_url: str, item_id: str, save_path: str) -> str:
        """Download a file from a shared folder to a local path."""
        if not self.is_configured:
            raise RuntimeError("OneDrive is not configured.")

        token = await self._get_access_token()
        share_token = _encode_share_url(share_url)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Get the download URL
            response = await client.get(
                f"{self.GRAPH_BASE}/shares/{share_token}/items/{item_id}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            download_url = response.json().get("@microsoft.graph.downloadUrl")

            if not download_url:
                raise RuntimeError(f"No download URL for item {item_id}")

            # Download the file
            file_response = await client.get(download_url, timeout=120)
            file_response.raise_for_status()

            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(file_response.content)

            return save_path

    async def crawl_shared_folder(
        self, share_url: str, extensions: list[str] | None = None
    ) -> list[OneDriveItem]:
        """Recursively crawl a shared folder and return all matching files.
        
        Args:
            share_url: The OneDrive share URL
            extensions: File extensions to include (e.g., ['.pptx', '.docx']). None = all files.
        """
        all_files: list[OneDriveItem] = []
        
        async def _crawl(items: list[OneDriveItem]):
            for item in items:
                if item.is_folder:
                    if item.item_id:
                        sub_items = await self.list_subfolder(share_url, item.item_id)
                        await _crawl(sub_items)
                else:
                    if extensions is None or any(item.name.lower().endswith(ext) for ext in extensions):
                        all_files.append(item)

        root_items = await self.list_shared_folder(share_url)
        await _crawl(root_items)
        return all_files


class LocalLibraryService:
    """Index PPTX files from the local library/ folder.
    
    This is the fallback when OneDrive credentials aren't configured.
    Users can manually download files from OneDrive and place them here.
    
    Folder structure:
        library/
            modules/          <- Current lesson modules (PPTX)
            reference/        <- Old workshop content for reference
    """

    def __init__(self, library_path: str = "./library"):
        self.library_path = Path(library_path)

    def list_all_files(self, extensions: list[str] | None = None) -> list[OneDriveItem]:
        """List all files in the library folder recursively."""
        if extensions is None:
            extensions = [".pptx", ".ppt", ".docx", ".pdf"]

        files = []
        if not self.library_path.exists():
            return files

        for ext in extensions:
            for filepath in self.library_path.rglob(f"*{ext}"):
                stat = filepath.stat()
                files.append(OneDriveItem(
                    name=filepath.name,
                    path=str(filepath.relative_to(self.library_path)),
                    is_folder=False,
                    size=stat.st_size,
                    download_url=None,  # Local file, no download URL
                    item_id=str(filepath),
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                ))
        return files

    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """Get the absolute path to a file in the library."""
        full_path = self.library_path / relative_path
        if full_path.exists():
            return full_path
        return None

    def get_status(self) -> dict:
        """Get a summary of the local library."""
        files = self.list_all_files()
        by_folder: dict[str, int] = {}
        for f in files:
            folder = str(Path(f.path).parent)
            by_folder[folder] = by_folder.get(folder, 0) + 1

        return {
            "total_files": len(files),
            "by_folder": by_folder,
            "library_path": str(self.library_path.resolve()),
            "exists": self.library_path.exists(),
        }


# Singletons
onedrive_service = OneDriveService()
local_library = LocalLibraryService()
