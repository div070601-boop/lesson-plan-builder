"""
Admin Router — System administration endpoints.
For indexer control, re-analysis triggers, provider diagnostics, and system stats.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services.providers import provider_service, ProviderError
from services.onedrive import onedrive_service, local_library
from services.generation import _generations
from config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/auth/onedrive/login")
async def onedrive_login(request: Request):
    """Initiate Microsoft Graph OAuth flow."""
    redirect_uri = str(request.base_url) + "api/admin/auth/onedrive/callback"
    # Ensure scheme is http if running locally
    if redirect_uri.startswith("http://127.0.0.1"):
        redirect_uri = redirect_uri.replace("127.0.0.1", "localhost")
    try:
        auth_url = onedrive_service.get_auth_url(redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/onedrive/callback")
async def onedrive_callback(request: Request):
    """Handle Microsoft Graph OAuth redirect."""
    redirect_uri = str(request.base_url) + "api/admin/auth/onedrive/callback"
    if redirect_uri.startswith("http://127.0.0.1"):
        redirect_uri = redirect_uri.replace("127.0.0.1", "localhost")
        
    query_params = dict(request.query_params)
    try:
        onedrive_service.acquire_token_by_auth_code(query_params, redirect_uri)
        # Redirect back to frontend admin panel
        return RedirectResponse(url=f"{settings.frontend_url}/admin?onedrive=connected")
    except Exception as e:
        return RedirectResponse(url=f"{settings.frontend_url}/admin?onedrive=error&msg={str(e)}")



class TestProviderRequest(BaseModel):
    prompt: str = "Respond with: Hello from Lesson Plan Builder!"


@router.post("/reindex")
async def trigger_reindex():
    """Trigger a re-index. Uses Graph API if configured, otherwise scans local library/ folder."""
    # Check if OneDrive Graph API is configured
    if onedrive_service.is_configured and settings.onedrive_share_urls:
        try:
            all_files = []
            for share_url in settings.onedrive_share_urls:
                files = await onedrive_service.crawl_shared_folder(
                    share_url, extensions=[".pptx", ".ppt", ".docx"]
                )
                all_files.extend(files)

            # Download files to local library
            downloaded = 0
            for f in all_files:
                if f.item_id and f.download_url:
                    save_path = f"./library/{f.name}"
                    await onedrive_service.download_file(
                        settings.onedrive_share_urls[0], f.item_id, save_path
                    )
                    downloaded += 1

            return {
                "status": "ok",
                "source": "onedrive",
                "files_found": len(all_files),
                "files_downloaded": downloaded,
                "files": [f.to_dict() for f in all_files],
            }
        except Exception as e:
            import logging, traceback
            logger = logging.getLogger(__name__)
            logger.error(f"OneDrive crawl failed during reindex: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            # Graceful fallback: return local files with a warning message so UI doesn't break
            local_files = local_library.list_all_files()
            return {
                "status": "ok",
                "source": "local_fallback",
                "message": f"Indexed local library ({len(local_files)} files). Note: OneDrive crawl encountered: {type(e).__name__}: {str(e)}",
                "files_found": len(local_files),
                "files": [f.to_dict() for f in local_files],
            }
    else:
        # Scan local library/ folder
        local_files = local_library.list_all_files()
        return {
            "status": "ok",
            "source": "local",
            "message": "Scanned local library/ folder. To enable OneDrive sync, add MS_GRAPH_CLIENT_ID and MS_GRAPH_CLIENT_SECRET to .env",
            "files_found": len(local_files),
            "files": [f.to_dict() for f in local_files],
        }


@router.get("/debug-onedrive")
async def debug_onedrive():
    """Debug endpoint: step-by-step check of OneDrive connectivity."""
    import traceback
    from services.database import supabase

    result = {
        "client_id_set": bool(settings.ms_graph_client_id),
        "client_secret_set": bool(settings.ms_graph_client_secret),
        "is_configured": onedrive_service.is_configured,
        "has_active_session": onedrive_service.has_active_session,
        "share_urls": settings.onedrive_share_urls,
        "share_urls_count": len(settings.onedrive_share_urls),
        "supabase_connected": supabase is not None,
    }

    # Check Supabase settings table
    if supabase:
        try:
            res = supabase.table("settings").select("key").execute()
            result["supabase_settings_keys"] = [r["key"] for r in res.data] if res.data else []
            result["supabase_settings_table_ok"] = True
        except Exception as e:
            result["supabase_settings_table_ok"] = False
            result["supabase_settings_error"] = f"{type(e).__name__}: {str(e)}"

    # Step 1: Try to acquire access token
    if onedrive_service.is_configured:
        try:
            token = await onedrive_service._get_access_token()
            result["token_acquired"] = True
            result["token_preview"] = token[:20] + "..." if token else None
        except Exception as e:
            result["token_acquired"] = False
            result["token_error"] = f"{type(e).__name__}: {str(e)}"
            result["token_traceback"] = traceback.format_exc()
            return result

        # Step 2: Try to list shared folder
        if settings.onedrive_share_urls:
            try:
                items = await onedrive_service.list_shared_folder(settings.onedrive_share_urls[0])
                result["list_shared_folder_ok"] = True
                result["items_found"] = len(items)
                result["items"] = [i.to_dict() for i in items[:10]]  # First 10 items

                if items and items[0].item_id:
                    import httpx
                    from services.onedrive import _encode_share_url
                    share_token = _encode_share_url(settings.onedrive_share_urls[0])
                    item_id = items[0].item_id
                    drive_id = item_id.split("!")[0]
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        # Test Option A: shares/.../driveItem/items/.../children
                        try:
                            rA = await client.get(
                                f"https://graph.microsoft.com/v1.0/shares/{share_token}/driveItem/items/{item_id}/children",
                                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                                timeout=15
                            )
                            result["subfolder_test_A_status"] = rA.status_code
                            if rA.status_code == 200:
                                result["subfolder_test_A_count"] = len(rA.json().get("value", []))
                        except Exception as e:
                            result["subfolder_test_A_error"] = str(e)

                        # Test Option B: drives/.../items/.../children
                        try:
                            rB = await client.get(
                                f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children",
                                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                                timeout=15
                            )
                            result["subfolder_test_B_status"] = rB.status_code
                            if rB.status_code == 200:
                                result["subfolder_test_B_count"] = len(rB.json().get("value", []))
                        except Exception as e:
                            result["subfolder_test_B_error"] = str(e)

            except Exception as e:
                result["list_shared_folder_ok"] = False
                result["list_error"] = f"{type(e).__name__}: {str(e)}"
                result["list_traceback"] = traceback.format_exc()

    return result


@router.post("/restart")
async def restart_server():
    """Restart the server process (causes Render or Docker container to reboot cleanly)."""
    import os, threading, time
    def _do_restart():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_do_restart, daemon=True).start()
    return {"status": "ok", "message": "Server restarting cleanly in 1 second..."}


@router.post("/reanalyze/{deck_id}")
async def trigger_reanalysis(deck_id: str):
    """Trigger re-analysis of a specific deck."""
    return {"status": "not_configured", "message": "AI analysis not yet configured"}


@router.post("/reanalyze-all")
async def trigger_full_reanalysis():
    """Trigger re-analysis of the full library."""
    return {"status": "not_configured", "message": "AI analysis not yet configured"}


@router.get("/stats")
async def get_stats():
    """Get system statistics: indexed decks, generations, provider usage."""
    lib_status = local_library.get_status()
    return {
        "total_decks": lib_status["total_files"],
        "total_generations": len(_generations),
        "total_users": 0,
        "indexer_status": "onedrive" if onedrive_service.is_configured else "local",
        "library": lib_status,
        "last_index_run": None,
    }


@router.get("/provider-status")
async def get_provider_status():
    """Get the configuration status of each AI provider."""
    status = provider_service.get_status()
    status["onedrive"] = "configured" if onedrive_service.is_configured else "unconfigured"
    return status


@router.get("/library-status")
async def get_library_status():
    """Get detailed status of the deck library."""
    return {
        "onedrive_configured": onedrive_service.is_configured,
        "share_urls": len(settings.onedrive_share_urls),
        "local_library": local_library.get_status(),
    }


@router.post("/test-provider")
async def test_provider(request: TestProviderRequest):
    """Send a test prompt to the first available AI provider."""
    try:
        response, model = await provider_service.complete(
            prompt=request.prompt,
            system="You are a helpful test assistant. Respond briefly.",
            task_type="analysis",
        )
        return {"status": "ok", "model": model, "response": response.strip()[:500]}
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))
