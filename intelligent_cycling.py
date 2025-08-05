# Import required libraries
import logging
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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

def intelligent_cycling_login():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    import logging
    import time
    import os
    from dotenv import load_dotenv

    load_dotenv()
    IC_USER = os.getenv("IC_USER")
    IC_PASS = os.getenv("IC_PASS")

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        logger.info("Navigating to the login page")
        driver.get("https://login.intelligent-cycling.com/")

        logger.info("Waiting for the login form to be present")
        driver.implicitly_wait(10)

        logger.info("Entering username")
        driver.find_element(By.ID, "Email").send_keys(IC_USER)

        logger.info("Entering password")
        driver.find_element(By.ID, "Password").send_keys(IC_PASS)

        logger.info("Submitting the login form")
        login_button = driver.find_element(By.CLASS_NAME, "btn.btn-ca-signup")
        login_button.click()

        logger.info("Successfully logged in to Intelligent Cycling")
        driver.implicitly_wait(10)

    except Exception as e:
        logger.error(f"Error during Intelligent Cycling login: {e}")
        raise
    finally:
        logger.info("Closing the browser.")
        driver.quit()
