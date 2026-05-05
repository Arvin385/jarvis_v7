from llm import generate_cli
import json
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live

console = Console()

CLI_PROMPT = """
You are Jarvis, a terminal-based AI assistant.

You MUST respond with ONLY valid JSON in this exact schema:

{
  "content": "<markdown text to display>",
  "tool": null OR {
    "name": "<tool_name>",
    "args": { ... }
  }
}

-------------------------
AVAILABLE TOOLS
-------------------------

1. shell
- Execute terminal commands
- args: { "cmd": "<command>" }

2. 
-------------------------
CORE RULES
-------------------------

1. TOOL DECISION
Use a tool ONLY if the user explicitly or implicitly wants an action performed.

Examples requiring tools:
- run commands
- manipulate files
- inspect system state
- install / build / execute

If the user is asking for explanation, guidance, or knowledge → DO NOT use tools.

2. SHELL TOOL USAGE
Use "shell" ONLY for direct terminal commands.

DO NOT:
- invent scripts or file paths
- reference non-existent files
- assume project structure unless shown in context

GOOD:
- ls
- seq 1 10
- python3 -m venv venv

BAD:
- ./scripts/run.sh
- scripts/print_numbers.sh

3. CONTENT RULE
"content" is for human-readable explanation ONLY.

- Must NEVER contain executable commands
- Must NOT duplicate the command
- Keep concise (1–2 lines unless necessary)

4. COMMAND QUALITY
- Prefer simplest correct command
- Avoid unnecessary flags
- Do not guess unknown system state

If unsure → ask or respond without tool.

5. SAFETY
NEVER generate destructive commands unless explicitly requested.

Examples:
- rm -rf
- sudo operations
- system modifications

If needed → explain instead of executing.

6. OUTPUT STRICTNESS
- Output ONLY valid JSON
- No markdown outside JSON
- No backticks
- No extra text

-------------------------
EXAMPLES
-------------------------

User: list files
Response:
{
  "content": "Listing files in current directory",
  "tool": { "name": "shell", "args": { "cmd": "ls" } }
}

User: what does ls do
Response:
{
  "content": "Lists files and directories in the current directory",
  "tool": null
}
"""

from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


def render_text_stream(text: str):
    md = Markdown(text)
    return Panel(
        md,
        title="[bold cyan]jarvis[/bold cyan]",
        border_style="cyan"
    )


def render_command(cmd: str):
    t = Text()
    t.append("▶ COMMAND\n", style="bold yellow")
    t.append(cmd, style="bold white")
    t.append("\n\n[Enter] Run   [n] Cancel", style="dim")

    return Panel(
        t,
        title="[bold red]EXECUTABLE[/bold red]",
        border_style="red"
    )

import time
import sys

def stream_text(live, base_text: str, speed: float = 0.01):
    out = ""
    for ch in base_text:
        out += ch
        live.update(render_text_stream(out))
        time.sleep(speed)
    return out


def main():
    payload = json.loads(sys.argv[1])

    prompt = payload["prompt"]
    context = payload["context"]

    system = f"""
{CLI_PROMPT}

Context:
cwd: {context.get("cwd")}
git_branch: {context.get("git_branch")}
git_status: {context.get("git_status")}
last_cmd: {context.get("last_cmd")}
shell: {context.get("shell")}
host: {context.get("host")}
dir: {context.get("dir")}
"""

    response = generate_cli(prompt, system)

    response = response.strip().replace("```json", "").replace("```", "")
    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1:
        print(response)
        return

    data = json.loads(response[start:end+1])

    content = data.get("content", "")
    tool = data.get("tool")

    # -------------------------
    # STREAM TEXT (CHAR-BY-CHAR)
    # -------------------------
    with Live(render_text_stream(""), console=console, refresh_per_second=30) as live:
        if content:
            streamed = ""
            for ch in content:
                streamed += ch
                live.update(render_text_stream(streamed))
                time.sleep(0.005)

    # -------------------------
    # TOOL RENDER (CLEAR UI SEPARATION)
    # -------------------------
    if tool and tool.get("name") == "shell":
        cmd = tool["args"]["cmd"]

        console.print(render_command(cmd))

        choice = input().strip().lower()

        if choice in ["", "y"]:
            subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()

