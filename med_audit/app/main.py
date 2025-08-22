from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import traceback
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from soap import send_soap, eas_base_information
from SeleniumInterface import SeleniumInterfaceBase
from bs4 import BeautifulSoup
from sendresults import send_results
import logging
import sys
from pythonjsonlogger import jsonlogger


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


    def run(self, tns: list):
        results_container = {}
        count = 1
        total = len(tns)
        for tn in tns:
            logging.info(f"Working on TN: {tn}  {count}/{total}")
            count += 1
            try:
                # Get the EAS Password
                eas_env = eas_base_information.format(tn=tn)
                eas_result = send_soap(eas_env)
                eas_soup = BeautifulSoup(eas_result, features="xml")
                eas_result_code = eas_soup.find('ResultCode').text
                if eas_result_code != "2001":
                    results_container[tn] = 'Unable to get Password'
                    continue

                # BCM and ICM have different ids for commportal fields so we need to identify which one we are using
                bcm_profiles = ['business']
                eas_profile = eas_soup.find('CoSID').text

                # We have a special case where emulated_pots has EAS service but not commportal access
                if 'emulated_pots' in eas_profile.lower() or \
                    'grt_base' in eas_profile.lower():
                    results_container[tn] = 'No Commportal Access'
                    continue

                # Check if the eas profile is a BCM profile
                if list(filter(lambda x: x in eas_profile.lower(), bcm_profiles)):
                    forward_radio_id = 'dcfEnabledTrue'
                    forward_point_to_id = 'jsShowIf-DCF-Number._-NotEquals- jsFunction-setDCFForwardingDestinationName'
                    call_handler = 'bcm'
                else:
                    forward_radio_id = 'summaryRadioForwardTo'
                    forward_point_to_id = 'summarySelectForwardTo'
                    call_handler = 'icm'

                # Now we try to find the password
                eas_password = eas_soup.find('Password')
                if eas_password:
                    eas_password = eas_password.text
                else:
                    results_container[tn] = 'No Password'
                    continue

                # Remove any cookies if they exist
                self.driver.delete_all_cookies()

                
                #go to compportal
                self.driver.get("https://commportal.granitevoip.com/#login.html")

                # Make sure the instance is on the default content
                self.driver.switch_to.default_content()

                # Find the login form iframe
                iframe = self.wait.until(EC.visibility_of_element_located((By.ID, 'embedded')))

                # Switch to the iframe
                self.driver.switch_to.frame(iframe)

                # Find and fill in the Number field
                directory_number_field = self.wait.until(EC.visibility_of_element_located((By.ID, 'DirectoryNumberDummy')))
                directory_number_field.send_keys(tn)

                # Find and fill in the password field
                directory_number_field = self.driver.find_element(By.ID, "Password")
                directory_number_field.send_keys(eas_password)

                # Find and click the login button
                self.driver.find_element(By.ID, 'loginSubmit').click()
                
                # Find the new iframe and switch to it
                iframe = self.wait.until(EC.visibility_of_element_located((By.ID, 'iFrameResizer0')))
                self.driver.switch_to.frame(iframe)

                # .find_elements returns a list, so we need to reassign the variable to the first element in the list
                # forward_radio = self.driver.find_elements(By.ID, forward_radio_id)[0]
                forward_radio = self.wait.until(EC.visibility_of_element_located((By.ID, forward_radio_id)))

                if forward_radio.is_displayed():
                    is_forwarding = forward_radio.is_selected()
                    forwarding_destination = None
                    if is_forwarding:
                        # .find_elements returns a list, so we need to reassign the variable to the first element in the list
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

                # Find the radio button for time of day handling and check it
                if call_handler == 'icm':
                    if self.driver.find_element(By.ID, 'summaryRadioSchedules').is_displayed():
                        is_using_schedule = self.driver.find_element(By.ID, 'summaryRadioSchedules').is_selected()
                    else:
                        is_using_schedule = False
                else:
                    is_using_schedule = False

                status = 'Neither'
                if is_using_schedule:
                    status = 'Using Schedule'
                elif is_forwarding:
                    status = 'Forwarding to ' + forwarding_destination


                results_container[tn] = status
            except Exception as e:
                # Log any exceptions
                print(f'Error auditing {tn}: {e}')
                results_container[tn] = 'Error'
                traceback.print_exc()
                continue

        # Write the results container to a csv file, column 1 will be the key, column 2 will be the value
        with open('results.csv', 'w') as f:
            for key in results_container.keys():
                f.write("%s,%s\n"%(key,results_container[key]))

        # Send the results with email
        send_results()


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


