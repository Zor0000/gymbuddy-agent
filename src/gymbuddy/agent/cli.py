"""GymBuddy CLI — ask the agent a question from the terminal.

    python -m gymbuddy.agent.cli "Bench is taken, alternative with dumbbells?"
    python -m gymbuddy.agent.cli --verbose "Build me a beginner push day at home"
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel

from gymbuddy.agent.graph_agent import answer

console = Console()


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    verbose = "--verbose" in argv or "-v" in argv
    question = " ".join(a for a in argv if not a.startswith("-")).strip()
    if not question:
        console.print("[red]Usage:[/red] python -m gymbuddy.agent.cli \"your question\"")
        return 2

    console.print(Panel(question, title="You", border_style="cyan"))
    if verbose:
        console.print("[dim]tool calls:[/dim]")
    result = answer(question, verbose=verbose)

    console.print(Panel(result["answer"] or "(no answer)", title="GymBuddy", border_style="green"))

    if result.get("reasoning_path"):
        trail = "  ".join(
            (f"[{p['node']}]" if "node" in p else f"-{p['edge']}->{p['to']}")
            for p in result["reasoning_path"]
        )
        console.print(f"[dim]path:[/dim] {trail}")
    if result.get("tools_used"):
        console.print(f"[dim]tools:[/dim] {', '.join(result['tools_used'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
