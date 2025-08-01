# Import required libraries
import logging
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Load environment variables
load_dotenv()

# Retrieve credentials from environment variables
IC_USER = os.getenv("IC_USER")
IC_PASS = os.getenv("IC_PASS")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--headless")  # Run in headless mode, no GUI

# Initialise the Chrome web driver
driver = webdriver.Chrome(options=chrome_options)

try:
    logger.info("Navigating to the login page")
    driver.get("https://login.intelligent-cycling.com/")

    # Wait for the login form to be present
    logger.info("Waiting for the login form to be present")
    driver.implicitly_wait(10)

    logger.info("Entering username")
    driver.find_element(By.ID, "Email").send_keys(IC_USER)

    logger.info("Entering password")
    driver.find_element(By.ID, "Password").send_keys(IC_PASS)

    # Locate the login button by its class name and click it
    logger.info("Submitting the login form")
    login_button = driver.find_element(By.CLASS_NAME, "btn.btn-ca-signup")
    login_button.click()
    logger.info("Successfully logged in to Intelligent Cycling")

    # Wait for the dashboard to load
    logger.info("Waiting for the dashboard to load")
    driver.implicitly_wait(10)

except TimeoutException as e:
    logger.error(f"Timeout occurred: {e}")
except NoSuchElementException as e:
    logger.error(f"Element not found: {e}")
except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
finally:
    logger.info("Closing the browser.")
    driver.quit()
