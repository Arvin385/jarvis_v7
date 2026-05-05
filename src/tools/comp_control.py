import pyautogui

def run_computer_control(intent, params):
    if intent == "mouse_move":
        pyautogui.moveTo(params["x"], params["y"])
        return {"status": "moved"}

    elif intent == "left_click":
        pyautogui.click()
        return {"status": "clicked"}

    elif intent == "type":
        pyautogui.write(params["text"])
        return {"status": "typed"}

    elif intent == "keypress":
        pyautogui.press(params["key"])
        return {"status": "pressed"}

    return {"error": "unknown intent"}