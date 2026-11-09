"""Provider-neutral HTTP boundary; identity and model transports are explicit adapters."""
import asyncio
import json
import threading
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from structured_output import _object

class PolicyUnverified(Exception):
    pass

class AccessDenied(Exception):
    pass

def create_app(config, verify, infer, public_config, static_root=None, token_header=None, protect_assets=False, require_origin=False):
    root = Path(static_root or Path(__file__).parent / "web")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Small internal apps admit a burst of five model requests per process.
    # Capacity is bounded; excess callers receive a retryable 429, never a hidden
    # unbounded queue. Destination quota/latency still needs real qualification.
    slots = threading.BoundedSemaphore(5)

    @app.middleware("http")
    async def headers(request, next_handler):
        denied = False
        if protect_assets and request.url.path != "/healthz":
            try:
                await run_in_threadpool(verify, request.headers.get(token_header, ""))
            except Exception:
                denied = True
        response = JSONResponse({"error": "access_denied"}, status_code=401) if denied else await next_handler(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                                 "Content-Security-Policy": config.get("csp", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"), "Strict-Transport-Security": "max-age=31536000"})
        return response

    @app.get("/healthz")
    def health():
        # Startup liveness, not proof that identity/model/account policy is ready.
        return {"status": "running"}

    @app.get("/config.json")
    def get_public_config():
        return public_config()


    @app.get("/")
    def index():
        return FileResponse(root / "index.html")

    @app.get("/app.js")
    def script():
        return FileResponse(root / "app.js", media_type="text/javascript")

    @app.get("/app.css")
    def style():
        return FileResponse(root / "app.css", media_type="text/css")

    @app.post("/api/ask")
    async def ask(request: Request):
        origin = request.headers.get("origin")
        if (require_origin and not origin) or (origin and origin != config["PUBLIC_ORIGIN"]):
            return JSONResponse({"error": "access_denied"}, status_code=403)
        auth = request.headers.get("authorization", "")
        token = request.headers.get(token_header, "") if token_header else auth[7:] if auth.startswith("Bearer ") else ""
        try:
            await run_in_threadpool(verify, token)
        except Exception:
            return JSONResponse({"error": "access_denied"}, status_code=401)
        if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            return JSONResponse({"error": "invalid_request"}, status_code=400)
        if not slots.acquire(blocking=False):
            return JSONResponse({"error": "busy"}, status_code=429)
        try:
            raw = bytearray()
            async with asyncio.timeout(5):
                async for chunk in request.stream():
                    raw.extend(chunk)
                    if len(raw) > config["max_input"] * 6 + 100:
                        return JSONResponse({"error": "input_too_large"}, status_code=413)
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
            text = body.get("text") if isinstance(body, dict) and set(body) == {"text"} else None
            if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > config["max_input"]:
                return JSONResponse({"error": "invalid_request"}, status_code=400)
            try:
                result = await run_in_threadpool(infer, text)
            except (ValueError, UnicodeError, RecursionError):
                return JSONResponse({"error": "invalid_model_output"}, status_code=503)
            # Never return an inference result after expiry, or if injected verification fails.
            await run_in_threadpool(verify, token)
            return {"result": result, "requiresHumanReview": True}
        except PolicyUnverified:
            return JSONResponse({"error": "data_retention_unverified"}, status_code=503)
        except AccessDenied:
            return JSONResponse({"error": "access_denied"}, status_code=403)
        except (ValueError, UnicodeError, RecursionError):
            return JSONResponse({"error": "invalid_request_or_output"}, status_code=400)
        except Exception:
            return JSONResponse({"error": "temporarily_unavailable"}, status_code=503)
        finally:
            slots.release()
    return app

