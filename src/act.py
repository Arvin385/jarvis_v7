import subprocess
from tools.terminal import run_terminal
from tools.browser import run_browser
from tools.screen import run_screen_capture
from tools.comp_control import run_computer_control
from tools.gmail import run_gmail


def act_call(action):
    tool = action["tool"]
    params = action.get("parameters", {})

    if tool == "terminal":
        return run_terminal(params)

    elif tool == "browser":
        return run_browser(params, verb=action.get("action"))

    elif tool == "gmail":
        return run_gmail(params, verb=action.get("action"))

    # elif tool == "screen_capture":
    #     return run_screen_capture()

    # elif tool == "computer_control":
    #     return run_computer_control(intent, params)

    else:
        raise Exception(f"Unknown tool: {tool}")