#!/usr/bin/env python3
""" UML Capstone: 20-205 Smart Cabinet
Components: Raspberry Pi 4 and rf IDeas pcProx Plus
Reference Links:    'https://www.rfideas.com/sites/default/files/2020-01/ASCII_Manual.pdf'
                    'https://www.rfideas.com/sites/default/files/2020-01/RFIDeas-pcProx_Plus_Enroll_Wiegand-Manual.pdf'
                    'https://www.hidglobal.com/sites/default/files/resource_files/an0109_a.2_credential_id_markings_application_note.pdf'
                    'https://www.hidglobal.com/sites/default/files/hid-understanding_card_data_formats-wp-en.pdf'
                    'https://www.hidglobal.com/system/files/doc_eol_expired_files/0004_an_en.pdf'
cmd: "python -m serial.tools.miniterm"
"""

import serial
import enum
import time
import logging


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
        self.serial = serial.Serial(serial_port, 115200, parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE, timeout=60)
        if self.get_variable("rfid:cmd.echo"):  # Disable echo if on
            self.disable_echo()
        self.send_command("rfid:cfg=2")

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
        self.serial.read(11)  # Read 11 bytes to account for the repetitive "\r\nRF Ideas>" prompt

    def disable_echo(self):  # Removing the echo makes processing easier. Only runs if echo is enabled.
        # time.sleep(0.1)
        self.send_command("rfid:cmd.echo=False")
        self.serial.read(20)

    def set_read_bits(self, bits: int):  # Set the number of bits being read by the device
        # time.sleep(0.1)
        self.send_command("rfid:wieg.id.bits=" + str(bits))
        self.send_command("rfid:cfg.write")  # Send write command to the device
        self.serial.read(6)  # Read 6 bytes to account for the "\r\n{OK}}" output

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
        # TODO: FIX BUG
        try:
            self.set_read_bits(16)
            self.serial.reset_input_buffer()
            res_16 = self.read_card_raw()  # Data is in the format of "FAC:ID"
            time.sleep(.1)
            self.set_read_bits(32)
            res_32 = self.read_card_raw()
            split_16 = res_16.split(':')  # Splitting the data into [FAC, ID number]
            if int(split_16[0]) <= 255:  # This ID is 16bits
                return res_16
            else:  # This ID is 32bits
                return res_32
        except Exception as e:
            print(e)
            return ""

    def set_color(self, led: RFIDLed):  # Set LED color types
        # time.sleep(0.1)
        self.send_command('rfid:out.led={}'.format(int(led)))

    def set_beep(self, buzzer: RFIDBuzzer):  # Set buzzer sound type
        # time.sleep(0.1)
        self.send_command("rfid:beep.now={}".format(int(buzzer)))

    def close(self):  # Close the serial port
        self.serial.close()


