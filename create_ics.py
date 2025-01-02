import pytesseract
from pytesseract import Output
import cv2
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv, find_dotenv
import os
import time

# ---------- CONSTANTS ----------

# Load environment variables
load_dotenv(find_dotenv())

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")

# Selenium parameters
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
DOWNLOADS_PATH = os.getenv("DOWNLOADS_PATH")
LOGIN_URL = os.getenv("LOGIN_URL")
ONBOARD_USERNAME = os.getenv("ONBOARD_USERNAME")
ONBOARD_PASSWORD = os.getenv("ONBOARD_PASSWORD")

# Global variables
Y_OFFSET = 50  # Offset to account for the browser's warning bar
BIG_ICS_FILE = os.path.join(DOWNLOADS_PATH, "big_planning.ics")

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
        print(f"Clicked on '{target_text}' at screen coordinates ({screen_x}, {screen_y})")
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
    print("\nBrowser restored to full-screen mode.")

def append_to_big_ics(planning_ics_path):
    """Append the content of a downloaded .ics file to the big ICS file."""
    if not os.path.exists(planning_ics_path):
        print(f"File {planning_ics_path} does not exist, skipping.")
        return

    with open(planning_ics_path, "r") as file:
        lines = file.readlines()
    
    with open(BIG_ICS_FILE, "a") as big_file:
        for line in lines:
            if "BEGIN:VEVENT" in line or "END:VEVENT" in line or ("BEGIN" not in line and "END" not in line):
                big_file.write(line)

    print(f"Appended {planning_ics_path} to {BIG_ICS_FILE}")
    
# ---------- MAIN ----------

def main_ics():
    # Set Chrome options to automatically allow multiple downloads
    chrome_options = Options()
    chrome_prefs = {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", chrome_prefs)

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        
        # ----------------------------------------------------
        # LOG IN
        
        # Create/reset the big_planning.ics file
        with open(BIG_ICS_FILE, "w") as file:
            file.write("BEGIN:VCALENDAR\n")

        # Go to login page
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").send_keys(ONBOARD_USERNAME)
        driver.find_element(By.ID, "password").send_keys(ONBOARD_PASSWORD)
        driver.find_element(By.ID, "password").send_keys("\n")
        WebDriverWait(driver, 15).until(EC.url_changes(LOGIN_URL))
        
        restore_fullscreen(driver)
        
        # ----------------------------------------------------
        # NAVIGATE TO THE PLANNING PAGE

        # Click "Planning"
        screenshot_path_1 = "screenshot_1.png"
        driver.save_screenshot(screenshot_path_1)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_1, "Planning"):
            print("Could not find 'Planning' in the image.")
            return

        restore_fullscreen(driver)

        # Click "My schedule"
        schedule_locator = (By.XPATH, "//a[contains(., 'schedule')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(schedule_locator))
        print("'My schedule' is now visible.")
        screenshot_path_2 = "screenshot_2.png"
        driver.save_screenshot(screenshot_path_2)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_2, "schedule"):
            print("Could not find 'schedule' in the image.")
            return

        restore_fullscreen(driver)

        # Click "Month"
        month_locator = (By.XPATH, "//button[contains(., 'Month')]")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(month_locator))
        print("'Month' is now visible.")
        screenshot_path_3 = "screenshot_3.png"
        driver.save_screenshot(screenshot_path_3)
        if not click_on_text(driver, Y_OFFSET, screenshot_path_3, "Month"):
            print("Could not find 'Month' in the image.")
            return
        
        # ----------------------------------------------------
        # RETRIEVE THE PLANNING (NEXT 3 MONTHS)
        
        # Loop through months
        for k in range(4):  
            print(f"\n --- Month {k+1} --- \n")
            # Scroll to bottom
            scroll_height = driver.execute_script("return document.body.scrollHeight;")
            driver.execute_script(f"window.scrollTo(0, {scroll_height});")
            # Delete old .ics
            planning_ics_path = os.path.join(DOWNLOADS_PATH, "planning.ics")
            if os.path.exists(planning_ics_path):
                os.remove(planning_ics_path)
                #print("Deleted older planning.ics file.")
            # Click the download icon
            download_icon_locator = (By.XPATH, "//i[contains(@class, 'fa fa-download Fs20 Gray')]")
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(download_icon_locator))
            #print("Download icon is now visible.")
            download_icon = driver.find_element(By.XPATH, "//i[contains(@class, 'fa fa-download Fs20 Gray')]")
            driver.execute_script("arguments[0].click();", download_icon)
            #print("Clicked on the download icon using JavaScript.")
            WebDriverWait(driver, 10).until(lambda d: os.path.exists(planning_ics_path))
            print("Downloaded planning.ics")
            # Append to big .ics file
            append_to_big_ics(planning_ics_path)
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            # Wait the loading of "Next Month" button
            next_month_locator = (By.XPATH, "//button[@class='fc-next-button ui-button ui-state-default ui-corner-left ui-corner-right']")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(next_month_locator))
            next_month_button = driver.find_element(By.XPATH, "//button[@class='fc-next-button ui-button ui-state-default ui-corner-left ui-corner-right']")
            # Click on "Next Month"
            driver.execute_script("arguments[0].click();", next_month_button)
            print("Navigated to the next month.")
            # Wait for next month view to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'fc-month-view')]"))
            )

    finally:
        print("\nClosing the browser.")
        driver.quit()
        print("\nDone !")
