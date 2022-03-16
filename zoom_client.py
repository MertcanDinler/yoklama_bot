from concurrent.futures import thread
from enum import Enum
from operator import le
from time import sleep
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from config import DRIVER_CACHE_PATH
import logging
import threading
from participant import Participant

logger = logging.getLogger(__name__)


class Status(Enum):
    initial = 0
    not_started = 1
    waiting_room = 2
    started = 3
    joined = 4
    meeting_end = 5


class ZoomClientError(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)


class ZoomClient(object):
    __driver: Chrome = None
    __meeting_id: int = None
    __status: int = None
    __participants: "list[Participant]" = []
    __old_participants_els: list = []
    __last_id: int = 0
    __threads: "list[threading.Thread]" = []
    __funcs = {}

    def __init__(self) -> None:
        self.__funcs = {
            Status.initial: None,
            Status.not_started: None,
            Status.waiting_room: None,
            Status.started: None,
            Status.joined: self.__on_meeting_joined,
            Status.meeting_end: None
        }
        self.__init_driver()

    def __init_driver(self) -> None:
        chrome_driver_manager = ChromeDriverManager(path=DRIVER_CACHE_PATH)
        service = Service(chrome_driver_manager.install())

        options = ChromeOptions()
        # options.headless = True
        options.add_argument("--lang=en")
        # options.add_argument("--disable-gpu")
        options.add_argument("--mute-audio")
        options.add_argument("--start-maximized")
        options.add_experimental_option(
            'excludeSwitches', ['enable-logging', "enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        self.__driver = Chrome(
            service=service, options=options, service_log_path="NUL")

    def __check_meeting_state(self):
        errors = self.__driver.find_elements_by_css_selector(
            "span.error-message")
        if len(errors) > 0:
            raise ZoomClientError(errors[0].text)

        if self.__status in [Status.waiting_room]:
            elements = self.__driver.find_elements_by_class_name(
                "zm-modal-body-title")
            if len(elements) > 0 and "ended by host" in elements[0].text:
                # TODO
                print("meeting end")
                return Status.meeting_end
            # elements = WebDriverWait(self.__driver, 2).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "join-audio-container__btn")))
            elements = self.__driver.find_elements_by_class_name(
                "join-audio-container__btn")
            if len(elements) > 0:
                print("joined")
                return Status.joined

        # Meeting not started
        elements = self.__driver.find_elements_by_id("prompt")
        if len(elements) > 0:
            if "has not started" in elements[0].text.lower():
                print("not started")
                return Status.not_started

        elements = self.__driver.find_elements_by_class_name(
            "wr-default__text")
        if len(elements) > 0 and "host will let" in elements[0].text.lower():
            print("waiting room")
            return Status.waiting_room

    def __set_meeting_status(self, status: Status):
        func = self.__funcs.get(status)
        if callable(func):
            func()
        self.__status = status

    def join_meeting(self, meeting_id: str, password: str) -> None:
        meeting_id = meeting_id.replace(" ", "")
        url = "https://zoom.us/wc/join/{}".format(meeting_id)
        self.__driver.get(url)

        cookie_dialog = WebDriverWait(self.__driver, 15, poll_frequency=2).until(
            EC.visibility_of_all_elements_located((By.ID, "onetrust-accept-btn-handler")))
        if len(cookie_dialog) > 0:
            cookie_dialog[0].click()

        WebDriverWait(self.__driver, 10, poll_frequency=2).until(
            EC.visibility_of_element_located((By.ID, "inputname")))
        self.__driver.find_element_by_id("inputname").send_keys("YoklamaBot")
        self.__driver.find_element_by_id("joinBtn").click()

        self.__set_meeting_status(self.__check_meeting_state())

        while self.__status == Status.not_started:
            self.__set_meeting_status(self.__check_meeting_state())
            sleep(5)

        a = WebDriverWait(self.__driver, 180, poll_frequency=2).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input#inputpasscode")))
        a.send_keys(password)
        # self.__driver.find_element_by_id(
        #         "inputpasscode").send_keys(password)
        self.__driver.find_element_by_id("joinBtn").click()

        # wr-default__text
        # Please wait, the meeting host will let you in soon.
        # .wr-leave-btn
        # .footer__leave-btn-container

        WebDriverWait(self.__driver, 180).until(lambda driver: driver.find_element_by_class_name(
            "wr-leave-btn") or driver.find_element_by_class_name("footer__leave-btn-container"))
        #WebDriverWait(self.__driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".wr-leave-btn, .element_B_class")))
        self.__set_meeting_status(self.__check_meeting_state())

        while self.__status == Status.waiting_room:
            self.__set_meeting_status(self.__check_meeting_state())
            sleep(5)

    def __check_participants(self, is_first_run=False):
        el = self.__driver.find_elements_by_class_name("show-participants")
        if len(el) <= 0:
            el = self.__driver.find_element_by_xpath(
                '//*[@id="foot-bar"]/div[2]/div[1]/button')
            self.__driver.execute_script("arguments[0].click();", el)

        participant_elements = self.__driver.find_elements_by_class_name(
            "participants-li")
        for element in participant_elements:
            md_id = element.get_attribute("md_id")
            if md_id == None:
                self.__on_new_participant(element)
            else:
                participant = self.__participants[int(md_id)]
                self.__check_name_changes(participant, element)
        for participant in self.__participants:
            elements = self.__driver.find_elements_by_xpath(
                '//li[@md_id={}]'.format(participant.id))
            if len(elements) <= 0:
                print(participant.name, "çıktı")

    def __on_new_participant(self, element):
        md_id = self.__last_id
        self.__driver.execute_script(
            "arguments[0].setAttribute('md_id',arguments[1])", element, md_id)
        name = element.find_element_by_class_name(
            "participants-item__display-name").text
        participant = Participant(md_id, name)
        self.__participants.append(participant)
        self.__last_id += 1

    def __check_name_changes(self, participant, element):
        name = element.find_element_by_class_name(
            "participants-item__display-name").text
        if participant.name != name:
            print("isim değişti", name, participant.name)
            participant.name = name

    def __on_meeting_joined(self):
        def task():
            while True:
                self.__check_participants()
                sleep(5)
        thread = threading.Thread(target=task)
        thread.start()
        self.__threads.append(thread)

    def loop(self):
        for thread in self.__threads:
            thread.join()

    def close(self) -> None:
        self.__driver.close()
