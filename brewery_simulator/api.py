"""
brewery_simulator/api.py

FastAPI control plane — runs in the same asyncio event loop as the simulator.
All state mutations go through the BreweryEngine instance (shared object, no locks needed
because asyncio is single-threaded).

Endpoints:
  POST /auth/token     → exchange API key for Bearer JWT token
  GET  /               → redirect to /docs
  GET  /status         → full runtime status
  POST /speed/{value}  → change speed multiplier live  [requires Bearer token]
  POST /pause          → pause simulation              [requires Bearer token]
  POST /resume         → resume simulation             [requires Bearer token]
  GET  /tags           → all tags with current values
  GET  /tags/{name}    → single tag
  POST /tags/{name}    → override a tag value manually [requires Bearer token]
  POST /fault/{tag}    → inject a fault                [requires Bearer token]
  POST /fault/{tag}/clear → clear a fault              [requires Bearer token]
  GET  /areas          → list areas and their tag counts

Authentication flow:
  1. POST /auth/token  with body { "api_key": "your-secret" }
  2. Copy the returned access_token
  3. Click Authorize 🔒 in Swagger UI and paste: Bearer <access_token>
  4. All protected POST endpoints are now unlocked
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Path, Security, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("BREWERY_API_KEY")
if not API_KEY:
    raise RuntimeError("BREWERY_API_KEY environment variable is not set")

JWT_SECRET = os.getenv("BREWERY_JWT_SECRET", API_KEY + "_jwt_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

# ── JWT helpers ───────────────────────────────────────────────────────────────
try:
    from jose import JWTError, jwt as jose_jwt

    def create_token() -> str:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        return jose_jwt.encode(
            {"sub": "brewery-sim", "exp": expire},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

    def decode_token(token: str) -> bool:
        try:
            jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return True
        except JWTError:
            return False

except ImportError:
    # Fallback: simple signed token without python-jose
    import hmac
    import hashlib
    import base64
    import json

    def create_token() -> str:
        expire = int(time.time()) + JWT_EXPIRE_MINUTES * 60
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "brewery-sim", "exp": expire}).encode()
        ).decode()
        sig = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{sig}"

    def decode_token(token: str) -> bool:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return False
            payload_b64, sig = parts
            expected_sig = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return False
            payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
            return payload.get("exp", 0) > time.time()
        except Exception:
            return False


# ── Security scheme (shows Authorize 🔒 button in Swagger) ───────────────────
bearer_scheme = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    if not decode_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Models ────────────────────────────────────────────────────────────────────
class ApiKeyRequest(BaseModel):
    api_key: str


class TagValue(BaseModel):
    value: float | bool | int


# Engine is injected at startup — see engine.py
_engine = None


def create_app(engine) -> FastAPI:
    global _engine
    _engine = engine

    app = FastAPI(
        title="🍺 Brewery Simulator",
        description=(
            "Live control plane for the Industrial Brewery PLC Simulator.\n\n"
            "### Authentication\n\n"
            "1. Use **POST /auth/token** with your `api_key` to get a Bearer token\n"
            "2. Click **Authorize 🔒** and enter: `Bearer <your_token>`\n"
            "3. Protected POST endpoints are now unlocked\n\n"
            "GET endpoints are public and require no authentication."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Auth ──────────────────────────────────────────────────────────────────

    @app.post("/auth/token", tags=["Auth"], summary="Exchange API key for Bearer token")
    async def get_token(body: ApiKeyRequest):
        if body.api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        token = create_token()
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in_minutes": JWT_EXPIRE_MINUTES,
        }

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @app.get("/status", tags=["Control"], summary="Runtime status")
    async def status():
        e = _engine
        dt_sim = e.cfg.sim.tick_interval * e.speed
        sim_hours = e._tick_count * dt_sim / 3600
        uptime_s = time.monotonic() - e._started_at

        return {
            "running":     not e.paused,
            "speed":       e.speed,
            "tick_count":  e._tick_count,
            "sim_time_h":  round(sim_hours, 2),
            "uptime_s":    round(uptime_s, 1),
            "mqtt_broker": f"{e.cfg.mqtt.host}:{e.cfg.mqtt.port}",
            "total_tags":  len(e.store.all_tags()),
            "areas":       [a.__class__.__name__ for a in e._areas],
        }

    @app.post(
        "/speed/{value}",
        tags=["Control"],
        summary="Change simulation speed",
        dependencies=[Depends(verify_token)],
    )
    async def set_speed(
        value: float = Path(..., ge=0.1, le=86400, description="Speed multiplier (1=realtime, 3600=turbo)")
    ):
        _engine.speed = value
        return {"speed": value, "message": f"Speed set to {value}x"}

    @app.post(
        "/pause",
        tags=["Control"],
        summary="Pause simulation",
        dependencies=[Depends(verify_token)],
    )
    async def pause():
        if _engine.paused:
            return {"paused": True, "message": "Already paused"}
        _engine.paused = True
        return {"paused": True, "message": "Simulation paused"}

    @app.post(
        "/resume",
        tags=["Control"],
        summary="Resume simulation",
        dependencies=[Depends(verify_token)],
    )
    async def resume():
        if not _engine.paused:
            return {"paused": False, "message": "Already running"}
        _engine.paused = False
        return {"paused": False, "message": "Simulation resumed"}

    @app.get("/tags", tags=["Tags"], summary="All tags with current values")
    async def get_tags(
        area: str | None = None,
        io_type: str | None = None,
        equipment: str | None = None,
    ):
        result = {}
        for name, state in _engine.store.all_tags().items():
            if area and state.meta.area != area:
                continue
            if io_type and state.meta.io_type != io_type.upper():
                continue
            if equipment and state.meta.equipment != equipment:
                continue
            result[name] = {
                "value":       state.value,
                "unit":        state.meta.unit,
                "io_type":     state.meta.io_type,
                "area":        state.meta.area,
                "equipment":   state.meta.equipment,
                "description": state.meta.description,
            }
        return result

    @app.get("/tags/{name}", tags=["Tags"], summary="Single tag value")
    async def get_tag(name: str):
        tags = _engine.store.all_tags()
        if name not in tags:
            raise HTTPException(status_code=404, detail=f"Tag '{name}' not found")
        state = tags[name]
        return {
            "tag":         name,
            "value":       state.value,
            "unit":        state.meta.unit,
            "io_type":     state.meta.io_type,
            "area":        state.meta.area,
            "equipment":   state.meta.equipment,
            "description": state.meta.description,
            "min":         state.meta.min_val,
            "max":         state.meta.max_val,
        }

    @app.post(
        "/tags/{name}",
        tags=["Tags"],
        summary="Override a tag value",
        dependencies=[Depends(verify_token)],
    )
    async def set_tag(name: str, body: TagValue):
        tags = _engine.store.all_tags()
        if name not in tags:
            raise HTTPException(status_code=404, detail=f"Tag '{name}' not found")
        try:
            _engine.store.set(name, body.value)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"tag": name, "value": _engine.store.get(name), "message": "Value overridden"}

    @app.post(
        "/fault/{tag}",
        tags=["Faults"],
        summary="Inject a fault",
        dependencies=[Depends(verify_token)],
    )
    async def inject_fault(tag: str):
        tags = _engine.store.all_tags()
        if tag not in tags:
            candidates = [
                t for t in tags
                if ("FAULT" in t or "FLT" in t) and tags[t].meta.equipment.lower() == tag.lower()
            ]
            if candidates:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tag '{tag}' not found. Did you mean one of: {candidates}"
                )
            raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")

        state = tags[tag]
        if state.meta.io_type not in ("DI", "DO"):
            raise HTTPException(
                status_code=400,
                detail=f"'{tag}' is not a DI/DO tag (it's {state.meta.io_type})"
            )

        _engine.store.set(tag, True)
        return {"tag": tag, "value": True, "message": "Fault injected"}

    @app.post(
        "/fault/{tag}/clear",
        tags=["Faults"],
        summary="Clear a fault",
        dependencies=[Depends(verify_token)],
    )
    async def clear_fault(tag: str):
        tags = _engine.store.all_tags()
        if tag not in tags:
            raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")
        _engine.store.set(tag, False)
        return {"tag": tag, "value": False, "message": "Fault cleared"}

    @app.get("/faults", tags=["Faults"], summary="List all active faults")
    async def list_faults():
        faults = {
            name: {
                "equipment":   state.meta.equipment,
                "area":        state.meta.area,
                "description": state.meta.description,
            }
            for name, state in _engine.store.all_tags().items()
            if ("FAULT" in name or "FLT" in name)
            and state.meta.io_type in ("DI", "DO")
            and state.value
        }
        return {"active_faults": len(faults), "faults": faults}

    @app.get("/areas", tags=["Tags"], summary="Areas and tag counts")
    async def list_areas():
        areas: dict[str, Any] = {}
        for name, state in _engine.store.all_tags().items():
            a = state.meta.area
            if a not in areas:
                areas[a] = {"total": 0, "DI": 0, "DO": 0, "AI": 0, "AO": 0}
            areas[a]["total"] += 1
            areas[a][state.meta.io_type] = areas[a].get(state.meta.io_type, 0) + 1
        return areas

    return app