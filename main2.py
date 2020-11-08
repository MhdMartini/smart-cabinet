import json
from time import time, sleep
import RPi.GPIO as GPIO
from pi_server import PiServer
from rfid_reader import RFIDReader

# Local directory where the Admin, Inventory, and Students files exist
ADMINS_PATH = r"/home/pi/admin.json"
INVENTORY_PATH = r"/home/pi/inventory.json"
STUDENTS_PATH = r"/home/pi/students.json"

PORT_RFID = r"tmr:///dev/ttyACM0"

LOCK_PIN = 17
DOOR_PIN = 18
OPEN_TIMEOUT = 5  # Open door before 5 seconds pass
CLOSE_TIMEOUT = 60  # Close door before 1 minute passes


class SmartCabinet:
    ADMINS = {}
    INVENTORY = {}  # Complete inventory; key = tag number; value = string identifier
    STUDENTS = {}

    existing_inventory = set()  # Set of existing inventory items

    reader = RFIDReader(PORT_RFID)  # Connect to RFID Reader
    server = PiServer(reader)  # Create server for Admin App communication. Pass in RFID reader.
    # TODO: SAM: Create id scanner object. To be used to perform id_scanner functionality
    admin = False

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
        self.setup_pi()
        self.update_local_objects()
        self.normal_operation()

    @staticmethod
    def setup_pi():
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.LOW)  # Low: Lock. High: Unlock Door
        GPIO.setup(DOOR_PIN, GPIO.IN)  # High when door is closed. Low if door opens.

    def normal_operation(self):
        # Read Scanned ID's. Local objects should be up-to-date. If ADMINS are not added yet,
        # Go into Admin Routine to allow user to add Admins. Admins then hold their ID to enter
        # Admin Routine and perform Admin functions
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
                    sleep(1)
                    continue

            # Only get here when valid ID is scanned
            if self.admin:
                self.unlock()
                sleep(1)  # TODO: Optimize Later
                # TODO: SAM: Set ID Scanner Timeout as 0.1
                # TODO: SAM: Scan ID. Uncomment next line and fill in the scan method
                # hold = <call scan method> == id
                # TODO: SAM: Set ID Scanner Timeout as None
                if hold:
                    self.admin_routine()
                    continue

            use = self.handle_user()
            # Only get here when door is closed back
            if use:
                # If the Cabinet was used, update the log
                self.update_log(user)

    def update_local_objects(self):
        # Update ADMIN, INVENTORY, and STUDENTS from json files. If a file does not exist, create it.
        # Finally, update existing_inventory by performing an inventory_scan
        files = (ADMINS_PATH, INVENTORY_PATH, STUDENTS_PATH)
        dicts = [self.ADMINS, self.INVENTORY, self.STUDENTS]

        for idx, file, dict_ in zip(range(len(files)), files, dicts):
            try:
                with open(file, "r") as outfile:
                    dicts[idx] = json.load(outfile)
            except FileNotFoundError:
                with open(file, "w") as outfile:
                    json.dump(dict_, outfile, indent=4)

        self.existing_inventory = self.reader.scan()

    def admin_routine(self):
        # Unlock door, then get into Admin Routine. Only return when a "done" command is received,
        # at which point we update local objects.
        #  Block until door is closed at the end, then lock door and return
        self.unlock()
        self.server.admin_routine()
        self.update_local_objects()

        while not GPIO.input(DOOR_PIN):
            pass
        self.lock()

    @staticmethod
    def unlock():
        # TODO: SAM: Beep.
        # TODO: SAM: LED GREEN.
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
            # TODO: SAM: Beep
            sleep(1)
        self.lock()

    def update_log(self, user):
        # Only get here when user has used the Cabinet (opened door, then closed door)
        # Scan inventory and handle tickets. XOR between two sets returns the different items.
        # Finally, update the existing_inventory variable
        new_inventory = self.reader.scan()
        different_tags = new_inventory ^ self.existing_inventory
        if not different_tags:
            return

        for tag in different_tags:
            box_name = self.INVENTORY[tag]
            item = "borrowed" if tag in self.existing_inventory else "returned"
            # TODO: SAM: DECIDE OUTPUT FORMAT. Info: tag (RFID#), box_name (shoebox#), user (user name),
            #  item (borrowed, returned), time of use (time())

        self.existing_inventory = new_inventory

    def notify(self):
        # TODO: ADD CODE for when a student opens the door but never closes it.
        pass


if __name__ == '__main__':
    SmartCabinet()
