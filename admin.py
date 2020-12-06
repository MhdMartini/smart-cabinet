import socket
import sys
import time
import atexit

# RPi_address = ("192.168.1.229", 4236)
RPi_address = (socket.gethostname(), 4236)
MAX_LENGTH = 1024  # Maximum length of received message

BANNER = """
      University of Massachusetts Lowell
Department of Electrical and Computer Engineering

*****ECE Smart Cabinet Inventory Application*****
"""


def pprompt(prompt, opts=[]):
    # Persistent prompt until a valid input is received
    while True:
        ans = input(prompt)
        if ans in opts:
            return ans
        print("Invalid Input. Try again!")


class Admin:
    # TCP socket object
    admin = None
    prompt = """
    Please select an option below, by entering the corresponding number. E.g. Enter 1 to Add Admins.
    1- Add Admins
    2- Add Students
    3- Add Inventory Items
    4- Close Connection
    """

    def __init__(self, gui=False):
        # Create socket object, connect to RPi, and prompt Admin to send commands.
        # User input should be a number from 1 to 4.
        self.gui = gui  # To indicate if called by GUI or Terminal
        if not gui:
            print(BANNER)

        self.commands = {
            "1": lambda: self.add(msg=b"admin"),
            "2": lambda: self.add(msg=b"student"),
            "3": lambda: self.add(msg=b"shoebox"),
            "4": lambda: self.close()
        }

        self.admin = socket.socket()
        self.connect()

        if not self.gui:
            # If using Terminal AdminApp
            atexit.register(self.exit_handler)  # At force exit, release connection with Cabinet
            self.send_commands()

    def connect(self):
        # Connect to the RPi, RPi should be in Admin Routine, expecting a connection
        # Stay until you are connected. Return after creating an Admin socket object.
        while True:
            # If this application is run before an Admin scans their ID, the application
            # will be stuck here until an Admin ID is scanned, followed by a new student ID scanned.
            try:
                self.admin.connect(RPi_address)
                print("Connection Successful!")
                return
            except ConnectionRefusedError:
                print("Could not establish connection. Make sure the Cabinet is in Admin Mode")
                print("Retrying...")
                print()
                time.sleep(1)
                continue

    def send_commands(self):
        # Get here after the connect() method has created an Admin socket object
        # connected to the RPi.
        # Prompt Admin to select an option, and act accordingly.
        while True:
            command = pprompt(prompt=self.prompt, opts=list("1234"))
            self.commands[command]()

    def add(self, msg):
        # Send command to Add Admin, or Add Student, or Add Inventory Item. BLock until ACK is received
        # ACK is received when Cabinet is ready for next step
        # After receiving scanned ID from RPi, get the associated name. (Admin name, student name, or item name)
        # Finally, send ID,name to RPi, and check if user is done or not.
        while True:
            # Send command and receive ack
            self.send_msg(msg)

            print(f"Scan the new {msg.decode()} ID")

            # Receive ID Number (bytes)
            new_id = self.get_msg()

            print(f"{new_id} Received!")

            while True:
                # prompt for Admin name. Do not allow empty strings.
                new_name = input(f"Enter {msg.decode()} Name: ")
                if not new_name:
                    print("Invalid Input: You cannot assign an empty name to the item.")
                    continue
                retry = input("Confirm? <Hit Enter>. Retry? <Enter any character>")
                if not retry:
                    break

            # Send Identifier Over to RPi
            identifier = new_name.encode()
            self.send_msg(identifier)

            print()
            done = input(f"Add Another {msg.decode()}? <Hit Enter>. Exit? <Enter any character>")
            if done:
                # Return to send_commands method
                return

    def send_msg(self, msg):
        # Send the message and receive the ack
        self.admin.send(msg)
        self.admin.recv(MAX_LENGTH)

    def get_msg(self):
        # Get the message and send the ack
        msg = self.admin.recv(MAX_LENGTH)
        self.admin.send(b"ack")
        return msg

    def close(self):
        self.send_msg(b"done")
        self.admin.shutdown(socket.SHUT_RDWR)
        self.admin.close()
        sys.exit(0)

    def exit_handler(self):
        self.close()


if __name__ == '__main__':
    Admin().send_commands()
