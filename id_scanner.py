#!/usr/bin/env python3
""" UML Capstone: 20-205 Smart Cabinet
Components: Raspberry Pi 4 and rf IDeas pcProx Plus
Reference Links:    'https://www.rfideas.com/sites/default/files/2020-01/ASCII_Manual.pdf'
                    'https://www.rfideas.com/sites/default/files/2020-01/RFIDeas-pcProx_Plus_Enroll_Wiegand-Manual.pdf'
                    'https://www.hidglobal.com/sites/default/files/resource_files/an0109_a.2_credential_id_markings_application_note.pdf'
                    'https://www.hidglobal.com/sites/default/files/hid-understanding_card_data_formats-wp-en.pdf'
                    'https://www.hidglobal.com/system/files/doc_eol_expired_files/0004_an_en.pdf'
cmd: "python -m serial.tools.miniterm"

Steps to run:
    1. Run program to automatically create 3 files ("ID_Admin.txt", "ID_Regular.txt", and "ID_Scanner.log")
    2. Add the required admin IDs to "ID_Admin.txt" (1 ID per line)
    3. Re-run the program
    4. Refer tp RFIDLed class to

TODO: Google sheet API
TODO: File size for upload to drive
TODO: Scan ID in binary and convert (?)
TODO: Integration with main program

gmail username: "smartcabinet.uml@gmail.com"
gmail password: "UML20-205"
"""

import serial
import enum
import time
import datetime
import logging
import os, sys

