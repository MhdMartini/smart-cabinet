#!/usr/bin/env python3
""" UML Capstone: 20-205 Smart Cabinet
Components: Raspberry Pi 4 and rf IDeas pcProx Plus
Referece Links: 'https://www.rfideas.com/sites/default/files/2020-01/ASCII_Manual.pdf'
       			'https://www.rfideas.com/sites/default/files/2020-01/RFIDeas-pcProx_Plus_Enroll_Wiegand-Manual.pdf'
cmd: "python -m serial.tools.miniterm"

Steps to run:
	1. Run program to automatically create 3 files ("ID_Admin.txt", "ID_Regular.txt", and "ID_Scanner.log")
	2. Add the required admin IDs to "ID_Admin.txt" (1 ID per line)
	3. Re-run the program
	4. Refer tp RFIDLed class to

TODO: Link with google, Make adding admin ID much easier
"""

import serial
import time
import datetime
import logging
import os

# Logging INFO level
logger = logging.getLogger("ID_Scanner")  # Create logger name labeled "ID_Scanner"
logger.setLevel(logging.INFO)  # DEBUG mode if needed
log_format = logging.Formatter(fmt="[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_logger = logging.StreamHandler()  # Create console handler to see
console_logger.setFormatter(log_format)
file_logger = logging.FileHandler("ID_log.log")  # Create file handler to save
file_logger.setFormatter(log_format)
logger.addHandler(console_logger)  # Add handlers for dispatching log messages to destination
logger.addHandler(file_logger)


# ID scanner output variables
class RFIDLed:  # LED color on the ID scanner
    OFF = 0
    RED = 1  # Default (solid) and invalid ID (blink once + beep once)
    GREEN = 2  # Regular mode with valid ID (blink once + beep once)
    AMBER = 3  # Admin mode with special ID (solid + beep once)
    # Admin Mode: Tap once to enter and tap again (or timeout in 60s) to exit
    # 0. Scan ID to add and scan the same ID to remove
    # 1. Add valid ID (Green blink once + beep twice) - If ID not found in list
    # 2. Remove valid ID (Red blink once + beep long) - If ID found in list


class RFIDBuzzer:  # Buzzer sound on the ID scanner
    ONE = 1  # Acknowledge (General)
    TWO = 2  # Add (Admin)
    THREE = 3
    FOUR = 4
    FIVE = 5  # Error (General)
    LONG = 101  # Remove (Admin)
    LONGER = 102
    """ Parameter:
        - 1 to 5: X short beep(s)
        - 101 – single long beep
        - 102 – two long beeps
    """


# ID scanner serial functions
class RFIDSerial:
    def __init__(self, serial_port):  # Initialized the serial device
        # The RFID devices requires no parity, and one stop bit
        self.serial = serial.Serial(serial_port)

    def send_command(self, command):  # Send a command to the RFID scanner
        # :param command: The RFID command to send
        out_binary = str.encode(command + "\n")  # Convert the command to binary
        self.serial.write(out_binary)  # Send the command to the device
        trace = self.serial.read(11)  # Read 11 bytes to account for the repetitive "\r\nRF Ideas>" prompt
        logger.debug("send_command read(11) result: " + str(trace))

    def read_card(self):  # Read ID scanned
        read = self.serial.read(6)  # Read raw card data from RFID scanner (6 bytes)
        read = read.decode().strip()
        logger.debug("read_card read(6) result: " + read)
        # TODO: Cards might have an input of more than 6 bytes
        return read  # Convert binary to UTF-8 (string), remove invisible characters, and return

    def set_color(self, led):  # Set LED color type
        self.send_command('rfid:out.led={}'.format(led))

    def set_beep(self, buzzer):  # Set buzzer sound type
        self.send_command("rfid:beep.now={}".format(buzzer))

    def close(self):  # Close the serial port
        self.serial.close()


# ID scanner program
class Program:
    @staticmethod
    def main():
        logger.info("Smart cabinet power on")
        if rfid.get_variable("rfid:cmd.echo"):  # Disable echo if on
            rfid.disable_echo()
        logger.info("Configuration completed")
        while True:
            rfid.set_color(RFIDLed.RED)  # Default LED color set to red
            number = rfid.read_card()  # Get the ID
            if number in adminID:  # Check if it's the admin ID
                logger.info("Door opened by admin ID #" + number)
                Program.mode_admin()
                Program.save_regular_id(regularID)
                # TODO: Open doors and other functions
            elif number in regularID:  # Check if it's the valid ID
                logger.info("Door opened by student ID #" + number)
                Program.mode_regular()
                return number
                # TODO: Open doors and other functions
            else:  # Invalid ID
                logger.info("Invalid ID #" + number)
                Program.mode_invalid()

            time.sleep(.1)

    @staticmethod
    def save_regular_id(data):  # Save all the valid ID for backup
        logger.debug("IDs to be saved:" + str(data))
        with open("ID_Regular.txt", "w") as f:
            f.write("Updated as of " + str(datetime.datetime.now()) + "\n")
            for card_id in data:
                f.write(card_id + "\n")

    @staticmethod
    def mode_admin():  # Add/Remove valid ID
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned
        rfid.serial.timeout = 5  # Switch from event based to checking every second for scanned cards
        admin_timeout = time.time() + 60  # Set timeout in 60s
        while True:
            rfid.set_color(RFIDLed.AMBER)  # Amber to show admin mode
            number = rfid.read_card()  # Get the ID
            if time.time() > admin_timeout:
                logger.info("Exit admin mode due to timeout")
                break
            if number in adminID:  # Exit admin mode by admin
                logger.info("Exit admin mode due to ID #" + number)
                break
            elif len(number) != 0:  # Ignoring non-scan from ID scanner
                if number not in regularID:  # Check if ID is not in the list then add
                    rfid.set_color(RFIDLed.GREEN)  # Green to show add
                    regularID.append(number)  # Add ID
                    logger.info("Added student ID #" + number)
                    rfid.set_beep(RFIDBuzzer.TWO)  # Beep twice to show added
                    admin_timeout = time.time() + 60  # Reset timeout in 60s
                elif number in regularID:  # Check if ID is in the list then remove
                    rfid.set_color(RFIDLed.RED)  # Red to show remove
                    regularID.remove(number)  # Remove ID
                    logger.info("Removed student ID #" + number)
                    rfid.set_beep(RFIDBuzzer.LONG)  # Beep long to show removed
                    admin_timeout = time.time() + 60  # Reset timeout in 60s
                else:
                    rfid.set_beep(RFIDBuzzer.FIVE)  # Error

            time.sleep(.1)
        rfid.serial.timeout = None

    @staticmethod
    def mode_regular():  # Door unlock and inside program begin
        rfid.set_color(RFIDLed.GREEN)  # Green to show access granted
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned

    @staticmethod
    def mode_invalid():  # Invalid ID
        rfid.set_color(RFIDLed.OFF)  # LED off to show access denied
        rfid.set_beep(RFIDBuzzer.ONE)  # Acknowledge ID scanned

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


# ID scanner Setup
DATA_FOLDER = os.path.join("/home", "pi", "RFIDProject")  # Should be changed or removed on different PI
rfid = RFIDSerial('/dev/ttyACM0')  # Create an RFIDClass which initialize the serial device.
adminID = Program.load_list(os.path.join(DATA_FOLDER, "ID_Admin.txt"))  # Need to add admin ID manually
regularID = Program.load_list(os.path.join(DATA_FOLDER, "ID_Regular.txt"))
# Test IDs: '40515', '18664'

if __name__ == '__main__':
    Program.main()
