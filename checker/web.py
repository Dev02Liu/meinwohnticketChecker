"""Web UI (setup wizard + dashboard) and the small JSON API behind it."""
from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Any, Mapping

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import PERSISTED_FIELDS, SECRET_FIELDS, Settings, is_search_url
from .filters import FILTER_CATALOG, describe_search
from .service import Service

log = logging.getLogger(__name__)
TEMPLATES_DIR = Path(__file__).parent / "templates"


def apply_payload(current: Settings, payload: Mapping[str, Any]) -> Settings:
    """Merge a settings form submission into the current settings.

    Blank secret fields mean "keep the stored value"; ``clear_<field>: true`` removes it.
    """
    changes: dict[str, Any] = {}
    for name in PERSISTED_FIELDS:
        if name not in payload:
            continue
        value = payload[name]
        if name in SECRET_FIELDS and (value is None or str(value).strip() == ""):
            if payload.get(f"clear_{name}"):
                changes[name] = None
            continue
        changes[name] = value
    return current.with_updates(**changes)


def create_app(service: Service) -> FastAPI:
    app = FastAPI(
        title="Mein Wohn-Ticket Checker",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    basic = HTTPBasic(auto_error=False)

    def require_auth(credentials: HTTPBasicCredentials | None = Depends(basic)) -> None:
        expected = service.settings.ui_password
        if not expected:
            return
        given = credentials.password if credentials else ""
        if not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
            raise HTTPException(
                status_code=401,
                detail="Login required",
                headers={"WWW-Authenticate": 'Basic realm="Wohn-Ticket Checker"'},
            )

    def require_fetch(request: Request) -> None:
        # Cross-site forms cannot set custom headers, so this blocks CSRF on state-changing calls.
        if request.headers.get("x-requested-with") != "fetch":
            raise HTTPException(status_code=403, detail="Missing 'X-Requested-With: fetch' header")

    page_deps = [Depends(require_auth)]
    api_deps = [Depends(require_auth), Depends(require_fetch)]

    def render(request: Request, name: str, **context: Any) -> HTMLResponse:
        context.update(
            version=__version__,
            configured=service.settings.is_configured,
            ui_password_set=bool(service.settings.ui_password),
        )
        return templates.TemplateResponse(request, name, context)

    # -- pages --------------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse, dependencies=page_deps)
    def dashboard(request: Request) -> Any:
        if not service.settings.is_configured:
            return RedirectResponse("/settings", status_code=303)
        return render(request, "dashboard.html", status=service.status())

    @app.get("/settings", response_class=HTMLResponse, dependencies=page_deps)
    def settings_page(request: Request) -> Any:
        return render(
            request,
            "settings.html",
            settings=service.settings.public_dict(),
            setup=not service.settings.is_configured,
            filter_catalog=FILTER_CATALOG,
        )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True, "version": __version__}

    # -- api ------------------------------------------------------------------------------
    @app.get("/api/status", dependencies=page_deps)
    def api_status() -> dict[str, Any]:
        return service.status()

    @app.post("/api/settings", dependencies=api_deps)
    def api_save_settings(payload: dict[str, Any] = Body(...)) -> Any:
        try:
            new_settings = apply_payload(service.settings, payload)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "errors": [str(exc)]}, status_code=400)
        errors = new_settings.validate()
        if errors:
            return JSONResponse({"ok": False, "errors": errors}, status_code=400)
        service.update_settings(new_settings)
        return {"ok": True}

    @app.post("/api/test/login", dependencies=api_deps)
    def api_test_login(payload: dict[str, Any] = Body(...)) -> Any:
        username = str(payload.get("username") or service.settings.username or "").strip()
        password = str(payload.get("password") or service.settings.password or "")
        if not username or not password:
            return JSONResponse({"ok": False, "error": "Username and password are required."}, status_code=400)
        try:
            state = service.test_login(username, password)
        except Exception as exc:  # noqa: BLE001 - report any failure to the UI
            log.warning("Login test failed: %s", exc)
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
        return {"ok": True, "state": state}

    @app.post("/api/test/search", dependencies=api_deps)
    def api_test_search(payload: dict[str, Any] = Body(...)) -> Any:
        url = str(payload.get("search_url") or "").strip()
        if not is_search_url(url):
            return JSONResponse(
                {"ok": False, "error": "Please paste a https://www.meinwohnticket.wien/wohnungen?... URL."},
                status_code=400,
            )
        try:
            total, hits = service.test_search(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("Search test failed: %s", exc)
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
        return {
            "ok": True,
            "total": total,
            "summary": describe_search(url),
            "listings": [Service._listing_view(hit) for hit in hits[:10]],
        }

    @app.post("/api/test/notification", dependencies=api_deps)
    def api_test_notification(payload: dict[str, Any] = Body(...)) -> Any:
        try:
            candidate = apply_payload(service.settings, payload)
            sent = service.test_notification(candidate)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        if not sent:
            return JSONResponse(
                {"ok": False, "error": "Sending failed. Check the values and the container log."}, status_code=502
            )
        return {"ok": True, "channels": candidate.channels}

    @app.post("/api/check", dependencies=api_deps)
    def api_check() -> Any:
        if not service.settings.is_configured:
            return JSONResponse({"ok": False, "error": "Finish the setup first."}, status_code=400)
        service.trigger_check()
        return {"ok": True}

    return app
