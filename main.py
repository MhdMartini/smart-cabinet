"""
Script:     main.py
Project:    Smart Cabinet
Author:     Mohamed Martini
Version:    0.9 - Completely Functional. Offline mode to be tested
Purpose:    Run Smart Cabinet Inventory Application
"""
import json
import pickle
import socket
from time import time, sleep
from datetime import datetime
import RPi.GPIO as GPIO
from pi_server import PiServer
from rfid_reader import RFIDReader
from id_scanner import RFIDSerial, RFIDBuzzer, RFIDLed
import threading
import serial.tools.list_ports
import atexit


# Local directory where the Admin, Inventory, and Students files exist
ADMINS_PATH = r"/home/pi/Desktop/Smart_Cabinet/admin.json"
INVENTORY_PATH = r"/home/pi/Desktop/Smart_Cabinet/inventory.json"
STUDENTS_PATH = r"/home/pi/Desktop/Smart_Cabinet/students.json"
LOCAL_LOG_PATH = r"/home/pi/Desktop/Smart_Cabinet/log.pickle"

# PORT_RFID = r"tmr:///dev/ttyACM1"
# PORT_READER = r"/dev/ttyACM0"

MAX_LOG_LENGTH = 1000

LOCK_PIN = 17
DOOR_PIN_LEFT = 27
DOOR_PIN_RIGHT = 26

OPEN_TIMEOUT = 5  # Open door before 5 seconds pass
CLOSE_TIMEOUT = 20  # Close door before 1 minute passes
SYNC_FREQ = 60  # Frequency of syncing with SC Access spreadsheet
LOCAL_CHECK_INTERVAL = 60


def online():
    # Function to know whether there is internet connection.
    # Thanks to miraculixx:
    # https://stackoverflow.com/questions/20913411/test-if-an-internet-connection-is-present-in-python/20913928
    try:
        host = socket.gethostbyname("one.one.one.one")
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except socket.gaierror:
        return False


def setup_pi():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Low: Unlock. High: Lock
    GPIO.setup(DOOR_PIN_LEFT, GPIO.IN)  # High when door is closed. Low if door is open.
    GPIO.setup(DOOR_PIN_RIGHT, GPIO.IN)  # High when door is closed. Low if door is open.


