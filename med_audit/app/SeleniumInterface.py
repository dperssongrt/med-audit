from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import os


class SeleniumInterfaceBase:
    def __init__(self):
        BASE_PATH = os.path.join(os.getcwd())
        self.driver = None
        # Configure the firefox options
        options = Options()
        options.add_argument('-private')
        options.add_argument("--headless")
        options.set_preference('dom.webnotifications.enabled', False)
        options.set_preference('browser.cache.disk.enable', False)
        options.set_preference('browser.cache.memory.enable', False)
        options.set_preference('browser.cache.offline.enable', False)
        options.set_preference('network.cookie.cookieBehavior', 2)
        options.set_preference('network.http.pipelining', True)
        options.set_preference('network.dns.disableIPv6', True)
        options.set_preference('network.prefetch-next', True)
        options.set_preference("devtools.chrome.enabled", True)
        options.set_preference("devtools.debugger.remote-enabled", True)
        options.set_preference("devtools.debugger.prompt-connection", False)

        if os.getenv('TED_ENV', None):
            if 'keegan' in os.getenv('TED_ENV'):
                driver_path = os.path.join(BASE_PATH, 'geckodriver_mac_m1')
            elif 'dpersson' in os.getenv('TED_ENV'):
                driver_path = os.path.join(BASE_PATH, 'geckodriver')
        else:
            driver_path = os.path.join(BASE_PATH, 'geckodriver_linux')

        service = Service(driver_path)
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.implicitly_wait(10)  # seconds

    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.close()

    def run(self, *args, **kwargs):
        raise NotImplementedError("You must implement your own run method")
