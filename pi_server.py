import socket, json

RPi_address = ("10.0.0.157", 4236)
MAX_LENGTH = 1024

ADMINS_PATH = r"/home/pi/admin.json"
INVENTORY_PATH = r"/home/pi/inventory.json"
STUDENTS_PATH = r"/home/pi/students.json"


class PiServer:
    admin = None  # Admin object to handle communication with Admin App

    def __init__(self, reader):
        # Bind to TCP socket and wait for Admin App to connect.
        # Take in the RFID reader object as an argument. This is used to add inventory
        self.sock = socket.socket()
        self.commands = {
            b"admin": lambda: self.add_access(kind="admin"),
            b"student": lambda: self.add_access(kind="student"),
            b"shoebox": lambda: self.add_access(kind="shoebox"),
            b"done": lambda: self.close()
        }
        self.reader = reader

    def accept(self):
        # Connect to Admin object (Admin application).
        # When connection is successful, the Admin App will notify Admin
        self.sock.bind(RPi_address)
        self.sock.listen(1)
        self.admin, _ = self.sock.accept()

    def admin_routine(self):
        # Connect to Admin App. Keep receiving commands until a "done" command is received.
        # Call necessary methods when a command is received.
        self.accept()
        while True:
            command = self.get_msg()
            self.commands[command]()
            if command == b"done":
                return

    def add_access(self, kind="student"):
        # Scan ID. Send ID to Admin App. Receive info (id,String Identifier).
        # Update local files accordingly.
        if kind == "shoebox":
            scanned = self.reader.scan_until()
        else:
            # TODO: SAM: Scan ID. Replace the next line
            scanned = "some_number"

        self.send_msg(scanned.encode())
        identifier = self.get_msg()
        new_entry = {scanned: identifier.decode()}

        self.update_record(new_entry=new_entry, record=kind)

    @staticmethod
    def update_record(new_entry, record="student"):
        # Load current json, add entry to it, dump it back
        file = STUDENTS_PATH if record == "student" else ADMINS_PATH if record == "admin" else INVENTORY_PATH
        with open(file, "r") as outfile:
            temp = json.load(outfile)

        temp.update(new_entry)
        with open(file, "w") as outfile:
            json.dump(temp, outfile, indent=4)

    def send_msg(self, msg):
        # Send message and receive ack
        self.admin.send(msg)
        self.admin.recv(MAX_LENGTH)

    def get_msg(self):
        # Get message and send ack
        msg = self.admin.recv(MAX_LENGTH)
        self.admin.send(b"ack")
        return msg

    def close(self):
        self.sock.close()
