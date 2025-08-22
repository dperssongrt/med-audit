from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import os


class SeleniumInterfaceBase:
    def __init__(self):
        BASE_PATH = os.path.join(os.getcwd())
        self.driver = None
        # Tab management for MetaView Web workflow
        self.tab_handles = {}  # {tab_id: window_handle}
        self.main_tab_handle = None
        self.current_tab_id = "main"
        self.tab_cleanup_counter = 0
        # Configure the firefox options
        options = Options()
        options.add_argument('-private')
        options.add_argument("--headless")
        # options.set_preference('dom.webnotifications.enabled', False)
        # options.set_preference('browser.cache.disk.enable', False)
        # options.set_preference('browser.cache.memory.enable', False)
        # options.set_preference('browser.cache.offline.enable', False)
        # options.set_preference('network.cookie.cookieBehavior', 2)
        # options.set_preference('network.http.pipelining', True)
        # options.set_preference('network.dns.disableIPv6', True)
        # options.set_preference('network.prefetch-next', True)
        # options.set_preference("devtools.chrome.enabled", True)
        # options.set_preference("devtools.debugger.remote-enabled", True)
        # options.set_preference("devtools.debugger.prompt-connection", False)

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

    def open_new_tab(self, url=None, tab_id=None):
        """Open new tab, store handle, optionally navigate to URL"""
        if not tab_id:
            tab_id = f"tab_{len(self.tab_handles)}"
        
        # Open new tab
        self.driver.execute_script("window.open('');")
        
        # Get all window handles and find the new one
        all_handles = self.driver.window_handles
        new_handle = None
        for handle in all_handles:
            if handle not in self.tab_handles.values():
                new_handle = handle
                break
        
        if new_handle:
            self.tab_handles[tab_id] = new_handle
            self.driver.switch_to.window(new_handle)
            self.current_tab_id = tab_id
            
            if url:
                self.driver.get(url)
            
            return tab_id
        return None

    def switch_to_tab(self, tab_id):
        """Switch driver context to specified tab"""
        if tab_id in self.tab_handles:
            handle = self.tab_handles[tab_id]
            try:
                self.driver.switch_to.window(handle)
                self.current_tab_id = tab_id
                return True
            except Exception as e:
                print(f"Failed to switch to tab {tab_id}: {e}")
                # Remove invalid handle
                del self.tab_handles[tab_id]
                return False
        return False

    def close_tab(self, tab_id):
        """Close tab and remove from tracking"""
        if tab_id in self.tab_handles:
            handle = self.tab_handles[tab_id]
            try:
                # Switch to the tab before closing it
                self.driver.switch_to.window(handle)
                self.driver.close()
                del self.tab_handles[tab_id]
                
                # Switch back to main tab if available
                if "metaview_main" in self.tab_handles:
                    self.switch_to_tab("metaview_main")
                elif self.tab_handles:
                    # Switch to any remaining tab
                    remaining_tab = list(self.tab_handles.keys())[0]
                    self.switch_to_tab(remaining_tab)
                
                return True
            except Exception as e:
                print(f"Failed to close tab {tab_id}: {e}")
                # Remove from tracking even if close failed
                if tab_id in self.tab_handles:
                    del self.tab_handles[tab_id]
                return False
        return False

    def cleanup_subscriber_tabs(self):
        """Close all subscriber tabs, keep main MetaView tab"""
        tabs_to_close = []
        for tab_id in self.tab_handles.keys():
            if tab_id != "metaview_main" and tab_id != "main":
                tabs_to_close.append(tab_id)
        
        for tab_id in tabs_to_close:
            self.close_tab(tab_id)
        
        # Reset cleanup counter
        self.tab_cleanup_counter = 0

    def get_current_tab_count(self):
        """Return number of open tabs for monitoring"""
        return len(self.driver.window_handles)

    def run(self, *args, **kwargs):
        raise NotImplementedError("You must implement your own run method")
