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

from .agent import analyze_profile_result, run_agent_result
from .chat import answer_question
from .extraction import MAX_UPLOAD_BYTES, extract_upload
from .models import SafetyAssessment
from .rules import TOTAL_RULE_COUNT
from .server import SAMPLE_PROFILE

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

    offline = mode == "offline"
    profile = body.get("profile")

    try:
        if profile is None:
            # No profile supplied: pull the protected one over authenticated MCP.
            # The agent uses asyncio.run() internally, so it must run off this loop.
            try:
                result = await run_in_threadpool(run_agent_result, offline=offline)
            except (OSError, ImportError) as exc:
                # A hosted deployment has no route to a local MCP service. Say
                # so plainly instead of reporting a generic agent failure.
                return JSONResponse(
                    {
                        "error": (
                            "The protected MCP service is not reachable from this "
                            "deployment. Enter a profile in the slots or upload a "
                            "medication list instead."
                        ),
                        "detail": type(exc).__name__,
                    },
                    status_code=503,
                )
        else:
            if not isinstance(profile, dict):
                return JSONResponse(
                    {"error": "profile must be an object"}, status_code=400
                )
            result = await run_in_threadpool(
                analyze_profile_result, profile, offline=offline
            )
    except ValueError as exc:
        # Guardrail rejections are safe to show: they describe the input, not secrets.
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:  # noqa: BLE001 - surface a safe, generic failure
        return JSONResponse(
            {"error": f"{type(exc).__name__}: agent run failed"}, status_code=502
        )

    return JSONResponse(result.model_dump())


async def sample(request: Request) -> JSONResponse:
    """Prefill the input slots with the de-identified demonstration profile."""
    return JSONResponse(SAMPLE_PROFILE)


async def extract(request: Request) -> JSONResponse:
    """Read an uploaded document or image into the input slots.

    Nothing is analysed here. The operator confirms the extracted rows before
    running the review, which keeps a human between a scanned page and a
    clinical finding.
    """
    try:
        form = await request.form(max_files=1, max_fields=4)
    except Exception:  # noqa: BLE001 - malformed multipart bodies vary by client
        return JSONResponse({"error": "Could not read the upload"}, status_code=400)

    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return JSONResponse({"error": "No file was attached"}, status_code=400)

    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "File is larger than the 2 MB limit"}, 413)

    try:
        result = await run_in_threadpool(
            extract_upload,
            upload.filename or "",
            upload.content_type or "",
            data,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:  # noqa: BLE001 - surface a safe, generic failure
        return JSONResponse(
            {"error": f"{type(exc).__name__}: extraction failed"}, status_code=502
        )

    return JSONResponse(result.model_dump())


async def chat(request: Request) -> JSONResponse:
    """Answer a follow-up question grounded in an assessment from /api/analyze."""
    try:
        body = await request.json()
    except ValueError:
        body = {}

    mode = str(body.get("mode", "offline")).lower()
    if mode not in {"offline", "live"}:
        return JSONResponse(
            {"error": "mode must be 'offline' or 'live'"}, status_code=400
        )

    question = str(body.get("question", ""))
    history = body.get("history") or []
    if not isinstance(history, list):
        return JSONResponse({"error": "history must be a list"}, status_code=400)

    try:
        # Re-validating the assessment stops a tampered payload from becoming
        # the model's grounding context.
        assessment = SafetyAssessment.model_validate(body.get("assessment"))
    except Exception:  # noqa: BLE001 - pydantic raises several types here
        return JSONResponse(
            {"error": "a valid assessment from /api/analyze is required"},
            status_code=400,
        )

    try:
        reply = await run_in_threadpool(
            answer_question,
            assessment,
            question,
            history,
            offline=mode == "offline",
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)
    except Exception as exc:  # noqa: BLE001 - surface a safe, generic failure
        return JSONResponse(
            {"error": f"{type(exc).__name__}: chat failed"}, status_code=502
        )

    return JSONResponse(reply.model_dump())


app = Starlette(
    routes=[
        Route("/", index),
        Route("/health", health),
        Route("/api/sample", sample),
        Route("/api/analyze", analyze, methods=["POST"]),
        Route("/api/extract", extract, methods=["POST"]),
        Route("/api/chat", chat, methods=["POST"]),
        Mount("/static", StaticFiles(directory=STATIC_DIR), name="static"),
    ]
)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