class SmartCabinet:
    ADMINS = {}
    INVENTORY = {}  # Complete inventory; key = tag number; value = string identifier
    STUDENTS = {}
    existing_inventory = set()  # Set of existing inventory items

    # reader = RFIDReader(PORT_RFID)  # Connect to Inventory RFID Reader
    # id_reader = RFIDSerial(PORT_READER)  # ID scanner object
    reader = None  # Inventory RFID Reader object
    id_reader = None  # ID scanner object

    admin = False  # True when Admin scans ID
    LOCAL = False  # To flag whether log data was saved locally

    IDLE = False  # Flag to signify when Cabinet is idle, so Syncing from Access sheet can take place

    def __init__(self):
        # On boot-up, launch google client, then update the local objects according to the local files
        # and RFID inventory scan.
        # Local files include the Admins list, allowed Students, and Complete Inventory items (Not current)
        # Local files and objects are dictionary-type data structures, where the key is
        # the RFID number, and the value is a human-readable identifier of that number.
        # E.g. {"2378682234" : "John Doe"}
        # If local files do not exist, create empty local files.
        # Local files will then be filled by using the Admin Application on a device on the same wifi as
        # the Cabinet, which will be handled by the admin_routine.
        # Block until door is closed. Lock the door and begin.
        # This ensures the Cabinet state is the same everytime program starts.
        self.get_ports()

        # Create server for Admin App communication. Pass in RFID reader.
        self.id_reader.set_color(RFIDLed.RED)
        self.server = PiServer(self.reader, self.id_reader)
        atexit.register(self.exit_handler)

        self.update_access_objects()
        self.normal_operation()

    def exit_handler(self):
        GPIO.cleanup()

    def check_if_local(self):
        while True:
            if online() and self.IDLE:
                # If files were saved locally, and there is internet connection,
                # upload local log, and delete it. Reset LOCAL to False.
                self.upload_local_log()
                break
            sleep(LOCAL_CHECK_INTERVAL)

    def normal_operation(self):
        # Read Scanned ID's. Local objects should be up-to-date. If ADMINS are not added yet,
        # Go into Admin Routine to allow user to add Admins. Admins then hold their ID to enter
        # Admin Routine and perform Admin functions
        while not self.ADMINS:
            # Stay in Admin Routine until an Admin is added
            self.admin_routine(persistent=True)

        # Get items in cabinet
        self.update_inventory()

        # Threads to constantly sync with online UI and check if there is local log to upload
        ONLINE_SYNC_THREAD = threading.Thread(target=self.sync_with_online)
        ONLINE_SYNC_THREAD.start()

        self.id_reader.set_beep(RFIDBuzzer.TWO)
        while True:
            self.IDLE = True
            self.admin = False

            self.id_reader.set_color(RFIDLed.AMBER)  # SAM: LED Orange.
            id_num = self.id_reader.read_card()  # SAM: Scan ID.
            self.IDLE = False

            try:
                # Check if scanned ID is Admin. If so, set admin variable
                self.ADMINS[id_num]
                self.admin = True
            except KeyError:
                try:
                    # If NOT Admin, Check if scanned ID is Student
                    self.STUDENTS[id_num]
                except KeyError:
                    # If scanned ID is neither Admin or Student
                    self.id_reader.set_color(RFIDLed.RED)  # SAM: LED Red.
                    sleep(1)
                    continue

            # Only get here when valid ID is scanned
            self.unlock()
            self.id_reader.set_beep(RFIDBuzzer.TWO)
            if self.admin:
                sleep(1.25)
                self.id_reader.serial.timeout = 0.1  # SAM: Set ID Scanner Timeout as 0.1
                hold = True if self.id_reader.serial.read() else False

                if hold:
                    self.admin_routine()
                    while self.door_open():
                        # Hold until they close the door
                        sleep(1)
                        continue

                    self.lock()
                    self.id_reader.set_beep(RFIDBuzzer.TWO)
                    # Update the log in case students added AND items borrowed
                    log_thread = threading.Thread(target=lambda: self.update_log(id_num))
                    log_thread.start()
                    continue

            use = self.handle_user()
            # Only get here when door is closed back
            if use:
                # If the Cabinet was used, create a thread to update the log
                log_thread = threading.Thread(target=lambda: self.update_log(id_num))
                log_thread.start()

    def update_access_objects(self):
        # Update ADMIN, INVENTORY, and STUDENTS from json files. If a file does not exist, create it.
        # Finally, update existing_inventory by performing an inventory_scan
        # files = (ADMINS_PATH, INVENTORY_PATH, STUDENTS_PATH)
        # dicts = [self.ADMINS, self.INVENTORY, self.STUDENTS]
        try:
            with open(ADMINS_PATH, "r") as f:
                self.ADMINS = json.load(f)
        except FileNotFoundError:
            with open(ADMINS_PATH, "w") as f:
                json.dump(self.ADMINS, f, indent=4)

        try:
            with open(STUDENTS_PATH, "r") as f:
                self.STUDENTS = json.load(f)
        except FileNotFoundError:
            with open(STUDENTS_PATH, "w") as f:
                json.dump(self.STUDENTS, f, indent=4)

        try:
            with open(INVENTORY_PATH, "r") as f:
                self.INVENTORY = json.load(f)
        except FileNotFoundError:
            with open(INVENTORY_PATH, "w") as f:
                json.dump(self.INVENTORY, f, indent=4)

    def update_inventory(self):
        self.existing_inventory = self.reader.scan()

    def admin_routine(self, persistent=False):
        self.IDLE = False
        # First, make sure there is internet connection. (Beep if connected)
        # Unlock door, then get into Admin Routine. Only return when a "done" command is received,
        # at which point we update local objects.
        # Block until door is closed at the end, then lock door and return
        # Persistent only True when no admin is found. App stays in Admin Routine persistently until an Admin is added
        # Without an admin, Admin Routine cannot be accessed
        if not online():
            self.id_reader.set_color(RFIDLed.RED)
            sleep(0.5)
            return
        self.unlock()

        if persistent:
            # Five buzzes when no admin, otherwise three buzzes
            # Either way Red LED
            self.id_reader.set_beep(RFIDBuzzer.FIVE)
        else:
            self.id_reader.set_beep(RFIDBuzzer.THREE)
        self.id_reader.set_color(RFIDLed.GREEN)

        self.server.admin_routine(persistent=persistent)

        # When out of Admin Routine update local access objects
        self.update_access_objects()

    def unlock(self):
        self.id_reader.set_beep(RFIDBuzzer.ONE)
        self.id_reader.set_color(RFIDLed.GREEN)
        GPIO.output(LOCK_PIN, GPIO.LOW)

    def lock(self):
        sleep(0.5)
        self.id_reader.set_beep(RFIDBuzzer.ONE)
        GPIO.output(LOCK_PIN, GPIO.HIGH)

    @staticmethod
    def door_open():
        sleep(0.1)
        status = not GPIO.input(DOOR_PIN_LEFT) or not GPIO.input(DOOR_PIN_RIGHT)
        return status

    @staticmethod
    def door_closed():
        sleep(0.1)
        return GPIO.input(DOOR_PIN_LEFT) and GPIO.input(DOOR_PIN_RIGHT)

    @staticmethod
    def timer_expired(t, timeout):
        return time() - t > timeout

    def handle_user(self):
        # Unlock door, monitor door, if door does not open before timeout, lock back and return
        # timeout 5 seconds. If door opens: if user is admin, wait for door to close. Else: wait for either
        # the door to close, or for a timeout to pass.

        t = time()
        while self.door_closed() and not self.timer_expired(t, OPEN_TIMEOUT):
            # While door is still closed
            sleep(1)
            continue
        if self.door_closed():
            # If door never opened
            self.lock()
            return False
        # Only get here when Door is open
        # Monitor Door
        # If it is an admin, do not check if door is left open
        # This allows admin to keep door open through lab time.
        t = time()
        while (not self.admin and self.door_open() and
               not self.timer_expired(t, CLOSE_TIMEOUT)) or (self.admin and self.door_open()):
            # Block while door is closed
            sleep(1)
            continue
        if self.door_open():
            self.alarm()

        self.lock()
        return True

    def alarm(self):
        # Notify Admins, Block until the door is closed, then lock the door and proceed normally.
        while self.door_open():
            self.id_reader.set_beep(RFIDBuzzer.ONE)
            sleep(1)

    def update_log(self, id_num):
        # Only get here when user has used the Cabinet (opened door, then closed door)
        # Scan inventory and handle tickets. XOR between two sets returns the different items.
        # Finally, update the existing_inventory variable
        new_inventory = self.reader.scan()
        different_tags = list(new_inventory ^ self.existing_inventory)
        if not different_tags:
            return

        timestamp = datetime.now().strftime("%B-%d-%A_%Y-%H:%M:%S")
        name = self.ADMINS.get(id_num) if self.admin else self.STUDENTS.get(id_num)  # borrower name
        data = {}  # {"24" : [["John Doe", "1238768912", "borrow", "<timestamp>"]], etc.}
        for tag in different_tags:
            # in case more than one box was borrows/returned
            # TODO: Prepare all data "[[]]", and then either save them at once to spreadsheet, or
            #  Save them locally
            box_name = sheet_name = self.INVENTORY.get(tag)  # In case a foreign RFID is found
            if not box_name:
                # ignore non added items
                continue
            action = "borrowed" if tag in self.existing_inventory else "added" if not name else "returned"
            row = [[name, id_num, action, timestamp]]
            data[box_name] = row
        if not online():
            # Append box number to user record
            self.local_save(data)
            return

        for box_name, row in data.items():
            worksheet = self.server.LOG.worksheet(box_name)
            worksheet.delete_rows(MAX_LOG_LENGTH)
            worksheet.insert_rows(row, 2)
            sleep(0.5)

        self.existing_inventory = new_inventory

    def local_save(self, data):
        # If file does not exist, create it. If it exists, load it, append to it, dump it back.
        try:
            with open(LOCAL_LOG_PATH, "rb") as file:
                log = pickle.load(file)
        except FileNotFoundError:
            log = {}
        for box_name, row in data.items():
            try:
                log[box_name].extend(row)
            except KeyError:
                log[box_name] = row

        with open(LOCAL_LOG_PATH, "wb") as file:
            pickle.dump(log, file)

        LOCAL_SAVE_THREAD = threading.Thread(target=self.check_if_local)
        LOCAL_SAVE_THREAD.start()

    def upload_local_log(self):
        # Get contents of local log, post contents to spreadsheet, empty local log
        self.id_reader.set_color(RFIDLed.RED)
        self.server.launch_google_client()

        with open(LOCAL_LOG_PATH, "rb") as file:
            log = pickle.load(file)

        for box_name, rows in log.items():
            worksheet = self.server.LOG.worksheet(box_name)
            num = len(rows)
            worksheet.delete_dimension("ROWS", start_index=MAX_LOG_LENGTH - num + 1, end_index=MAX_LOG_LENGTH)
            worksheet.insert_rows(rows, 2)
            sleep(0.5)

        with open(LOCAL_LOG_PATH, "wb") as file:
            pickle.dump({}, file)

    def sync_with_online(self):
        # Update local objects and json files according to online records if different
        while not online():
            sleep(10)
            continue
        admins_sheet = self.server.ACCESS.worksheet("ADMINS")
        students_sheet = self.server.ACCESS.worksheet("STUDENTS")

        while True:
            sleep(SYNC_FREQ)
            if not self.IDLE or not online():
                continue

            # Get the online records, compare to local objects and update if needed
            # data format example:
            # [{"Name" : "John Doe", "RFID": "127892", "ACCESS" : ""},
            # {"Name" : "Jane Doe", "RFID": "127892", "ACCESS" : ""}]
            change = False  # To indicate if a record was changed so that we update local access objects
            data = admins_sheet.get_all_records()
            admins_file = {}
            for d in data:
                if d["ACCESS"].lower() != "no":
                    values = list(d.values())
                    admins_file[values[1]] = values[0]
            if admins_file != self.ADMINS:
                change = True
                while not self.IDLE:
                    # If not Idle, don't proceed
                    sleep(10)
                    continue
                self.ADMINS = admins_file
                with open(ADMINS_PATH, "w") as f:
                    json.dump(self.ADMINS, f, indent=4)

            data = students_sheet.get_all_records()
            students_file = {}
            for d in data:
                if d["ACCESS"].lower() != "no":
                    values = list(d.values())
                    students_file[values[1]] = values[0]
            if students_file != self.STUDENTS:
                change = True
                while not self.IDLE:
                    # If not Idle, don't proceed
                    sleep(10)
                    continue
                self.STUDENTS = students_file
                with open(STUDENTS_PATH, "w") as f:
                    json.dump(self.STUDENTS, f, indent=4)

            if change:
                self.update_access_objects()

    def get_ports(self):
        # Connect to RFID Inventory reader first, then connect to ID Scanner
        rfid_prefix = r"tmr://"
        ports = []
        ports_obj = serial.tools.list_ports.comports()
        for port_obj in ports_obj:
            port = str(port_obj).split(" - ")[0]
            if port == r"/dev/ttyAMA0":
                continue
            ports.append(port)

        # TODO: Optimize Later
        try:
            self.reader = RFIDReader(rfid_prefix + ports[0])  # Connect to Inventory RFID Reader
            del (ports[0])
        except serial.serialutil.SerialException:
            self.reader = RFIDReader(rfid_prefix + ports[1])
            del (ports[1])

        self.id_reader = RFIDSerial(ports[0])  # ID scanner object


if __name__ == '__main__':
    # Wait for the door to be closed
    try:
        setup_pi()

        while not GPIO.input(DOOR_PIN_LEFT) or not GPIO.input(DOOR_PIN_RIGHT):
            sleep(1)
            print("waiting for door to close")
        sleep(0.5)
        SmartCabinet()
    except KeyboardInterrupt:
        GPIO.cleanup()
