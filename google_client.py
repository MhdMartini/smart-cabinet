import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import set_row_height, set_column_width, DataValidationRule, \
    set_data_validation_for_cell_range, BooleanCondition
import string

CREDENTIALS_PATH = r"/home/pi/Desktop/credentials.json"

LOG_SHEET = "Log_TEST2"
ACCESS_SHEET = "Access_TEST2"
MAX_LOG_LENGTH = 1000
LOG_COLS = ["user", "RFID", "action", "timestamp"]
USER_GMAIL = "smartcabinet.uml@gmail.com"

class_validation_rule = DataValidationRule(
    BooleanCondition("ONE_OF_LIST", ["Circuits I", "Circuits II", "Electronics I", "Electronics II", "Other"]),
    showCustomUi=True
)

access_validation_rule = DataValidationRule(
    BooleanCondition("ONE_OF_LIST", ["YES", "NO"]),
    showCustomUi=True
)


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


class GoogleClient:
    LOG = None  # Log Google Spreadsheet
    ACCESS = None  # Access Google Spreadsheet

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
            self.create_intro_sheet(self.LOG)
            self.LOG.share(USER_GMAIL, perm_type='user', role='writer')

        try:
            self.ACCESS = client.open(ACCESS_SHEET)
        except gspread.exceptions.SpreadsheetNotFound:
            self.ACCESS = client.create(ACCESS_SHEET)
            self.create_intro_sheet(self.ACCESS)
            self.create_access_worksheets()
            self.ACCESS.share(USER_GMAIL, perm_type='user', role='writer')

    @staticmethod
    def create_intro_sheet(sheet):
        # Create the Introductory Worksheet
        worksheet = sheet.add_worksheet(title="SMART CABINET", rows=1, cols=1)
        sheet.del_worksheet(sheet.sheet1)
        worksheet.insert_rows(INTRO_SHEET, 1)

        set_column_width(worksheet, 'A', 1000)
        set_row_height(worksheet, '1:4', 70)
        set_row_height(worksheet, '5:28', 34)

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
        headers = {
            "ADMINS": ["Admin", "RFID", "ACCESS"],
            "STUDENTS": ["Student", "RFID", "Class", "ACCESS"],
            "INVENTORY": ["Item", "RFID"]
        }
        for sheet_name, sheet_cols in headers.items():
            num_cols = len(sheet_cols)
            worksheet = self.ACCESS.add_worksheet(title=sheet_name, rows=1, cols=num_cols)
            worksheet.insert_rows([sheet_cols], 1)

            worksheet.format(f"A1:{string.ascii_uppercase[num_cols - 1]}1", {
                "backgroundColor": {
                    "red": colors[sheet_name][0],
                    "green": colors[sheet_name][1],
                    "blue": colors[sheet_name][2]
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
            if sheet_name == "STUDENTS":
                # Add a column which specified which class the student is in
                class_col = string.ascii_uppercase[sheet_cols.index("Class")]
                set_data_validation_for_cell_range(worksheet, class_col, class_validation_rule)

            if sheet_name != "INVENTORY":
                # Add a Yes/No column to grant/deny access
                access_col = string.ascii_uppercase[sheet_cols.index("ACCESS")]
                set_data_validation_for_cell_range(worksheet, access_col, access_validation_rule)

    # NOTE: TESTED
    def create_shoebox_worksheet(self, box_name):
        worksheet = self.LOG.add_worksheet(title=box_name, rows=MAX_LOG_LENGTH - 1, cols=len(LOG_COLS))
        worksheet.insert_rows([LOG_COLS], 1)

        cols_num = len(LOG_COLS)
        worksheet.format(f"A1:{string.ascii_uppercase[cols_num - 1]}1", {
            "backgroundColor": {
                "red": 0.2,
                "green": 0.2,
                "blue": 0.7
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
        # Make the "timestamp" column wider
        time_col = LOG_COLS.index("timestamp")
        time_col = string.ascii_uppercase[time_col]
        set_column_width(worksheet, time_col, 250)
        return worksheet

    def update_online_access(self, new_entry, record="student"):
        # Upload new Students/Admins/Inventory as they are scanned into the system
        worksheet_name = {
            "student": "STUDENTS",
            "admin": "ADMINS",
            "shoebox": "INVENTORY"
        }
        worksheet = self.ACCESS.worksheet(worksheet_name[record])
        worksheet.insert_rows([new_entry], 2)
