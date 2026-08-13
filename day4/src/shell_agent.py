"""
DAY 4 - Deep Agent with shell access.

READ FIRST: ../00-deep-agent-shell.md
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent

load_dotenv()

PROVIDER = os.getenv("SANDBOX_PROVIDER", "local")
WORK_DIR = Path(__file__).resolve().parent.parent / "work"
VENV_SCRIPTS = Path(__file__).resolve().parent.parent / ".venv" / "Scripts"

llm = ChatOpenAI(
    model=os.getenv(
        "OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free"
    ),
    temperature=0,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = (
    "You are a Python coding assistant with shell access. "
    "Write files with your filesystem tools and run them with execute. "
    "If a command fails, read the error and fix your code."
)


def make_backend():
    """Return (backend, cleanup_fn). Default runs locally under day4/work."""
    if PROVIDER == "local":
        from deepagents.backends import LocalShellBackend

        WORK_DIR.mkdir(exist_ok=True)
        backend = LocalShellBackend(
            root_dir=str(WORK_DIR),
            virtual_mode=True,
            env={
                "PATH": f"{VENV_SCRIPTS}{os.pathsep}{os.environ.get('PATH', '')}"
            },
        )
        return backend, lambda: None

    if PROVIDER == "daytona":
        from daytona import Daytona
        from langchain_daytona import DaytonaSandbox

        sandbox = Daytona().create()
        return DaytonaSandbox(sandbox=sandbox), sandbox.stop

    if PROVIDER == "langsmith":
        from deepagents.backends import LangSmithSandbox
        from langsmith.sandbox import SandboxClient

        client = SandboxClient()
        sandbox = client.create_sandbox()
        return LangSmithSandbox(sandbox=sandbox), lambda: client.delete_sandbox(sandbox.name)

    raise ValueError(f"unknown SANDBOX_PROVIDER: {PROVIDER}")


TASK = (
    "1. Create calculator.py with add/sub/mul/div functions (div raises on zero). "
    "2. Write test_calculator.py with pytest tests, including the zero case. "
    "3. Run the tests with execute (use 'python -m pytest'; pip install pytest "
    "first if it's missing). "
    "4. If anything fails, fix it and re-run until green. "
    "5. Report the final pytest output."
)


if __name__ == "__main__":
    backend, cleanup = make_backend()
    try:
        agent = create_deep_agent(
            model=llm,
            system_prompt=SYSTEM_PROMPT,
            backend=backend,
        )
        result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})
        print(result["messages"][-1].content)
    finally:
        cleanup()