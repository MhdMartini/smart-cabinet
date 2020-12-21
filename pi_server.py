"""
Script:     pi_server.py
Project:    Smart Cabinet
Author:     Mohamed Martini
Version:    1.0 - Tested
Purpose:    Handle Admin Routing Communication with admin.py on an Admin's computer
            Inherits from GoogleClient to handle communication with the Google Spreadsheets
"""
import socket
import json
import threading
from id_scanner import RFIDBuzzer
from google_client import GoogleClient

MAX_LENGTH = 1024

ADMINS_PATH = r"/home/pi/Desktop/Smart_Cabinet/admin.json"
INVENTORY_PATH = r"/home/pi/Desktop/Smart_Cabinet/inventory.json"
STUDENTS_PATH = r"/home/pi/Desktop/Smart_Cabinet/students.json"
SECRET_PATH = r"/home/pi/Desktop/secret.json"

# Get RPI (IP, port) from json file
with open(SECRET_PATH, "r") as secret:
    RPi_address = json.load(secret)
    RPi_address = (RPi_address["ip"], int(RPi_address["port"]))


class PiServer(GoogleClient):
    admin = None  # Admin object to handle communication with Admin App

    # NOTE: TESTED
    def __init__(self, reader=None, id_reader=None):
        # Bind to TCP socket and wait for Admin App to connect.
        # Take in the RFID reader object as an argument. This is used to add inventory
        self.commands = {
            b"admin": lambda: self.add_access(kind="admin"),
            b"student": lambda: self.add_access(kind="student"),
            b"shoebox": lambda: self.add_access(kind="shoebox"),
            b"done": lambda: self.close()
        }
        self.reader = reader
        self.id_reader = id_reader
        self.launch_google_client()

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
        self.admin.close()
        self.sock.close()

    def admin_routine(self, persistent=False):
        # Connect to Admin App. Keep receiving commands until a "done" command is received.
        # Call necessary methods when a command is received.
        if not self.accept(persistent=persistent):
            return
        while True:
            command = self.get_msg()
            try:
                try:
                    self.commands[command]()
                except Exception as e:
                    if e == "Client Disconnected":
                        self.close()
                        return
            except KeyError:
                # If an unknown command is received, recover from attack/connection drop
                self.recover()
                break
            if command == b"done":
                self.close()
                return

    def recover(self):
        self.admin.shutdown(socket.SHUT_RDWR)
        self.admin.close()
        self.admin = None

    def accept(self, persistent=False):
        # Connect to Admin object (Admin application).
        # When connection is successful, the Admin App will notify Admin
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(RPi_address)
        self.sock.listen(1)
        if not persistent:
            self.sock.settimeout(60)  # User has 1 minute to connect
        try:
            self.admin, _ = self.sock.accept()
            return True
        except socket.timeout:
            return False
        finally:
            self.sock.settimeout(None)

    def add_access(self, kind="student"):
        # Scan ID. Send ID to Admin App. Receive info (id,String Identifier).
        # Update local files accordingly.
        if kind == "shoebox":
            scanned = self.reader.scan_until()
            self.id_reader.set_beep(RFIDBuzzer.TWO)
        else:
            scanned = self.id_reader.read_card()
            self.id_reader.set_beep(RFIDBuzzer.TWO)

        self.send_msg(scanned.encode())
        identifier = self.get_msg().decode()
        if identifier == "done":
            # If admin app accidentally closed before admin enters identifer
            raise Exception("Client Disconnected")

        # Update local and online Access info.
        new_entry = [identifier, scanned, ""] if kind != "shoebox" else [identifier, scanned]
        self.update_local_access(new_entry=new_entry, record=kind)
        t1 = threading.Thread(target=lambda: self.update_online_access(new_entry=new_entry, record=kind))
        t1.start()

        # If Shoebox, create its LOG worksheet
        if kind == "shoebox":
            t2 = threading.Thread(target=lambda: self.create_shoebox_worksheet(identifier))
            t2.start()

    @staticmethod
    def update_local_access(new_entry, record="student"):
        # Load current json, add entry to it, dump it back
        new_entry = {new_entry[1]: new_entry[0]}
        file = STUDENTS_PATH if record == "student" else ADMINS_PATH if record == "admin" else INVENTORY_PATH
        with open(file, "r") as outfile:
            temp = json.load(outfile)

        temp.update(new_entry)
        with open(file, "w") as outfile:
            json.dump(temp, outfile, indent=4)
