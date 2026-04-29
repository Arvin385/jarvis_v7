from llm import generate_stream, generate_loq, generate_phone, generate_xenbook, SYSTEM_PROMPT, CLASSIFIER_PROMPT, parse_classifier_output
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import sys
from rich.live import Live

console = Console()
prompt = " ".join(sys.argv[1:])


CLI_PROMPT = """
You are Jarvis, a command-line programming and systems assistant embedded in a terminal environment.

You possess the knowledge, experience, and judgment of a senior-level software engineer and systems architect.

Your role is to act as a highly competent technical expert assisting the user by producing correct, efficient, and production-quality solutions.

Core behavior:
- Default to concise responses (1–2 lines maximum).
- Only expand when necessary for correctness, debugging, or system design clarity.
- Prioritize correctness, robustness, security, and performance over simplicity.
- Assume a Linux environment (zsh/bash) unless stated otherwise.
- Prefer direct solutions: commands, code, configs, or precise steps.
- When multiple solutions exist, choose the most reliable and industry-standard approach.
- Identify edge cases and failure modes when relevant, but briefly.
- Do not include filler, greetings, or conversational language.

Output style:
- Use bullet points for structured reasoning or options.
- Use code blocks for commands, configs, and code.
- Keep formatting optimized for terminal readability.

Important:
- You are not simulating a personality or teaching style.
- You are a high-trust technical execution engine that provides expert-level answers.

"""


def render(text: str) -> Panel:
    md = Markdown(text)

    return Panel(
        md,
        title="[bold cyan]jarvis[/bold cyan]",
        border_style="cyan"
    )

def main():
    payload = json.loads(sys.argv[1])

    prompt = payload["prompt"]
    context = payload["context"]

    output = ""

    system = f"""
    {CLI_PROMPT}

    Current environment:
    - cwd: {context.get("cwd")}
    - git_branch: {context.get("git_branch")}
    - git_status: {context.get("git_status")}
    - last_cmd: {context.get("last_cmd")}
    - shell: {context.get("shell")}
    - host: {context.get("host")}

    Directory snapshot (top-level):
    {context.get("dir")}
    """
    stream = generate_stream(prompt, system)

    with Live(render(""), console=console, refresh_per_second=20) as live:
        for token in stream:
            output += token
            live.update(render(output))


if __name__ == "__main__":
    main()