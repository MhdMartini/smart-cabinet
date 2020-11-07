import socket, sys, time

RPi_address = ("10.0.0.157", 4236)
MAX_LENGTH = 1024

BANNER = """
  University of Massachusetts Lowell
ECE Smart Cabinet Inventory Application
"""


def pprompt(prompt, opts=list("1234")):
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

    def __init__(self):
        # Create socket object, connect to RPi, and prompt Admin to send commands.
        # User input should be a number from 1 to 4.
        self.commands = {
            "1": lambda: self.add(msg=b"admin"),
            "2": lambda: self.add(msg=b"student"),
            "3": lambda: self.add(msg=b"shoebox"),
            "4": lambda: self.close()
        }

        self.admin = socket.socket()
        self.connect()

        print(BANNER)

        self.send_commands()

    def connect(self):
        # Connect to the RPi, RPi should be in Admin Routine, expecting a connection
        # Stay until you are connected. Return after creating an Admin socket object.
        while True:
            # If this application is run before an Admin scans their ID, the application
            # will be stuck here until an Admin ID is scanned, followed by a new student ID scanned.
            try:
                self.admin.connect(RPi_address)
                print("Successful Connected!")
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
            command = pprompt(self.prompt)
            self.commands[command]()

    def add(self, msg):
        # Send command to Add Admin, or Add Student, or Add Inventory Item. BLock until ACK is received
        # ACK is received when Cabinet is ready for next step
        # After receiving scanned ID from RPi, get the associated name. (Admin name, student name, or item name)
        # Finally, send ID,name to RPi, and check if user is done or not.
        while True:
            self.admin.send(msg)
            self.get_msg()  # Get Ack

            print(f"Scan the new {msg.decode()} ID")

            # Receive ID Number (bytes)
            new_id = self.get_msg()
            self.ack(self)
            print(f"{new_id} Received!")

            while True:
                # prompt for Admin name
                new_name = input(f"Enter {msg.decode()} Name: ")
                retry = input("Confirm? <Hit Enter>. Retry? <Enter any character>")
                if not retry:
                    break

            # Send Info Over to RPi. Info looks like this:
            # b"34645723,John Doe"
            info = b",".join([new_id, new_name.encode()])
            self.admin.send(info)

            print()
            done = input(f"Add Another {msg.decode()}? <Hit Enter>. Exit? <Enter any character>")
            if done:
                # Return to send_commands method
                return

    def get_msg(self):
        msg = self.admin.recv(MAX_LENGTH)
        return msg

    def ack(self):
        self.admin.send(b"ack")

    def close(self):
        self.admin.close()
        sys.exit(0)


if __name__ == '__main__':
    Admin().send_commands()