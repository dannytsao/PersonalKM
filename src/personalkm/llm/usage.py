"""Daily token accounting per provider.

This is what makes LLM management *automatic*: the router consults
`is_over_budget()` before every call, so when your Claude quota for the day
is spent, traffic flows to fallbacks (e.g. local Ollama) without any code
or config change — and flows back the next day.

State lives in .runtime/llm_usage.json (gitignored), keyed by local date.
"""
from __future__ import annotations

import json
import sys
import argparse
from datetime import date
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parents[3] / ".runtime"
USAGE_FILE = RUNTIME_DIR / "llm_usage.json"


def _load() -> dict:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save(data: dict) -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    USAGE_FILE.write_text(json.dumps(data, indent=2))


def record(provider: str, input_tokens: int, output_tokens: int) -> None:
    data = _load()
    day = data.setdefault(str(date.today()), {})
    p = day.setdefault(provider, {"input": 0, "output": 0, "calls": 0})
    p["input"] += input_tokens
    p["output"] += output_tokens
    p["calls"] += 1
    _save(data)


def today_total(provider: str) -> int:
    day = _load().get(str(date.today()), {})
    p = day.get(provider)
    return (p["input"] + p["output"]) if p else 0


def is_over_budget(provider: str, daily_budget: int | str) -> bool:
    if daily_budget in ("unlimited", None):
        return False
    return today_total(provider) >= int(daily_budget)


def report() -> str:
    day = _load().get(str(date.today()), {})
    if not day:
        return "No LLM usage recorded today."
    lines = [f"LLM usage for {date.today()}:"]
    for provider, p in sorted(day.items()):
        lines.append(
            f"  {provider:8s} calls={p['calls']:4d} "
            f"in={p['input']:8d} out={p['output']:8d} "
            f"total={p['input'] + p['output']:8d}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report PersonalKM LLM token usage.")
    sub = parser.add_subparsers(dest="command")
    report_parser = sub.add_parser("report", help="Print today's usage")
    report_parser.add_argument("--notify", action="store_true", help="Send report through configured notification channels")
    args = parser.parse_args(argv)

    if args.command == "report":
        text = report()
        print(text)
        if args.notify:
            from personalkm.llm.alerts import notify_usage_report

            notify_usage_report(text)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
