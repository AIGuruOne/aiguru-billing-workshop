"""Ask questions about the billing data in plain English.

    python3 -m billing.ask "which invoices are pending, and in which state?"

The model does the reasoning; every number it quotes comes from a tool call
into the engine. This is the only module in the project that needs a network
and an API key — nothing else imports it, so `check.py` and the engine keep
working on a laptop with no internet.

The Anthropic API is called over urllib rather than the SDK to honour the
standard-library-only rule in CLAUDE.md.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from .tools import TOOL_SCHEMAS, run_tool

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = "claude-sonnet-5"
MAX_TURNS = 8

SYSTEM_PROMPT = """You answer questions about a GST billing system for an Indian business.

Use the tools for every fact. Never estimate, recall or calculate a total
yourself — if you need a number, call a tool and quote what it returns.

Vocabulary in this domain:
- "pending" or "outstanding" means unpaid or part-paid, and never includes
  cancelled invoices.
- "cancelled" is the invoice lifecycle status, separate from payment status.
- Amounts are Indian rupees. Quote them exactly as the tools return them.

Answer in a few short sentences. When you list invoices, give the invoice
number, the customer, the state and the amount."""


class AskError(RuntimeError):
    """Raised when the conversation cannot be completed."""


def _post(payload: Dict[str, Any], api_key: str, timeout: float) -> Dict[str, Any]:
    """Send one request to the Messages API."""
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AskError(f"API returned {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise AskError(f"Could not reach the API: {exc.reason}") from None


def ask(
    question: str,
    api_key: Optional[str] = None,
    transport: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    verbose: bool = False,
    timeout: float = 60.0,
) -> str:
    """Answer a question, letting the model call tools until it is done.

    `transport` replaces the HTTP call, so the loop can be tested without a
    network or a key. It takes the request payload and returns the parsed
    response body.
    """
    if transport is None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise AskError(
                "No API key. Set ANTHROPIC_API_KEY in your environment, or pass "
                "api_key=... . Everything except this module works offline."
            )

        def transport(payload: Dict[str, Any]) -> Dict[str, Any]:
            return _post(payload, key, timeout)

    messages: List[Dict[str, Any]] = [{"role": "user", "content": question}]

    for _ in range(MAX_TURNS):
        response = transport(
            {
                "model": MODEL,
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "tools": TOOL_SCHEMAS,
                "messages": messages,
            }
        )

        if response.get("type") == "error":
            raise AskError(str(response.get("error", response)))

        content = response.get("content", [])
        messages.append({"role": "assistant", "content": content})

        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        if not tool_uses:
            answer = "\n".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
            return answer.strip()

        results = []
        for block in tool_uses:
            if verbose:
                print(f"  [tool] {block['name']}({json.dumps(block.get('input', {}))})")
            output = run_tool(block["name"], block.get("input", {}))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": json.dumps(output),
                }
            )

        messages.append({"role": "user", "content": results})

    raise AskError(f"Gave up after {MAX_TURNS} turns without a final answer.")


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[2].strip())
        return 1

    verbose = "--verbose" in argv
    question = " ".join(a for a in argv if a != "--verbose")

    try:
        print(ask(question, verbose=verbose))
    except AskError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
