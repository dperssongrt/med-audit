import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class MetaViewWebInterface:
    def __init__(self, selenium_base):
        self.driver = selenium_base.driver
        self.selenium_base = selenium_base
        self.mvw_base_url = "https://mvw.granitevoip.com:8445/"
        self.mvw_username = os.getenv('MVW_USERNAME')
        self.mvw_password = os.getenv('MVW_PASSWORD')
        self.login_timeout = int(os.getenv('COMMPORTAL_TIMEOUT', '30'))
        self.search_timeout = 15

    def login_to_metaview(self):
        """Implement 5-step login process from specification"""
        try:
            print(f"Logging into MetaView Web at {self.mvw_base_url}")
            
            # Step 1: Navigate to MVW URL
            self.driver.get(self.mvw_base_url)
            
            # Step 2: Enter username
            username_input = WebDriverWait(self.driver, self.login_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input.gwt-TextBox[style*="width: 90%"]'))
            )
            username_input.clear()
            username_input.send_keys(self.mvw_username)
            
            # Step 3: Enter password  
            password_input = self.driver.find_element(By.CSS_SELECTOR, 'input.gwt-PasswordTextBox[style*="width: 90%"]')
            password_input.clear()
            password_input.send_keys(self.mvw_password)
            
            # Step 4: Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button.gwt-Button')
            login_button.click()
            
            # Step 5: Wait for welcome message
            WebDriverWait(self.driver, self.login_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.gwt-Label'))
            )
            
            print("Successfully logged into MetaView Web")
            return True
            
        except TimeoutException as e:
            print(f"MetaView Web login timeout: {e}")
            return False
        except Exception as e:
            print(f"MetaView Web login failed: {e}")
            return False

    def search_subscriber(self, telephone_number):
        """Search for subscriber and return tab ID if found"""
        try:
            print(f"Searching for subscriber: {telephone_number}")
            
            # Enter TN in search box
            search_input = WebDriverWait(self.driver, self.search_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input.gwt-TextBox.gwt-TextBox-search'))
            )
            search_input.clear()
            search_input.send_keys(telephone_number)
            
            # Click search button with "Search All" text
            search_button = WebDriverWait(self.driver, self.search_timeout).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@class="mvw-Split-Button-Label" and contains(text(), "Search All")]'))
            )
            search_button.click()
            
            # Wait for subscriber tab/button to appear - look for button containing subscriber info
            try:
                WebDriverWait(self.driver, self.search_timeout).until(
                    EC.presence_of_element_located((By.XPATH, f'//button[contains(text(), "Subscriber {telephone_number}")]'))
                )
                print(f"Found subscriber {telephone_number}")
                return f"subscriber_{telephone_number}"
            except TimeoutException:
                print(f"Subscriber {telephone_number} not found or no results")
                return None
                
        except TimeoutException as e:
            print(f"Timeout during subscriber search for {telephone_number}: {e}")
            return None
        except Exception as e:
            print(f"Subscriber search failed for {telephone_number}: {e}")
            return None

    def open_commportal_for_subscriber(self, subscriber_tab_id):
        """Click Open in CommPortal button and return new tab ID"""
        try:
            print(f"Opening CommPortal for {subscriber_tab_id}")
            
            # Wait for "Open in CommPortal" button to be available
            commportal_button = WebDriverWait(self.driver, self.search_timeout).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@class="mvw-Split-Button-Label-No-Icon" and contains(text(), "Open in CommPortal")]'))
            )
            
            # Get current tab count before clicking
            current_tabs = len(self.driver.window_handles)
            
            # Click the button
            commportal_button.click()
            
            # Wait for new tab to open
            WebDriverWait(self.driver, self.login_timeout).until(
                lambda driver: len(driver.window_handles) > current_tabs
            )
            
            # Get the new tab handle
            new_handles = set(self.driver.window_handles) - set(self.selenium_base.tab_handles.values())
            if new_handles:
                new_handle = list(new_handles)[0]
                commportal_tab_id = f"commportal_{subscriber_tab_id}"
                self.selenium_base.tab_handles[commportal_tab_id] = new_handle
                print(f"Successfully opened CommPortal tab: {commportal_tab_id}")
                return commportal_tab_id
            
            print("Failed to detect new CommPortal tab")
            return None
            
        except TimeoutException as e:
            print(f"Timeout waiting for CommPortal button or new tab for {subscriber_tab_id}: {e}")
            return None
        except Exception as e:
            print(f"Failed to open CommPortal for {subscriber_tab_id}: {e}")
            return None

    def close_subscriber_tab_in_ui(self, telephone_number):
        """Close the subscriber tab within MetaView Web UI (not browser tab)"""
        try:
            print(f"Closing subscriber tab for {telephone_number} in MetaView UI")
            
            # Try multiple XPath strategies to find the close button (Strategy 3 proven most reliable)
            xpath_strategies = [
                # Strategy 3: Find close button in same table row (PROVEN WORKING)
                f'//button[@class="gwt-Button" and contains(text(), "Subscriber {telephone_number}")]/ancestor::tr//button[@class="gwt-Button closeButton"]',
                
                # Strategy 4: Fallback - find the subscriber button, then look for closeButton in parent elements
                f'//button[@class="gwt-Button" and contains(text(), "Subscriber {telephone_number}")]/ancestor::table//button[@class="gwt-Button closeButton"]',
                
                # Strategy 2: Fallback - Look within the same table structure
                f'//button[@class="gwt-Button" and contains(text(), "Subscriber {telephone_number}")]/../../../..//button[@class="gwt-Button closeButton"]',
                
                # Strategy 1: Original complex path (kept as final fallback)
                f'//button[@class="gwt-Button" and contains(text(), "Subscriber {telephone_number}")]/../../following-sibling::td//button[@class="gwt-Button closeButton"]'
            ]
            
            for i, xpath in enumerate(xpath_strategies, 1):
                try:
                    close_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    close_button.click()
                    print(f"Successfully closed subscriber tab for {telephone_number}")
                    return True
                except TimeoutException:
                    continue
            
            print(f"Could not find close button for subscriber {telephone_number}")
            return False
                
        except Exception as e:
            print(f"Error closing subscriber tab for {telephone_number}: {e}")
            return False

    def handle_no_access_case(self, telephone_number):
        """Handle case where subscriber has no CommPortal access"""
        print(f"Subscriber {telephone_number} has no CommPortal access")
        return "No CommPortal Access"