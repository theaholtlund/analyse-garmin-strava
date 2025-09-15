def intelligent_cycling_login():
    # Import required libraries
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options

    # Import shared configuration and functions from other scripts
    from config import logger, check_ic_credentials

    # Get credentials and run credentials check
    creds = check_ic_credentials()
    IC_USER = creds["IC_USER"]
    IC_PASS = creds["IC_PASS"]

    # Configure options for Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--headless")

    # Initialise the Chrome web driver
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
        logger.error(f"Error during Intelligent Cycling login: {e}", exc_info=True)
        raise
    finally:
        logger.info("Closing the browser")
        driver.quit()
