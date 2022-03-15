from enum import Enum
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from config import DRIVER_CACHE_PATH


class Status(Enum):
    not_started = 0
    waiting_room = 1
    started = 2


class ZoomClientError(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)


class ZoomClient(object):
    __driver: Chrome = None
    __meeting_id: int = None
    __status: int = None

    def __init__(self) -> None:
        self.__init_driver()

    def __init_driver(self) -> None:
        chrome_driver_manager = ChromeDriverManager(path=DRIVER_CACHE_PATH)
        service = Service(chrome_driver_manager.install())

        options = ChromeOptions()
        # options.headless = True
        options.add_argument("--lang=en")
        # options.add_argument("--disable-gpu")
        options.add_argument("--mute-audio")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        self.__driver = Chrome(
            service=service, options=options, service_log_path="NUL")

    def __check_meeting_state(self):
        errors = self.__driver.find_elements_by_css_selector(
            "span.error-message")
        if len(errors) > 0:
            raise ZoomClientError(errors[0].text)

        # Meeting not started
        elements = self.__driver.find_elements_by_css_selector("div#prompt")
        if len(elements) > 0:
            if "has not started" in elements[0].text.lower():
                return Status.not_started

    def __set_meeting_status(self, status: Status):
        self.__status = status

    def join_meeting(self, meeting_id: str, password: str) -> None:
        meeting_id = meeting_id.replace(" ", "")
        url = "https://zoom.us/wc/join/{}".format(meeting_id)
        self.__driver.get(url)

        WebDriverWait(self.__driver, 15, poll_frequency=2).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "button#onetrust-accept-btn-handler")))
        cookie_dialog = self.__driver.find_elements_by_css_selector(
            "button#onetrust-accept-btn-handler")
        if len(cookie_dialog) > 0:
            cookie_dialog[0].click()

        WebDriverWait(self.__driver, 10, poll_frequency=2).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input#inputname")))
        self.__driver.find_element_by_id("inputname").send_keys("YoklamaBot")
        self.__driver.find_element_by_id("joinBtn").click()

        self.__set_meeting_status(self.__check_meeting_state())

        if self.__status == Status.not_started:
            WebDriverWait(self.__driver, 180, poll_frequency=2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input#inputpasscode")))
            self.__driver.find_element_by_id(
                "inputpasscode").send_keys(password)
            self.__driver.find_element_by_id("joinBtn").click()

        # wr-default__text
        # Please wait, the meeting host will let you in soon.
        # wr-leave-btn

        return
        self.__driver.find_element_by_id("inputpasscode").send_keys(password)
        self.__driver.find_element_by_id("joinBtn").click()

    def close(self) -> None:
        self.__driver.close()
