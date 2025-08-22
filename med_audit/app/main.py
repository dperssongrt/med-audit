from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import traceback
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from soap import send_soap, eas_base_information
from SeleniumInterface import SeleniumInterfaceBase
from MetaViewWebInterface import MetaViewWebInterface
from bs4 import BeautifulSoup
from sendresults import send_results
import logging
import sys
from pythonjsonlogger import jsonlogger
import os
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

log_handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s', rename_fields={'levelname': 'severity'}
)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


class MyEyeDrAudit(SeleniumInterfaceBase):
    def __init__(self):
        super().__init__()
        self.wait = WebDriverWait(self.driver, 20)
        self.mvw_username = os.getenv('MVW_USERNAME')
        self.mvw_password = os.getenv('MVW_PASSWORD')
        self.results_container = {}

    def get_profile_info(self, tn):
        """Get EAS profile information to determine BCM vs ICM"""
        try:
            # Get the EAS Profile information (we still need this for BCM/ICM detection)
            eas_env = eas_base_information.format(tn=tn)
            eas_result = send_soap(eas_env)
            eas_soup = BeautifulSoup(eas_result, features="xml")
            eas_result_code = eas_soup.find('ResultCode').text
            
            if eas_result_code != "2001":
                return None, 'Unable to get Profile Information'

            eas_profile = eas_soup.find('CoSID').text

            # Check for profiles that don't have CommPortal access
            if 'emulated_pots' in eas_profile.lower() or 'grt_base' in eas_profile.lower():
                return None, 'No Commportal Access'

            # Determine if BCM or ICM profile
            bcm_profiles = ['business']
            if list(filter(lambda x: x in eas_profile.lower(), bcm_profiles)):
                return 'bcm', None
            else:
                return 'icm', None
                
        except Exception as e:
            print(f"Error getting profile for {tn}: {e}")
            return None, 'Error getting profile'

    def audit_call_forwarding(self, tn, call_handler):
        """Audit call forwarding settings in the current CommPortal tab"""
        try:
            # Determine the correct element IDs based on call handler type
            if call_handler == 'bcm':
                forward_radio_id = 'dcfEnabledTrue'
                forward_point_to_id = 'jsShowIf-DCF-Number._-NotEquals- jsFunction-setDCFForwardingDestinationName'
            else:  # icm
                forward_radio_id = 'summaryRadioForwardTo'
                forward_point_to_id = 'summarySelectForwardTo'

            # Find the new iframe and switch to it (existing CommPortal logic)
            iframe = self.wait.until(EC.visibility_of_element_located((By.ID, 'iFrameResizer0')))
            self.driver.switch_to.frame(iframe)

            # Check forwarding status
            forward_radio = self.wait.until(EC.visibility_of_element_located((By.ID, forward_radio_id)))

            if forward_radio.is_displayed():
                is_forwarding = forward_radio.is_selected()
                forwarding_destination = None
                
                if is_forwarding:
                    if call_handler == 'icm':
                        forwarding_destination = self.driver.find_elements(By.ID, forward_point_to_id)
                        forwarding_destination = forwarding_destination[0].get_attribute('value')
                    else:
                        forwarding_destination = self.driver.find_elements(By.CLASS_NAME, forward_point_to_id)
                        forwarding_destination = forwarding_destination[0].text
                    # Remove anything that is not a number from the forwarding destination
                    forwarding_destination = ''.join(filter(str.isdigit, forwarding_destination))
            else:
                is_forwarding = False
                forwarding_destination = None

            # Check for time of day handling (ICM only)
            is_using_schedule = False
            if call_handler == 'icm':
                if self.driver.find_element(By.ID, 'summaryRadioSchedules').is_displayed():
                    is_using_schedule = self.driver.find_element(By.ID, 'summaryRadioSchedules').is_selected()

            # Determine status
            status = 'Neither'
            if is_using_schedule:
                status = 'Using Schedule'
            elif is_forwarding:
                status = 'Forwarding to ' + forwarding_destination

            return status

        except Exception as e:
            print(f'Error auditing call forwarding for {tn}: {e}')
            return 'Error during audit'

    def record_result(self, tn, status):
        """Record the audit result for a telephone number"""
        self.results_container[tn] = status
        logging.info(f"TN: {tn} - Status: {status}")

    def write_results_to_csv(self):
        """Write the results container to a CSV file"""
        with open('results.csv', 'w') as f:
            for key in self.results_container.keys():
                f.write("%s,%s\n" % (key, self.results_container[key]))

    def send_email_results(self):
        """Send the results via email"""
        send_results()

    def run(self, tns: list):
        # Initialize MetaView Web interface (replaces SOAP setup)
        mvw_interface = MetaViewWebInterface(self)
        
        # Login to MetaView Web (one-time at start)
        if not mvw_interface.login_to_metaview():
            raise Exception("Failed to login to MetaView Web - check credentials")
        
        # Store main tab as MetaView Web tab
        self.tab_handles["metaview_main"] = self.driver.current_window_handle
        
        count = 1
        total = len(tns)
        start_time = time.time()
        restart_interval = 40  # Restart WebDriver every 40 subscribers to prevent cookie accumulation
        
        # Process each telephone number
        for tn in tns:
            # Periodic WebDriver restart to prevent cookie/header accumulation
            if count > 1 and (count - 1) % restart_interval == 0:
                print(f"Restarting WebDriver session after {count - 1} subscribers to prevent HTTP 400 errors...")
                
                # Close current driver
                self.driver.quit()
                
                # Re-initialize WebDriver with fresh session
                super().__init__()
                self.wait = WebDriverWait(self.driver, 20)
                
                # Re-create MetaView interface and login
                mvw_interface = MetaViewWebInterface(self)
                if not mvw_interface.login_to_metaview():
                    raise Exception("Failed to re-login to MetaView Web after driver restart")
                
                # Update main tab handle
                self.tab_handles["metaview_main"] = self.driver.current_window_handle
                print(f"WebDriver restart complete, continuing with TN processing...")
            # Calculate time estimation
            if count > 1:
                elapsed_time = time.time() - start_time
                avg_time_per_tn = elapsed_time / (count - 1)
                remaining_tns = total - count + 1
                estimated_remaining_seconds = avg_time_per_tn * remaining_tns
                
                hours = int(estimated_remaining_seconds // 3600)
                minutes = int((estimated_remaining_seconds % 3600) // 60)
                
                time_str = f"Estimated time remaining: {hours} Hours {minutes} Minutes"
            else:
                time_str = "Estimated time remaining: Calculating..."
            
            logging.info(f"Working on TN: {tn}  {count}/{total}")
            print(time_str)
            count += 1
            
            try:
                # Get profile information to determine BCM vs ICM (still needed for audit logic)
                call_handler, profile_error = self.get_profile_info(tn)
                if profile_error:
                    self.record_result(tn, profile_error)
                    continue
                
                # Search for subscriber in MetaView Web
                subscriber_tab = mvw_interface.search_subscriber(tn)
                
                if subscriber_tab:
                    # Open CommPortal for this subscriber
                    commportal_tab = mvw_interface.open_commportal_for_subscriber(subscriber_tab)
                    
                    if commportal_tab:
                        # Switch to CommPortal tab and run existing audit logic
                        self.switch_to_tab(commportal_tab)
                        
                        # Clear cookies and navigate to CommPortal login
                        self.driver.delete_all_cookies()
                        
                        # Wait a moment for CommPortal to load
                        try:
                            # Try to wait for CommPortal interface to load
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            
                            # Run the audit logic
                            status = self.audit_call_forwarding(tn, call_handler)
                            self.record_result(tn, status)
                            
                        except Exception as audit_error:
                            print(f"Error during CommPortal audit for {tn}: {audit_error}")
                            self.record_result(tn, "Error during audit")
                        
                        # Close CommPortal tab
                        self.close_tab(commportal_tab)
                    else:
                        self.record_result(tn, "No CommPortal Access")
                    
                    # Close the subscriber tab within MetaView UI after all work is complete
                    self.switch_to_tab("metaview_main")
                    mvw_interface.close_subscriber_tab_in_ui(tn)
                else:
                    self.record_result(tn, "Subscriber Not Found")
                    
            except Exception as e:
                print(f'Error processing {tn}: {e}')
                self.record_result(tn, f"Error: {str(e)}")
                # Ensure we're back on main tab after any error
                self.switch_to_tab("metaview_main")
                traceback.print_exc()
        
        # Final cleanup and results
        self.cleanup_subscriber_tabs()
        self.write_results_to_csv()
        self.send_email_results()


if __name__ == "__main__":
    # Relative path to geckodriver
    PATH = "./geckodriver_mac_m1"
    service = Service(PATH)

    #open file tns.txt and convert to a list to use for the function
    with open('tns.txt') as f:
        tns = f.readlines()
    tns = [x.strip() for x in tns]

    med_interface = MyEyeDrAudit()
    
    med_interface.run(tns)

    # Close the driver
    med_interface.driver.close()


