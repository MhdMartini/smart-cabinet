"""
Script:     pi_server.py
Project:    Smart Cabinet
Author:     Mohamed Martini
Version:    0.0 - Needs Testing
Purpose:    Handle Admin Routing Communication with admin.py on an Admin's computer
            Handle communication with the LOG Google Spreadsheet
"""
import socket
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import set_row_height, set_column_width
import threading

RPi_address = ("10.0.0.157", 4236)
MAX_LENGTH = 1024

ADMINS_PATH = r"/home/pi/Desktop/Smart Cabinet/local/admin.json"
INVENTORY_PATH = r"/home/pi/Desktop/Smart Cabinet/local/inventory.json"
STUDENTS_PATH = r"/home/pi/Desktop/Smart Cabinet/local/students.json"

LOCAL_LOG_PATH = r"/home/pi/Desktop/Smart Cabinet/local/log.pickle"
CREDENTIALS_PATH = r"/home/pi/Desktop/Smart Cabinet/credentials.json"

LOG_SHEET = "LOG"
ACCESS_SHEET = "ACCESS"
MAX_LOG_LENGTH = 1000
LOG_COLS = ["user", "RFID", "action", "timestamp"]
USER_GMAIL = "smartcabinet.uml@gmail.com"
# log link: https://docs.google.com/spreadsheets/d/14Yn1qQeSP7lMWCUF650HCiazOobwTpuGoGJtgpAK_wM/edit#gid=1552676933

INTRO_SHEET = [
    ["S M A R T   C A B I N E T"],
    ["UNIVERSITY OF MASSACHUSETTS LOWELL"],
    ["FRANCIS COLLEGE OF ENGINEERING"],
    ["ELECTRICAL AND COMPUTER ENGINEERING"],
    [],
    ["CAPSTONE PROJECT 20-205 - FALL20"],
    [],
    ["TEAM MEMBERS:"],
    ["    JOHN ALLEN"],
    ["    KHALED ALWASMI"],
    ["    PETER M BEER"],
    ["    THANAKIAT HASADINPAISAL"],
    ["    MOHAMED MARTINI"],
    ["    WILLIAM MORIARTY"],
    [],
    ["SPECIAL THANKS TO OUR MENTOR"],
    ["PROFESSOR JOHN PALMA"],
    [],
    [],
    [],
    [],
    [],
    [],
    [],
    [],
    ["For software support:"],
    ["mohamed_martini@student.uml.edu"]
]


