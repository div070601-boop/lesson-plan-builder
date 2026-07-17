"""
Admin Router — System administration endpoints.
For indexer control, re-analysis triggers, provider diagnostics, and system stats.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import asyncio
from datetime import datetime

from services.providers import provider_service, ProviderError
from services.onedrive import onedrive_service, local_library
from services.generation import _generations
from config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Global indexing progress state
# ---------------------------------------------------------------------------
_index_progress = {
    "status": "idle",        # idle | crawling | downloading | analyzing | done | error
    "total_remote": 0,       # Total files found on OneDrive
    "crawled": 0,            # Files discovered during crawl
    "downloaded": 0,         # Files downloaded (new or changed)
    "analyzed": 0,           # Files analyzed via deck_analyzer
    "cached_hits": 0,        # Files skipped (unchanged in cache)
    "current_file": "",      # Currently processing file name
    "started_at": None,
    "finished_at": None,
    "errors": [],
}


def _reset_progress():
    _index_progress.update({
        "status": "idle",
        "total_remote": 0,
        "crawled": 0,
        "downloaded": 0,
        "analyzed": 0,
        "cached_hits": 0,
        "current_file": "",
        "started_at": None,
        "finished_at": None,
        "errors": [],
    })


async def _background_full_reindex(share_urls):
    """Background task: crawl OneDrive, download new files, analyze with deck_analyzer, cache to Supabase."""
    import logging
    import traceback
    from pathlib import Path

    logger = logging.getLogger(__name__)
    _index_progress["status"] = "crawling"
    _index_progress["started_at"] = datetime.now().isoformat()
    _index_progress["finished_at"] = None
    _index_progress["errors"] = []

    try:
        # Get cached file hashes for change detection
        from services.library import get_cached_file_hashes, upsert_deck_to_cache
        from services.deck_analyzer import analyze_pptx, compute_file_hash
        cached_hashes = get_cached_file_hashes()

        # Phase 1: Crawl all share URLs to discover files
        all_files = []
        for share_url in share_urls:
            try:
                files = await onedrive_service.crawl_shared_folder(
                    share_url,
                    extensions=[".pptx", ".ppt", ".docx"],
                )
                all_files.extend(files)
                _index_progress["crawled"] = len(all_files)
            except Exception as e:
                logger.warning(f"Crawl error for {share_url}: {e}")
                _index_progress["errors"].append(f"Crawl: {str(e)[:200]}")

        _index_progress["total_remote"] = len(all_files)
        _index_progress["status"] = "downloading"
        logger.info(f"Crawl complete: {len(all_files)} files found across {len(share_urls)} share URLs")

        # Phase 2: Download new/changed files + analyze
        dl_sem = asyncio.Semaphore(2)

        async def _process_file(item, share_url):
            async with dl_sem:
                fname = item.name
                _index_progress["current_file"] = fname

                # Check if file is unchanged in cache
                old_hash = cached_hashes.get(fname, "")
                save_path = f"./library/{fname}"

                # Download the file
                try:
                    if not item.item_id:
                        _index_progress["cached_hits"] += 1
                        return
                    
                    # If file exists and we have a cached hash, check if unchanged
                    if old_hash and Path(save_path).exists():
                        current_hash = compute_file_hash(save_path)
                        if current_hash == old_hash:
                            _index_progress["cached_hits"] += 1
                            logger.debug(f"Cache hit (unchanged): {fname}")
                            return

                    await onedrive_service.download_file(share_url, item.item_id, save_path)
                    _index_progress["downloaded"] += 1
                    logger.info(f"Downloaded: {fname}")
                except Exception as e:
                    logger.warning(f"Download failed for {fname}: {e}")
                    _index_progress["errors"].append(f"Download {fname}: {str(e)[:100]}")
                    return

                # Analyze the downloaded file
                _index_progress["status"] = "analyzing"
                try:
                    if fname.lower().endswith((".pptx", ".ppt")):
                        deck = analyze_pptx(save_path, onedrive_path=item.path or fname)
                        if deck:
                            upsert_deck_to_cache(deck)
                            _index_progress["analyzed"] += 1
                            logger.info(f"Analyzed: {fname} ({deck.slide_count} slides)")
                except Exception as e:
                    logger.warning(f"Analysis failed for {fname}: {e}")
                    _index_progress["errors"].append(f"Analyze {fname}: {str(e)[:100]}")

        # Process all files
        for share_url in share_urls:
            files_for_url = [f for f in all_files if not f.is_folder]
            tasks = [_process_file(f, share_url) for f in files_for_url]
            await asyncio.gather(*tasks, return_exceptions=True)

        _index_progress["status"] = "done"
        _index_progress["finished_at"] = datetime.now().isoformat()
        _index_progress["current_file"] = ""
        logger.info(
            f"Re-index complete: {_index_progress['downloaded']} downloaded, "
            f"{_index_progress['cached_hits']} cached, "
            f"{_index_progress['analyzed']} analyzed, "
            f"{len(_index_progress['errors'])} errors"
        )

    except Exception as e:
        _index_progress["status"] = "error"
        _index_progress["errors"].append(f"Fatal: {str(e)[:300]}")
        _index_progress["finished_at"] = datetime.now().isoformat()
        logger.error(f"Background re-index fatal error: {type(e).__name__}: {e}\n{traceback.format_exc()}")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@router.get("/auth/onedrive/login")
async def onedrive_login(request: Request):
    """Initiate Microsoft Graph OAuth flow."""
    redirect_uri = str(request.base_url) + "api/admin/auth/onedrive/callback"
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
        return RedirectResponse(url=f"{settings.frontend_url}/admin?onedrive=connected")
    except Exception as e:
        return RedirectResponse(url=f"{settings.frontend_url}/admin?onedrive=error&msg={str(e)}")


class TestProviderRequest(BaseModel):
    prompt: str = "Respond with: Hello from Lesson Plan Builder!"


# ---------------------------------------------------------------------------
# Indexing endpoints
# ---------------------------------------------------------------------------
@router.post("/reindex")
async def trigger_reindex():
    """Trigger a re-index. Uses Graph API if configured, otherwise scans local library/ folder."""
    if onedrive_service.is_configured and settings.onedrive_share_urls:
        if _index_progress["status"] in ("crawling", "downloading", "analyzing"):
            return {
                "status": "already_running",
                "source": "onedrive",
                "message": "⏳ Re-index is already running. Check progress below.",
                "progress": _index_progress,
            }
        _reset_progress()
        asyncio.create_task(_background_full_reindex(settings.onedrive_share_urls))
        lib_status = local_library.get_status()
        current_files = lib_status["total_files"]
        return {
            "status": "ok",
            "source": "onedrive",
            "files_found": current_files,
            "files_downloaded": current_files,
            "message": f"✅ OneDrive re-indexing started! {current_files} decks currently cached. Scanning for new/changed files...",
            "files": [],
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


@router.get("/index-progress")
async def get_index_progress():
    """Get live indexing progress. Polled by frontend during re-index."""
    return _index_progress


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
@router.get("/debug-crawl")
async def debug_crawl():
    """Debug endpoint: run crawl_shared_folder and test download of the first presentation deck."""
    import traceback
    from pathlib import Path
    result = {}
    try:
        if not settings.onedrive_share_urls:
            return {"error": "No share URLs configured"}
        share_url = settings.onedrive_share_urls[0]
        files = await onedrive_service.crawl_shared_folder(share_url, extensions=[".pptx", ".ppt", ".docx"], max_depth=2)
        result["crawl_status"] = "ok"
        result["files_found"] = len(files)
        result["files"] = [f.to_dict() for f in files[:20]]
        if files and files[0].item_id:
            first_file = files[0]
            save_path = f"./library/{first_file.name}"
            result["test_download_start"] = save_path
            dl_res = await onedrive_service.download_file(share_url, first_file.item_id, save_path)
            result["test_download_path"] = dl_res
            result["test_download_exists"] = Path(save_path).exists() if save_path else False
            result["test_download_size"] = Path(save_path).stat().st_size if Path(save_path).exists() else 0
            result["local_library_status"] = local_library.get_status()
    except Exception as e:
        result["crawl_status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["traceback"] = traceback.format_exc()
    return result


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

    if supabase:
        try:
            res = supabase.table("settings").select("key").execute()
            result["supabase_settings_keys"] = [r["key"] for r in res.data] if res.data else []
            result["supabase_settings_table_ok"] = True
        except Exception as e:
            result["supabase_settings_table_ok"] = False
            result["supabase_settings_error"] = f"{type(e).__name__}: {str(e)}"

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

        if settings.onedrive_share_urls:
            try:
                items = await onedrive_service.list_shared_folder(settings.onedrive_share_urls[0])
                result["list_shared_folder_ok"] = True
                result["items_found"] = len(items)
                result["items"] = [i.to_dict() for i in items[:10]]
            except Exception as e:
                result["list_shared_folder_ok"] = False
                result["list_error"] = f"{type(e).__name__}: {str(e)}"
                result["list_traceback"] = traceback.format_exc()

    return result


@router.post("/restart")
async def restart_server():
    """Restart the server process."""
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


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
@router.get("/stats")
async def get_stats():
    """Get system statistics: indexed decks, generations, provider usage."""
    from services.library import _deck_cache
    lib_status = local_library.get_status()
    return {
        "total_decks": max(len(_deck_cache), lib_status["total_files"]),
        "total_generations": len(_generations),
        "total_users": 0,
        "indexer_status": "onedrive" if onedrive_service.is_configured else "local",
        "index_progress": _index_progress,
        "library": lib_status,
        "last_index_run": _index_progress.get("finished_at"),
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
