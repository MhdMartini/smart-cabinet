import socket, json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import set_row_height, set_column_width

RPi_address = ("10.0.0.157", 4236)
MAX_LENGTH = 1024

ADMINS_PATH = r"/home/pi/admin.json"
INVENTORY_PATH = r"/home/pi/inventory.json"
STUDENTS_PATH = r"/home/pi/students.json"

LOCAL_LOG_PATH = r"/home/pi/log.pickle"
CREDENTIALS_PATH = r"/home/pi/credentials.json"
LOG_SHEET = "log"
MAX_LOG_LENGTH = 1000
LOG_COLS = ["user", "RFID", "action", "timestamp"]
USER_GMAIL = "smartcabinet.uml@gmail.com"


INTRO_SHEET = [
    ["S M A R T   C A B I N E T"],
    ["UNIVERSITY OF MASSACHUSETTS LOWELL"],
    ["FRANCIS COLLEGE OF ENGINEERING"],
    ["ELECTRICAL AND COMPUTER ENGINEERING"],
    ["For software support:"],
    ["mohamed_martini@student.uml.edu"]
]


class PiServer:
    admin = None  # Admin object to handle communication with Admin App
    LOG = None  # LOG Google Spreadsheet

    def __init__(self, reader, rfid):
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

    def create_new_worksheet(self, box_name):
        worksheet = self.LOG.add_worksheet(title=box_name, rows=MAX_LOG_LENGTH - 1, cols=len(LOG_COLS))
        worksheet.insert_row(LOG_COLS, 1)

        def end_col(num):
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

    def launch_google_client(self):
        # Authorize, and create log spreadsheet if it does not exist
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(credentials)

        try:
            self.LOG = client.open(LOG_SHEET)
        except gspread.exceptions.SpreadsheetNotFound:
            self.LOG = client.create(LOG_SHEET)
            self.LOG.share(USER_GMAIL, perm_type='user', role='writer')

            # Create Introductory Sheet in place of default one
            worksheet = self.LOG.add_worksheet(title="SMART CABINET", rows=1, cols=1)
            self.LOG.del_worksheet(self.LOG.sheet1)
            worksheet.insert_rows(INTRO_SHEET, 1)
            set_column_width(worksheet, 'A', 1000)
            set_row_height(worksheet, '1:4', 70)
            worksheet.format("A1:A4", {
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
            worksheet.format("A5:A6", {
                "backgroundColor": {
                    "red": 0.2,
                    "green": 0.2,
                    "blue": 0.2
                },
                "horizontalAlignment": "LEFT",
                "textFormat": {
                    "foregroundColor": {
                        "red": 1,
                        "green": 0.2,
                        "blue": .2
                    },
                    "fontSize": 12,
                    "bold": True
                }
            })

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
            while True:
                try:
                    scanned = self.rfid.read_card()  # SAM: Scan ID. Replace the next line
                except self.rfid.SerialTimeoutException:
                    continue

        self.send_msg(scanned.encode())
        identifier = self.get_msg()
        new_entry = {scanned: identifier.decode()}

        self.update_record(new_entry=new_entry, record=kind)

    def update_record(self, new_entry, record="student"):
        # Load current json, add entry to it, dump it back
        file = STUDENTS_PATH if record == "student" else ADMINS_PATH if record == "admin" else INVENTORY_PATH
        with open(file, "r") as outfile:
            temp = json.load(outfile)

        temp.update(new_entry)
        with open(file, "w") as outfile:
            json.dump(temp, outfile, indent=4)

        # If shoebox, create the google worksheet for that shoebox
        shoebox = record == "shoebox"

        if shoebox:
            box_name = list(new_entry.values())[0]
            self.create_new_worksheet(box_name)

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
