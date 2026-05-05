import pyautogui

def run_screen_capture():
    path = "screenshot.png"
    img = pyautogui.screenshot()
    img.save(path)

    return {"screenshot_path": path}