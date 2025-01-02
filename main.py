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

# ---------- CONSTANTS ----------

# Load environment variables
load_dotenv(find_dotenv())

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")

# Selenium parameters
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
LOGIN_URL = os.getenv("LOGIN_URL")
ONBOARD_USERNAME = os.getenv("ONBOARD_USERNAME")
ONBOARD_PASSWORD = os.getenv("ONBOARD_PASSWORD")

# Global variables
Y_OFFSET = 50  # Offset to account for the browser's warning bar

# ---------- FUNCTIONS ----------

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

def click_on_text(driver, Y_OFFSET, image_path, target_text):
    """Locate the target text and perform a click on its coordinates."""
    coords = locate_text(image_path, target_text)
    if coords:
        x, y, w, h = coords
        screen_x = x + w // 2
        screen_y = y + h // 2 + Y_OFFSET
        pyautogui.click(screen_x, screen_y)
        print(f"Clicked on '{target_text}' at screen coordinates ({screen_x}, {screen_y})\n")
        return True
    else:
        print(f"Could not find '{target_text}' in the image.")
        return False
    
def restore_fullscreen(driver):
    """Ensure the browser is in full-screen mode."""
    driver.fullscreen_window()
    WebDriverWait(driver, 5).until(
        lambda d: driver.execute_script("return document.fullscreenElement !== null;")
    )
    print("Browser restored to full-screen mode.")

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
        restore_fullscreen(driver)

        # Click 1: Planning
        screenshot_path_1 = "screenshot_1.png"
        driver.save_screenshot(screenshot_path_1)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_1, "Planning"):
            print("Could not find 'Planning' in the image.")
            return

        # Restore full-screen after clicking "Planning"
        restore_fullscreen(driver)

        # Click 2: My schedule
        schedule_locator = (By.XPATH, "//a[contains(., 'schedule')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(schedule_locator))
        print("'My schedule' is now visible.")
        screenshot_path_2 = "screenshot_2.png"
        driver.save_screenshot(screenshot_path_2)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_2, "schedule"):
            print("Could not find 'schedule' in the image.")
            return

        # Restore full-screen after clicking "My schedule"
        restore_fullscreen(driver)

        # Click 3: Month
        month_locator = (By.XPATH, "//button[contains(., 'Month')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(month_locator))
        print("'Month' is now visible.")
        screenshot_path_3 = "screenshot_3.png"
        driver.save_screenshot(screenshot_path_3)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_3, "Month"):
            print("Could not find 'Month' in the image.")
            return
        
        # Click 4: Download the planning.ics file
        download_icon_locator = (By.XPATH, "//i[contains(@class, 'fa fa-download Fs20 Gray')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(download_icon_locator))
        print("Download icon is now visible.")

        # Locate and click the download icon using JavaScript
        download_icon = driver.find_element(By.XPATH, "//i[contains(@class, 'fa fa-download Fs20 Gray')]")
        driver.execute_script("arguments[0].click();", download_icon)
        print("Clicked on the download icon using JavaScript.")




    finally:
        input("Press Enter to close.")
        driver.quit()


if __name__ == "__main__":
    main()