class PiServer:
    admin = None  # Admin object to handle communication with Admin App
    LOG = None  # LOG Google Spreadsheet
    ACCESS = None

    # NOTE: TESTED
    def __init__(self, reader=None, rfid=None):
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
        self.rfid = rfid
        self.launch_google_client()

    def launch_google_client(self):
        # Create the LOG and ACCESS objects which hold the LOG spreadsheet and ACCESS spreadsheet.
        # If the either spreadsheet does not exist, create it.
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(credentials)

        try:
            self.LOG = client.open(LOG_SHEET)
        except gspread.exceptions.SpreadsheetNotFound:
            self.LOG = client.create(LOG_SHEET)
            self.LOG.share(USER_GMAIL, perm_type='user', role='writer')
            self.create_intro_sheet(self.LOG)

        try:
            self.ACCESS = client.open(ACCESS_SHEET)
        except gspread.exceptions.SpreadsheetNotFound:
            self.ACCESS = client.create(ACCESS_SHEET)
            self.ACCESS.share(USER_GMAIL, perm_type='user', role='writer')
            self.create_intro_sheet(self.ACCESS)
            self.create_access_worksheets()

    @staticmethod
    def create_intro_sheet(sheet):
        # Create the Introductory Worksheet
        worksheet = sheet.add_worksheet(title="SMART CABINET", rows=1, cols=1)
        sheet.del_worksheet(sheet.sheet1)
        worksheet.insert_rows(INTRO_SHEET, 1)

        set_column_width(worksheet, 'A', 1000)
        set_row_height(worksheet, '1:4', 70)
        set_row_height(worksheet, f'5:28', 34)

        worksheet.format("A1:A1", {
            "backgroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "horizontalAlignment": "CENTER",
            "textFormat": {
                "foregroundColor": {
                    "red": 0,
                    "green": 0.9,
                    "blue": 1
                },
                "fontSize": 30,
                "bold": True
            }
        })
        worksheet.format("A2:A5", {
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
        worksheet.format("A6:A7", {
            "backgroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "horizontalAlignment": "LEFT",
            "textFormat": {
                "foregroundColor": {
                    "red": 1,
                    "green": 0,
                    "blue": 0
                },
                "fontSize": 14,
                "bold": True
            }
        })
        worksheet.format("A8:A8", {
            "backgroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "horizontalAlignment": "LEFT",
            "textFormat": {
                "foregroundColor": {
                    "red": 0,
                    "green": 0.9,
                    "blue": 1
                },
                "fontSize": 12,
                "bold": True
            }
        })
        worksheet.format("A9:A14", {
            "backgroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "horizontalAlignment": "LEFT",
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
        worksheet.format("A15:A25", {
            "backgroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "horizontalAlignment": "CENTER",
            "textFormat": {
                "foregroundColor": {
                    "red": 0.9,
                    "green": 0,
                    "blue": 0
                },
                "fontSize": 14,
                "bold": False
            }
        })

        worksheet.format("A26:A27", {
            "backgroundColor": {
                "red": 0.2,
                "green": 0.2,
                "blue": 0.2
            },
            "horizontalAlignment": "LEFT",
            "textFormat": {
                "foregroundColor": {
                    "red": 1,
                    "green": 0,
                    "blue": 0
                },
                "fontSize": 12,
                "bold": False
            }
        })

        worksheet.delete_rows(28)

    def create_access_worksheets(self):
        colors = {
            "ADMINS": (0, 0.5, 0.5),
            "STUDENTS": (0.4, 0.8, 0.1),
            "INVENTORY": (0.5, 0.5, 0),
        }
        first_col = {
            "ADMINS": "Admin",
            "STUDENTS": "Student",
            "INVENTORY": "Item"
        }
        for name in ("ADMINS", "STUDENTS", "INVENTORY"):
            worksheet = self.ACCESS.add_worksheet(title=name, rows=1, cols=2)
            worksheet.insert_rows([[first_col[name], "RFID"]], 1)
            worksheet.format("A1:B1", {
                "backgroundColor": {
                    "red": colors[name][0],
                    "green": colors[name][1],
                    "blue": colors[name][2]
                },
                "horizontalAlignment": "CENTER",
                "textFormat": {
                    "foregroundColor": {
                        "red": 0,
                        "green": 0,
                        "blue": 0
                    },
                    "fontSize": 12,
                    "bold": True
                }
            })

    # NOTE: TESTED
    def create_shoebox_worksheet(self, box_name):
        worksheet = self.LOG.add_worksheet(title=box_name, rows=MAX_LOG_LENGTH - 1, cols=len(LOG_COLS))
        worksheet.insert_rows([LOG_COLS], 1)

        def end_col(num):
            # Turn column number to column letter
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

    # TODO: TEST
    def admin_routine(self):
        # Connect to Admin App. Keep receiving commands until a "done" command is received.
        # Call necessary methods when a command is received.
        self.accept()
        while True:
            command = self.get_msg()
            self.commands[command]()
            if command == b"done":
                return

    def accept(self):
        # Connect to Admin object (Admin application).
        # When connection is successful, the Admin App will notify Admin
        self.sock.bind(RPi_address)
        self.sock.listen(1)
        self.admin, _ = self.sock.accept()

    def add_access(self, kind="student"):
        # Scan ID. Send ID to Admin App. Receive info (id,String Identifier).
        # Update local files accordingly.
        if kind == "shoebox":
            scanned = self.reader.scan_until()
        else:
            while True:
                scanned = self.rfid.read_card()
                if scanned:
                    break


        self.send_msg(scanned.encode())
        identifier = self.get_msg()
        identifier = identifier.decode()
        new_entry = {scanned: identifier}

        t1 = threading.Thread(target=lambda: self.update_online_access(new_entry=new_entry, record=kind))
        t1.start()

        # If Shoebox, also create its LOG worksheet
        shoebox = kind == "shoebox"
        if shoebox:
            t2 = threading.Thread(target=lambda: self.create_shoebox_worksheet(identifier))
            t2.start()

    def update_online_access(self, new_entry, record="student"):
        # Upload new Students/Admins/Inventory as they are scanned into the system
        worksheet_name = {
            "student": "STUDENTS",
            "admin": "ADMINS",
            "shoebox": "INVENTORY"
        }
        worksheet = self.ACCESS.worksheet(worksheet_name[record])
        worksheet.insert_rows([list(new_entry)], 2)

    @staticmethod
    def update_local_access(new_entry, record="student"):
        # Load current json, add entry to it, dump it back
        file = STUDENTS_PATH if record == "student" else ADMINS_PATH if record == "admin" else INVENTORY_PATH
        with open(file, "r") as outfile:
            temp = json.load(outfile)

        temp.update(new_entry)
        with open(file, "w") as outfile:
            json.dump(temp, outfile, indent=4)