# Logging INFO level
logger = logging.getLogger("ID_Scanner")  # Create logger name labeled "ID_Scanner"
logger.setLevel(logging.INFO)  # INFO/DEBUG mode if needed
log_format = logging.Formatter(fmt="[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_logger = logging.StreamHandler()  # Create console handler to see
console_logger.setFormatter(log_format)
file_logger = logging.FileHandler("ID_log.log")  # Create file handler to save
file_logger.setFormatter(log_format)
logger.addHandler(console_logger)  # Add handlers for dispatching log messages to destination
logger.addHandler(file_logger)

# ID scanner output variables
class RFIDLed(enum.IntEnum):  # LED color on the ID scanner
    OFF = 0
    RED = 1  # Default (solid) and invalid ID (blink once + beep once)
    GREEN = 2  # Regular mode with valid ID (blink once + beep once)
    AMBER = 3  # Admin mode with special ID (solid + beep once)
    # Admin Mode: Tap once to enter and tap again (or timeout in 60s) to exit
    # 0. Scan ID to add and scan the same ID to remove
    # 1. Add valid ID (Green blink once + beep twice) - If ID not found in list
    # 2. Remove valid ID (Red blink once + beep long) - If ID found in list


class RFIDBuzzer(enum.IntEnum):  # Buzzer sound on the ID scanner
    ONE = 1  # Acknowledge (General)
    TWO = 2  # Add (Admin)
    THREE = 3
    FOUR = 4
    FIVE = 5  # Error (General)
    LONG = 101  # Remove (Admin)
    LONGER = 102  # Timeout (Admin)
    """ Parameter:
        - 1 to 5: X short beep(s)
        - 101 – single long beep
        - 102 – two long beeps
    """


# ID scanner serial functions
class RFIDSerial:
    def __init__(self, serial_port: str):  # Initialized the serial device
        # The RFID devices requires no parity, and one stop bit
        self.serial = serial.Serial(serial_port, 9600, parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE)

    def get_variable(self, variable: str):  # Get output from RFID scanner function
        # time.sleep(0.1)
        out_binary = str.encode(variable + "?\n")
        self.serial.write(out_binary)
        self.serial.timeout = 1
        res = self.serial.read(100)
        self.serial.timeout = None
        resp = str(res)  # Get relevant answer from response
        left_paren = resp.find("{")
        right_paren = resp.find('}')
        answer = resp[left_paren + 1: right_paren]
        if answer.isdigit():  # Format output
            return float(answer)
        elif answer == "True":
            return True
        elif answer == "False":
            return False

    def send_command(self, command: str):  # Send a command to the RFID scanner
        # :param command: The RFID command to send
        # time.sleep(0.1)
        out_binary = str.encode(command + "\n")  # Convert the command to binary
        self.serial.write(out_binary)  # Send the command to the device
        trace = self.serial.read(11)  # Read 11 bytes to account for the repetitive "\r\nRF Ideas>" prompt
        logger.debug("send_command read(11) result: " + str(trace))

    def disable_echo(self):  # Removing the echo makes processing easier. Only runs if echo is enabled.
        # time.sleep(0.1)
        self.send_command("rfid:cmd.echo=False")
        trace = self.serial.read(20)
        logger.debug("disable_echo read(20) result: " + str(trace))

    def set_read_bits(self, bits: int):  # Set the number of bits being read by the device
        # time.sleep(0.1)
        self.send_command("rfid:wieg.id.bits=" + str(bits))
        self.send_command("rfid:cfg.write")  # Send write command to the device
        trace = self.serial.read(6)  # Read 6 bytes to account for the "\r\n{OK}}" output
        logger.debug("set_read_bits read(6) result: " + str(trace))

    def read_card_raw(self):  # Read configuration 2 card (HID iCLASS ID) value in the format of "FAC:ID"
        res = ""
        while True:
            char = self.serial.read()  # Read raw card data from RFID scanner until '\r' character
            if char == b'\r':  # If we get this character, that is the end of the card data. Exit loop
                break
            res += char.decode("utf-8")  # Convert binary to UTF-8 (string)
        self.serial.reset_input_buffer()
        return res

    def read_card(self):  # Read ID scanned with both 16bits (Wiegand Standard 26bits Format) and 32bits
        self.set_read_bits(16)
        self.serial.reset_input_buffer()
        res_16 = self.read_card_raw()  # Data is in the format of "FAC:ID"
        logger.debug("res_16 log read result: " + str(res_16))
        time.sleep(.1)
        self.set_read_bits(32)
        res_32 = self.read_card_raw()
        logger.debug("res_32 log read result: " + str(res_32))
        split_16 = res_16.split(':')  # Splitting the data into [FAC, ID number]
        # split_32 = res_32.split(':')
        if int(split_16[0]) <= 255:  # This ID is 16bits
            logger.debug("read_card 16 bits loop result: " + str(res_16))
            return res_16
        else:  # This ID is 32bits
            logger.debug("read_card 32 bits loop result: " + str(res_32))
            return res_32

    def set_color(self, led: RFIDLed):  # Set LED color types
        # time.sleep(0.1)
        self.send_command('rfid:out.led={}'.format(int(led)))

    def set_beep(self, buzzer: RFIDBuzzer):  # Set buzzer sound type
        # time.sleep(0.1)
        self.send_command("rfid:beep.now={}".format(int(buzzer)))

    def close(self):  # Close the serial port
        self.serial.close()


# ID scanner program
class IDScanner:
    @staticmethod
    def initialize():  # Call this at the start of the main program
        logger.info("Smart cabinet power on")
        if rfid.get_variable("rfid:cmd.echo"):  # Disable echo if on
            rfid.disable_echo()
        rfid.send_command("rfid:cfg=2")  # Set configuration to 2 for HID iCLASS ID card
        logger.info("Configuration completed")

    @staticmethod
    def main():  # Stay in loop until an ID is scanned and return it
        while True:
            # rfid.set_color(RFIDLed.RED)  # Default LED color set to red
            number = rfid.read_card()  # Get the ID
            return number
            time.sleep(.1)

    @staticmethod
    def main_original():
        IDScanner.initialize()
        while True:  # TODO: To remove while loops for integration after debugging is completed
            rfid.set_color(RFIDLed.RED)  # Default LED color set to red
            number1 = rfid.read_card()  # Get the ID
            if number1 in adminID:  # Check if it's the admin ID
                logger.info("Admin mode activated by ID #" + number1)
                # TODO: Update admin sheet date
                IDScanner.mode_admin()
                IDScanner.save_regular_id(regularID)
                # TODO: Update regular sheet id
                # TODO: Return True, Open doors and other functions
            elif number1 in regularID:  # Check if it's the valid ID
                logger.info("Door opened by student ID #" + number1)
                # TODO: Update regular sheet date
                IDScanner.mode_regular()
                # TODO: Return False, Open doors and other functions
            else:  # Invalid ID
                logger.info("Invalid ID #" + number1)
                IDScanner.mode_invalid()
                # TODO: Return None, nothing happen

            # TODO: Update log
            # TODO: Pull admin sheet id
            time.sleep(.1)

    @staticmethod
    def mode_admin_original():  # Add/Remove valid ID
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned
        rfid.serial.timeout = 5  # Switch from event based to checking every second for scanned cards
        admin_timeout = time.time() + 60  # Set timeout in 60s
        while True:
            rfid.set_color(RFIDLed.AMBER)  # Amber to show admin mode
            number2 = rfid.read_card()  # Get the ID
            if time.time() > admin_timeout:
                logger.info("Exit admin mode due to timeout")
                rfid.set_beep(RFIDBuzzer.LONGER)
                break
            if number2 in adminID:  # Exit admin mode by admin
                logger.info("Exit admin mode due to ID #" + number2)
                rfid.set_beep(RFIDBuzzer.ONE)
                break
            elif len(number2) != 0:  # Ignoring non-scan from ID scanner

                if number2 not in regularID:  # Check if ID is not in the list then add
                    regularID.append(number2)  # Add ID
                    logger.info("Added student ID #" + number2)
                    rfid.set_beep(RFIDBuzzer.TWO)  # Beep twice to show added
                    rfid.set_color(RFIDLed.GREEN)  # Green to show add
                    admin_timeout = time.time() + 60  # Reset timeout in 60s

                elif number2 in regularID:  # Check if ID is in the list then remove
                    regularID.remove(number2)  # Remove ID
                    logger.info("Removed student ID #" + number2)
                    rfid.set_beep(RFIDBuzzer.LONG)  # Beep long to show removed
                    rfid.set_color(RFIDLed.RED)  # Red to show remove
                    admin_timeout = time.time() + 60  # Reset timeout in 60s

                else:
                    rfid.set_beep(RFIDBuzzer.FIVE)  # Error

            time.sleep(.1)
        rfid.serial.timeout = None

    @staticmethod
    def mode_regular():  # Regular ID output from ID scanner
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned
        rfid.set_color(RFIDLed.GREEN)  # Green to show access granted

    @staticmethod
    def mode_invalid():  # Invalid ID output from ID scanner
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned
        rfid.set_color(RFIDLed.OFF)  # LED off to show access denied

    @staticmethod
    def mode_admin():  # Admin mode output from ID scanner
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned
        rfid.set_color(RFIDLed.AMBER)  # Amber to show admin mode

    @staticmethod
    def mode_add():  # Add ID in admin mode output from ID scanner
        rfid.set_beep(RFIDBuzzer.TWO)  # Beep twice to show added
        rfid.set_color(RFIDLed.GREEN)  # Green to show add

    @staticmethod
    def mode_remove():  # Remove ID in admin mode output from ID scanner
        rfid.set_beep(RFIDBuzzer.LONG)  # Beep long to show removed
        rfid.set_color(RFIDLed.RED)  # Red to show remove

    @staticmethod
    def load_list(filename):
        if not os.path.exists(filename):
            logger.warning("File {} does not exist. Returning empty list. Require admin ID setup".format(filename))
            with open(filename, "w") as f:
                f.write("Updated as of " + str(datetime.datetime.now()) + "\n")
        else:
            res_list = []
            with open(filename, "r") as f:
                next(f)  # Ignore first line with date information
                for line in f:
                    res_list.append(line.strip())
            logger.info("Loaded {} items from {}".format(len(res_list), filename))
            return res_list

    @staticmethod
    def save_regular_id(data):  # Save all the valid ID for backup
        logger.debug("IDs to be saved:" + str(data))
        with open("ID_Regular.txt", "w") as f:
            f.write("Updated as of " + str(datetime.datetime.now()) + "\n")
            for card_id in data:
                f.write(card_id + "\n")


# ID scanner Setup
path = os.path.dirname(os.path.realpath(__file__))
rfid = RFIDSerial('/dev/ttyACM0')  # Create an RFIDClass which initialize the serial device.
adminID = IDScanner.load_list(os.path.join(path, "ID_Admin.txt"))  # Need to add admin ID manually
regularID = IDScanner.load_list(os.path.join(path, "ID_Regular.txt"))
# FAC = IDScanner.load_list(os.path.join(path, "ID_FAC.txt"))
# Test IDs: '40515', '18664'

if __name__ == '__main__':
    IDScanner.main()
