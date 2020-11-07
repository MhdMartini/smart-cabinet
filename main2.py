import os, json, time
import RPi.GPIO as GPIO
from rfid_reader import RFIDReader
from pi_server import PiServer

# Local directory where the Admin, Inventory, and Students files exist
ADMINS_PATH = r"/home/pi/admin.json"
INVENTORY_PATH = r"/home/pi/inventory.json"
STUDENTS_PATH = r"/home/pi/students.json"
LOCK_PIN = 17
DOOR_PIN = 18
OPEN_TIMEOUT = 5  # Door timeout
CLOSE_TIMEOUT = 60


def setup_pi():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.LOW)  # Low. Make High to Unlock Door
    GPIO.setup(DOOR_PIN, GPIO.IN)  # High when door is closed. Low if door opens.


class SmartCabinet:
    ADMINS = {}
    INVENTORY = {}  # Complete inventory; key = tag number; value = string identifier
    STUDENTS = {}

    existing_inventory = set()  # Set of existing inventory items

    reader = RFIDReader()  # Connect to RFID Reader
    server = PiServer(reader)  # Create server for Admin App communication. Pass in RFID reader.
    admin = False

    def __init__(self):
        # On boot-up, configure the Pi, then update the local objects according to the local files.
        # Finally, scan the existing inventory
        # Local files include the Admins list, allowed students, and complete inventory items
        # Local files and objects are dictionary-type data structures, where the key is
        # the RFID number, and the value is an human-readable identifier of that number.
        # E.g. {"2378682234" : "John Doe"}
        # If local files do not exist, create empty local files.
        # Local files will then be filled by using the Admin Application
        self.setup_pi()

        self.update_local_objects()  # TODO: This method is also called at the end of each Admin Routine.
        self.normal_operation()

    @staticmethod
    def setup_pi():
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.LOW)  # Low. Make High to Unlock Door
        GPIO.setup(DOOR_PIN, GPIO.IN)  # High when door is closed. Low if door opens.

    def normal_operation(self):
        # Read Scanned ID's. Local objects should be up-to-date. If ADMINS are not added yet,
        # Go into Admin Routine to allow user to add Admins.
        if not self.ADMINS:
            self.admin_routine()

        while True:
            # TODO: SAM: LED Orange.
            # TODO: SAM: Scan ID. Replace Next Line.
            id = "some_number"
            try:
                # Check if scanned ID is Admin. If so, set admin variable
                user = self.ADMINS[id]
                self.admin = True
            except KeyError:
                self.admin = False
                try:
                    # If NOT Admin, Check if scanned ID is Student
                    user = self.STUDENTS[id]
                except KeyError:
                    # If scanned ID is neither Admin or Student
                    # TODO: SAM: LED Red.
                    time.sleep(1)
                    continue

            # Only get here when valid ID is scanned
            if self.admin:
                # admin code
                pass

            self.handle_user()

            # Only get here when door is closed back
            self.update_log(user)

    def update_local_objects(self):
        # Update ADMIN, INVENTORY, and STUDENTS from json files. If a file does not exist, create it.
        # Finally, update existing_inventory by performing an inventory_scan
        files = (ADMINS_PATH, INVENTORY_PATH, STUDENTS_PATH)
        dicts = (self.ADMINS, self.INVENTORY, self.STUDENTS)

        for file, dict_ in zip(files, dicts):
            try:
                with open(file, "r") as outfile:
                    dict_ = json.load(outfile)
            except FileNotFoundError:
                with open(file, "w") as outfile:
                    json.dump(dict_, outfile, indent=4)

        self.inventory_scan()

    @staticmethod
    def unlock():
        # TODO: SAM: Beep.
        # TODO: SAM: LED GREEN.
        GPIO.output(LOCK_PIN, GPIO.HIGH)

    @staticmethod
    def lock():
        GPIO.output(LOCK_PIN, GPIO.LOW)

    def inventory_scan(self):
        self.existing_inventory = self.reader.scan()

    def handle_user(self):
        # Unlock door, monitor door, if door does not open before timeout, lock back and return
        # timeout 5 seconds. If door opens: if user is admin, wait for door to close. Else: wait for either
        # the door to close, or for a timeout to pass.
        self.unlock()
        t = time.time()
        while GPIO.input(DOOR_PIN) and (time.time() - t) < OPEN_TIMEOUT:
            # While door is still closed
            pass

        # If timeout
        if GPIO.input(DOOR_PIN):
            self.lock()
            return

        # Only get here when Door is open
        # Camera ON, Monitor Door
        # TODO: KHALED: Start Camera Recording
        t = time.time()

        # If it is an admin, do not check if door is left open
        # This allows admin to keep door open through lab time.
        t = time.time()
        while (not self.admin and (not GPIO.input(DOOR_PIN)) and
               (time.time() - t < CLOSE_TIMEOUT)) or (self.admin and not GPIO.input(DOOR_PIN)):
            # Block while door is open
            time.sleep(0.5)
            continue

        # Only get here when Door is closed Back, or Student timeouts
        # TODO: If timeout, notify!

        return

    def update_log(self, user):
        # Only get here when user has used the Cabinet (opened door, then closed door)
        # Scan inventory and handle tickets. XOR between two sets returns the different items.
        new_inventory = self.reader.scan()
        different_tags = new_inventory ^ self.existing_inventory
        if not different_tags:
            return

        for tag in different_tags:
            box_name = self.INVENTORY[tag]
            if tag in self.existing_inventory:
                # Tag was borrowed
                # TODO: DECIDE OUTPUT FORMAT
                pass
            elif tag in new_inventory:
                # Tag was returned
                # TODO: DECIDE OUTPUT FORMAT
                pass
        self.existing_inventory = new_inventory

    def notify(self):
        # TODO: ADD CODE for when a student opens the door but never closes it.
        pass

    def admin_routine(self):
        # Get into Admin Routine. Only return when a "done" command is received,
        # at which point we update local objects.
        self.server.admin_routine()
        self.update_local_objects()

