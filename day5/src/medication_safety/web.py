"""Local Starlette dashboard that runs the agent server-side.

The browser never receives an API key or an MCP bearer token. It posts a mode
and receives the assessment the deterministic layer already produced.
"""

from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .agent import run_agent_result
from .rules import TOTAL_RULE_COUNT

STATIC_DIR = Path(__file__).parent / "static"


async def health(request: Request) -> JSONResponse:
    """Report that the dashboard process is up."""
    return JSONResponse({"status": "ok", "rules": TOTAL_RULE_COUNT})


async def index(request: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


async def analyze(request: Request) -> JSONResponse:
    """Run the agent for the requested mode and return the assessment."""
    try:
        body = await request.json()
    except ValueError:
        body = {}

    mode = str(body.get("mode", "offline")).lower()
    if mode not in {"offline", "live"}:
        return JSONResponse(
            {"error": "mode must be 'offline' or 'live'"}, status_code=400
        )

    try:
        # The agent uses asyncio.run() internally, so it must run off this loop.
        result = await run_in_threadpool(run_agent_result, offline=mode == "offline")
    except ValueError as exc:
        # Guardrail rejections are safe to show: they describe the input, not secrets.
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:  # noqa: BLE001 - surface a safe, generic failure
        return JSONResponse(
            {"error": f"{type(exc).__name__}: agent run failed"}, status_code=502
        )

    return JSONResponse(result.model_dump())


app = Starlette(
    routes=[
        Route("/", index),
        Route("/health", health),
        Route("/api/analyze", analyze, methods=["POST"]),
        Mount("/static", StaticFiles(directory=STATIC_DIR), name="static"),
    ]
)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
