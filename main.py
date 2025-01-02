import pytesseract
from pytesseract import Output
import cv2
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables
load_dotenv(find_dotenv())


# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")

# Selenium parameters
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
LOGIN_URL = os.getenv("LOGIN_URL")
ONBOARD_USERNAME = os.getenv("ONBOARD_USERNAME")
ONBOARD_PASSWORD = os.getenv("ONBOARD_PASSWORD")

def locate_text(image_path, target_text):
    """Locate the target text in the image and return its coordinates."""
    img = cv2.imread(image_path)
    data = pytesseract.image_to_data(img, output_type=Output.DICT)

    for i, text in enumerate(data['text']):
        if target_text in text:
            x, y, w, h = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            print(f"'{target_text}' found at ({x=}, {y=}, {w=}, {h=})")
            return x, y, w, h
    print(f"'{target_text}' not found in the image.")
    return None

def click_on_text(driver, window_x, window_y, y_offset, image_path, target_text):
    """Locate the target text and perform a click on its coordinates."""
    coords = locate_text(image_path, target_text)
    if coords:
        x, y, w, h = coords
        screen_x = window_x + x + w // 2
        screen_y = window_y + y + h // 2 + y_offset
        pyautogui.click(screen_x, screen_y)
        print(f"Clicked on '{target_text}' at screen coordinates ({screen_x}, {screen_y})")
        return True
    else:
        print(f"Could not find '{target_text}' in the image.")
        return False

def main():
    # Selenium setup
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service)

    try:
        # Open login page
        driver.get(LOGIN_URL)

        # Wait for username field to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

        # Login
        driver.find_element(By.ID, "username").send_keys(ONBOARD_USERNAME)
        driver.find_element(By.ID, "password").send_keys(ONBOARD_PASSWORD)
        driver.find_element(By.ID, "password").send_keys("\n")

        # Wait for login to complete
        WebDriverWait(driver, 15).until(EC.url_changes(LOGIN_URL))

        # Make the browser full-screen
        driver.fullscreen_window()
        WebDriverWait(driver, 5).until(
            lambda d: driver.execute_script("return document.fullscreenElement !== null;")
        )

        # Get the browser's position on the screen
        window_x = driver.execute_script("return window.screenX;")
        window_y = driver.execute_script("return window.screenY;")
        y_offset = 50  # Offset to account for the browser's warning bar
        print(f"Browser position: ({window_x=}, {window_y=})")

        # Take a screenshot for main menu
        screenshot_path_1 = "screenshot_1.png"
        driver.save_screenshot(screenshot_path_1)

        # Locate and click "Planning"
        if not click_on_text(driver, window_x, window_y, y_offset, screenshot_path_1, "Planning"):
            return  # Exit if "Planning" is not found

        # Wait for "My schedule" to appear
        schedule_locator = (By.XPATH, "//a[contains(., 'schedule')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(schedule_locator))
        print("'My schedule' is now visible.")

        # Take another screenshot for locating "My schedule"
        screenshot_path_2 = "screenshot_2.png"
        driver.save_screenshot(screenshot_path_2)

        # Locate and click "My schedule"
        click_on_text(driver, window_x, window_y, y_offset, screenshot_path_2, "schedule")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
