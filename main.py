# TODO: Place "credentials.json" in working directory
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
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import set_row_height, set_column_width

INTRO_SHEET = [
    ["SMART CABINET"],
    ["UNIVERSITY OF MASSACHUSETTS LOWELL"],
    ["FRANCIS COLLEGE OF ENGINEERING"],
    ["ELECTRICAL AND COMPUTER ENGINEERING"],
    ["For software support:"],
    ["mohamed_martini@student.uml.edu"]
]

# Local directory where the Admin, Inventory, and Students files exist
ADMINS_PATH = r"/home/pi/admin.json"
INVENTORY_PATH = r"/home/pi/inventory.json"
STUDENTS_PATH = r"/home/pi/students.json"
LOCAL_LOG_PATH = r"/home/pi/log.pickle"
CREDENTIALS_PATH = r"/home/pi/credentials.json"

# TODO: CONSIDER AUOTOMATIC PORT FINDING
PORT_RFID = r"tmr:///dev/ttyACM0"
PORT_READER = "/dev/ttyACM1"

LOG_FILE = "log"
MAX_LOG_LENGTH = 1000
LOG_COLS = ["user", "RFID", "action", "timestamp"]
USER_GMAIL = "smartcabinet.uml@gmail.com"

# log link: https://docs.google.com/spreadsheets/d/1xFAgsIzERw8PmB9tJRJfL33mBX-WdAvlWdCkUI3zZ1k/edit#gid=820944832

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
    IDScanner.initialize()  # SAM: Create id scanner object. To be used to perform id_scanner functionality

    reader = RFIDReader(PORT_RFID)  # Connect to Inventory RFID Reader
    server = PiServer(reader, id_reader)  # Create server for Admin App communication. Pass in RFID reader.

    client = None  # Google client to handle posting to google spreadsheets.
    admin = False
    LOCAL = False  # To flag whether data was saved locally
    LOG = None  # To hold the log google spreadsheet later

    def __init__(self):
        # On boot-up, configure the Pi, then update the local objects according to the local files
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
        self.launch_google_client()
        self.update_local_objects()
        self.normal_operation()

    def launch_google_client(self):
        # Authorize, and create log spreadsheet if it does not exist
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        self.client = gspread.authorize(credentials)

        try:
            self.LOG = self.client.open(LOG_FILE)
        except gspread.exceptions.SpreadsheetNotFound:
            self.LOG = self.client.create(LOG_FILE)
            self.LOG.share(USER_GMAIL, perm_type='user', role='writer')

            # Create Introductory Sheet in place of default one
            worksheet = self.LOG.add_worksheet(title="SMART CABINET", rows=1, cols=1)
            self.LOG.del_worksheet(self.LOG.sheet1)
            worksheet.insert_rows(INTRO_SHEET, 1)
            set_column_width(worksheet, 'A', 1000)
            set_row_height(worksheet, '1:5', 70)
            worksheet.format("A1:A5", {
                "backgroundColor": {
                    "red": 0,
                    "green": 0,
                    "blue": 0
                },
                "horizontalAlignment": "CENTER",
                "textFormat": {
                    "foregroundColor": {
                        "red": 1,
                        "green": 1,
                        "blue": 1
                    },
                    "fontSize": 30,
                    "bold": True
                }
            })

    def normal_operation(self):
        # Read Scanned ID's. Local objects should be up-to-date. If ADMINS are not added yet,
        # Go into Admin Routine to allow user to add Admins. Admins then hold their ID to enter
        # Admin Routine and perform Admin functions
        if not self.ADMINS:
            self.admin_routine()

        while True:
            if self.LOCAL:
                # If files were saved locally, check for internet connection,
                # If successful, upload local log, and delete it. Reset LOCAL to False.
                if online():
                    self.upload_local_log()

            self.id_reader.set_color(RFIDLed.AMBER)  # SAM: LED Orange.
            try:
                id_num = self.id_reader.read_card()  # SAM: Scan ID.
            except serial.timeout:
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
            if self.admin:
                self.unlock()
                sleep(1)  # TODO: Optimize Later
                self.id_reader.serial.timeout = 0.1  # SAM: Set ID Scanner Timeout as 0.1
                # SAM: Scan ID. Uncomment next line and fill in the scan method
                try:
                    hold = id_num == self.id_reader.read_card()
                except self.rfid.SerialTimeoutException:
                    # TODO: Verify Syntax
                    hold = False
                finally:
                    self.id_reader.serial.timeout = 60

                if hold:
                    self.admin_routine()
                    continue

            use = self.handle_user()
            # Only get here when door is closed back
            if use:
                # If the Cabinet was used, update the log
                # Indicate with LED and beep when done
                self.id_reader.set_color(RFIDLed.RED)
                self.update_log(id_num)
                self.id_reader.set_beep(RFIDBuzzer.ONE)

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
        # First, make sure there is internet connection. (Beep when connected)
        # Unlock door, then get into Admin Routine. Only return when a "done" command is received,
        # at which point we update local objects.
        #  Block until door is closed at the end, then lock door and return
        while not online():
            sleep(1)
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
        self.unlock()
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
        rows = {}  # {"24" : ["John Doe", "1238768912", "borrow", "<timestamp>"], etc.}
        for tag in different_tags:
            # in case more than one box was borrows/returned
            # TODO: Prepare all rows "[[]]", and then either save them at once to spreadsheet, or
            #  Save them locally
            box_name = sheet_name = self.INVENTORY[tag]
            action = "borrowed" if tag in self.existing_inventory else "returned"
            row = [[name, id_num, action, timestamp]]
            rows[box_name] = row
        if not online():
            # Append box number to user record
            # TODO:
            self.local_save(rows)
            return

        for box_name, row in rows.items():
            try:
                # TODO: CREATE SHEETS WHEN INVENTORY IS CREATED
                # Try and open the worksheet. If it does not exist, create it and fill up column headers.
                worksheet = self.LOG.worksheet(box_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = self.create_new_worksheet(box_name)

            # Finally, delete the last row, and insert the new row at the top
            worksheet.delete_rows(MAX_LOG_LENGTH)
            worksheet.insert_row(row, 2)

        self.existing_inventory = new_inventory

    def create_new_worksheet(self, box_name):
        worksheet = self.LOG.add_worksheet(title=box_name, rows=MAX_LOG_LENGTH - 1, cols=len(LOG_COLS))
        worksheet.insert_row(LOG_COLS, 1)

        def end_col(num):
            return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[num - 1]

        cols_num = len(LOG_COLS)
        worksheet.format(f"A1:{end_col(cols_num)}1", {
            "backgroundColor": {
                "red": 0.2,
                "green": 0.2,
                "blue": 0.7
            },
            "horizontalAlignment": "CENTER",
            "textFormat": {
                "foregroundColor": {
                    "red": 1,
                    "green": 1,
                    "blue": 1
                },
                "fontSize": 12,
                "bold": True
            }
        })
        return worksheet

    def local_save(self, rows):
        # If file does not exist, create it. If it exists, load it, append to it, dump it back.
        self.LOCAL = True  # Local variable to flag when there is a local log
        try:
            with open(LOCAL_LOG_PATH, "rb") as file:
                log = pickle.load(file)
        except FileNotFoundError:
            log = {}
        for box_name, row in rows.items():
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
            try:
                # TODO: MOVE TO WHEN INVENTORY IS ADDED
                worksheet = self.LOG.worksheet(box_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = self.create_new_worksheet(box_name)

            num = len(rows)
            worksheet.delete_dimension("ROWS", start_index=MAX_LOG_LENGTH - num + 1, end_index=MAX_LOG_LENGTH)
            worksheet.insert_rows(rows, 2)

        with open(LOCAL_LOG_PATH, "wb") as file:
            pickle.dump({}, file)

        self.LOCAL = False


if __name__ == '__main__':
    # Wait for the door to be closed
    setup_pi()
    while not GPIO.input(DOOR_PIN):
        sleep(0.5)
    sleep(0.5)
    GPIO.output(LOCK_PIN, GPIO.LOW)
    SmartCabinet()
