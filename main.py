"""
Script:     main.py
Project:    Smart Cabinet
Author:     Mohamed Martini
Version:    0.0 - Needs Testing
Purpose:    Run Smart Cabinet Inventory Application
"""
import json
import pickle
import schedule
import socket
from time import time, sleep
from datetime import datetime
import RPi.GPIO as GPIO
from pi_server import PiServer
from rfid_reader import RFIDReader
from id_scanner import RFIDSerial, IDScanner, RFIDBuzzer, RFIDLed
import threading

# Local directory where the Admin, Inventory, and Students files exist
ADMINS_PATH = r"/home/pi/Desktop/Smart Cabinet/local/admin.json"
INVENTORY_PATH = r"/home/pi/Desktop/Smart Cabinet/local/inventory.json"
STUDENTS_PATH = r"/home/pi/Desktop/Smart Cabinet/local/students.json"
LOCAL_LOG_PATH = r"/home/pi/Desktop/Smart Cabinet/local/log.pickle"

# TODO: CONSIDER AUOTOMATIC PORT FINDING
PORT_RFID = r"tmr:///dev/ttyACM0"
PORT_READER = "/dev/ttyACM1"

MAX_LOG_LENGTH = 1000

LOCK_PIN = 17
DOOR_PIN = 18
OPEN_TIMEOUT = 5  # Open door before 5 seconds pass
CLOSE_TIMEOUT = 60  # Close door before 1 minute passes


def online():
    # Function to know whether there is internet connection.
    # Thanks to miraculixx:
    # https://stackoverflow.com/questions/20913411/test-if-an-internet-connection-is-present-in-python/20913928
    # TODO: Test on RPi
    try:
        host = socket.gethostbyname("one.one.one.one")
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except socket.gaierror:
        return False


def setup_pi():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.LOW)  # Low: Lock. High: Unlock Door
    GPIO.setup(DOOR_PIN, GPIO.IN)  # High when door is closed. Low if door opens.


class SmartCabinet:
    ADMINS = {}
    INVENTORY = {}  # Complete inventory; key = tag number; value = string identifier
    STUDENTS = {}
    existing_inventory = set()  # Set of existing inventory items

    id_reader = RFIDSerial(PORT_READER)  # ID scanner object
    reader = RFIDReader(PORT_RFID)  # Connect to Inventory RFID Reader

    server = PiServer(reader, id_reader)  # Create server for Admin App communication. Pass in RFID reader.

    client = None  # Google client to handle posting to google spreadsheets.
    admin = False
    LOCAL = False  # To flag whether data was saved locally

    IDLE = False  # Flag to signify when Cabinet is idle, so Syncing from ACCESS sheet can take place

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
        self.update_local_objects()
        self.normal_operation()

    def normal_operation(self):
        # Read Scanned ID's. Local objects should be up-to-date. If ADMINS are not added yet,
        # Go into Admin Routine to allow user to add Admins. Admins then hold their ID to enter
        # Admin Routine and perform Admin functions
        if not self.ADMINS:
            self.admin_routine()

        SYNC_THREAD = threading.Thread(target=self.sync_with_online)
        SYNC_THREAD.start()

        while True:
            if self.LOCAL and online():
                # If files were saved locally, and there is internet connection,
                # upload local log, and delete it. Reset LOCAL to False.
                self.id_reader.set_color(RFIDLed.RED)
                self.upload_local_log()
                continue

            self.IDLE = True
            self.id_reader.set_color(RFIDLed.AMBER)  # SAM: LED Orange.
            id_num = self.id_reader.read_card()  # SAM: Scan ID.
            if not id_num:
                continue

            try:
                # Check if scanned ID is Admin. If so, set admin variable
                self.ADMINS[id_num]
                self.admin = True
            except KeyError:
                self.admin = False
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
            if self.admin:
                sleep(1)  # TODO: Optimize Later
                self.id_reader.serial.timeout = 0.1  # SAM: Set ID Scanner Timeout as 0.1
                hold = id_num == self.id_reader.read_card()
                self.id_reader.serial.timeout = 60

                if hold:
                    self.admin_routine()
                    while not DOOR_PIN:
                        continue
                    self.lock()
                    self.id_reader.set_beep(RFIDBuzzer.ONE)
                    continue

            use = self.handle_user()
            # Only get here when door is closed back
            if use:
                # If the Cabinet was used, update the log
                # Indicate with LED and beep when done
                self.id_reader.set_color(RFIDLed.RED)

                log_thread = threading.Thread(target=lambda: self.update_log(id_num))
                log_thread.start()
                # self.update_log(id_num)
                # self.id_reader.set_beep(RFIDBuzzer.ONE)

    def update_local_objects(self):
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
            with open(INVENTORY_PATH, "r") as f:
                self.INVENTORY = json.load(f)
        except FileNotFoundError:
            with open(INVENTORY_PATH, "w") as f:
                json.dump(self.INVENTORY, f, indent=4)
        try:
            with open(STUDENTS_PATH, "r") as f:
                self.STUDENTS = json.load(f)
        except FileNotFoundError:
            with open(STUDENTS_PATH, "w") as f:
                json.dump(self.STUDENTS, f, indent=4)

        self.existing_inventory = self.reader.scan()

    def admin_routine(self):
        self.IDLE = False
        # First, make sure there is internet connection. (Beep if connected)
        # Unlock door, then get into Admin Routine. Only return when a "done" command is received,
        # at which point we update local objects.
        #  Block until door is closed at the end, then lock door and return
        if not online():
            return
        self.id_reader.set_beep(RFIDBuzzer.ONE)
        self.unlock()
        self.server.admin_routine()
        self.update_local_objects()

    def unlock(self):
        self.id_reader.set_beep(RFIDBuzzer.ONE)
        self.id_reader.set_color(RFIDLed.GREEN)
        GPIO.output(LOCK_PIN, GPIO.HIGH)

    @staticmethod
    def lock():
        GPIO.output(LOCK_PIN, GPIO.LOW)

    def handle_user(self):
        # Unlock door, monitor door, if door does not open before timeout, lock back and return
        # timeout 5 seconds. If door opens: if user is admin, wait for door to close. Else: wait for either
        # the door to close, or for a timeout to pass.
        t = time()
        while GPIO.input(DOOR_PIN) and (time() - t) < OPEN_TIMEOUT:
            # While door is still closed
            pass
        # If timeout
        if GPIO.input(DOOR_PIN):
            self.lock()
            return False
        # Only get here when Door is open
        # Camera ON, Monitor Door
        # TODO: KHALED: Start Camera Recording
        # If it is an admin, do not check if door is left open
        # This allows admin to keep door open through lab time.
        t = time()
        while (not self.admin and not GPIO.input(DOOR_PIN) and
               (time() - t < CLOSE_TIMEOUT)) or (self.admin and not GPIO.input(DOOR_PIN)):
            # Block while door is open
            sleep(0.5)  # TODO: Optimize Later
            continue
        if not GPIO.input(DOOR_PIN):
            self.alarm()
        return True

    def alarm(self):
        # Notify Admins, Block until the door is closed, then lock the door and proceed normally.
        # TODO: DISCUSS NOTIFICATION MEANS
        while not GPIO.input(DOOR_PIN):
            self.id_reader.set_beep(RFIDBuzzer.FIVE)  # SAM: Beep
            sleep(1)
        self.lock()

    def update_log(self, id_num):
        # Only get here when user has used the Cabinet (opened door, then closed door)
        # Scan inventory and handle tickets. XOR between two sets returns the different items.
        # Finally, update the existing_inventory variable
        new_inventory = self.reader.scan()
        different_tags = list(new_inventory ^ self.existing_inventory)
        if not different_tags:
            return

        timestamp = datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
        name = self.ADMINS[id_num] if self.admin else self.STUDENTS[id_num]  # borrower name
        data = {}  # {"24" : [["John Doe", "1238768912", "borrow", "<timestamp>"]], etc.}
        for tag in different_tags:
            # in case more than one box was borrows/returned
            # TODO: Prepare all data "[[]]", and then either save them at once to spreadsheet, or
            #  Save them locally
            box_name = sheet_name = self.INVENTORY.get(tag) or tag  # In case a foreign RFID is found
            action = "borrowed" if tag in self.existing_inventory else "returned"
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

        self.existing_inventory = new_inventory

    def local_save(self, data):
        # If file does not exist, create it. If it exists, load it, append to it, dump it back.
        self.LOCAL = True  # Local variable to flag when there is a local log
        try:
            with open(LOCAL_LOG_PATH, "rb") as file:
                log = pickle.load(file)
        except FileNotFoundError:
            log = {}
        for box_name, row in data.items():
            if log.get(box_name):
                log[box_name].extend(row)
            else:
                log[box_name] = row
        with open(LOCAL_LOG_PATH, "wb") as file:
            pickle.dump(log, file)

    def upload_local_log(self):
        # Get contents of local log, post contents to spreadsheet, empty local log
        with open(LOCAL_LOG_PATH, "rb") as file:
            log = pickle.load(file)

        for box_name, rows in log.items():
            worksheet = self.server.LOG.worksheet(box_name)
            num = len(rows)
            worksheet.delete_dimension("ROWS", start_index=MAX_LOG_LENGTH - num + 1, end_index=MAX_LOG_LENGTH)
            worksheet.insert_rows(rows, 2)

        with open(LOCAL_LOG_PATH, "wb") as file:
            pickle.dump({}, file)

        self.LOCAL = False

    def sync_with_online(self):
        # If the json files are open somewhere else, return
        worksheets = ("ADMINS", "STUDENTS", "INVENTORY")
        local_access = (ADMINS_PATH, STUDENTS_PATH, INVENTORY_PATH)
        while True:
            if not self.IDLE or not online() or not self.server.ACCESS:
                sleep(5)
                continue

            for worksheet, json_path in zip(worksheets, local_access):
                try:
                    worksheet = self.server.ACCESS.worksheet(worksheet)
                except:
                    sleep(1)
                    continue
                # List of Dictionaries, e.g.
                # [{"Admin" : "John", "RFID": "192837"}, {"Admin" : "Jack", "RFID" : 912382}]
                data = worksheet.get_all_records()
                if not data:
                    sleep(5)
                    continue

                file_to_be = {list(d.values())[1]: list(d.values())[0] for d in data}
                with open(json_path, "w") as f:
                    json.dump(file_to_be, f, indent=4)

            self.update_local_objects()
            sleep(60)


if __name__ == '__main__':
    # Wait for the door to be closed
    setup_pi()
    while not GPIO.input(DOOR_PIN):
        sleep(0.5)
    sleep(0.5)
    GPIO.output(LOCK_PIN, GPIO.LOW)
    SmartCabinet()
