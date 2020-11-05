from __future__ import print_function
import pickle
import os
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

path = os.path.dirname(os.path.realpath(__file__))
# Full, permissive scope to access all of a user's files, excluding the Application Data folder
scopes = ['https://www.googleapis.com/auth/drive']


class GoogleApi:
    @staticmethod  # Universal use
    def login(credentials_filename, service_type):  # Initialization setup for secure connection with google
        credential = None  # Stored code to connect to google
        token_file = os.path.join(path, credentials_filename.split('.')[0]+'.pickle')  # Convert from json to pickle
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                credential = pickle.load(token)
        if not credential or not credential.valid:  # If there are no (valid) credentials available, let the user log in
            if credential and credential.expired and credential.refresh_token:
                credential.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(os.path.join(path, credentials_filename), scopes)
                credential = flow.run_local_server(port=0)
            with open(token_file, 'wb') as token:  # Save the credentials for the next run
                pickle.dump(credential, token)

        if service_type == 'drive_v3':  # Service to drive version 3
            service = build('drive', 'v3', credentials=credential)
        elif service_type == 'drive_v2':  # Service to drive version 2
            service = build('drive', 'v2', credentials=credential)
        elif service_type == 'sheets':  # Service to sheets version 4
            service = build('sheets', 'v4', credentials=credential)
        
        return service

    @staticmethod  # Universal use
    def drive_upload(service, filename):  # v3 Upload new file TODO: check file size <5MB
        file_metadata = {'name': filename}  # Filename record
        media = MediaFileUpload(os.path.join(path, filename))  # Get new file location
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print('Successfully uploaded file (ID): {} ({})'.format(filename, file.get('id')))

    @staticmethod  # Universal use
    def drive_update(service, filename, file_id):  # v2 Update new revision of file TODO: check file size <5MB
        file_original = service.files().get(fileId=file_id).execute()  # Get old file drive ID
        media = MediaFileUpload(os.path.join(path, filename))  # Get new file location
        file_update = service.files().update(fileId=file_id, body=file_original, newRevision=True,
                                             media_body=media).execute()  # Replace old file with new file
        print('Successfully updated file (ID): {} ({})'.format(filename, file_update.get('id')))

    @staticmethod  # Universal use
    def drive_file_sync(service_v3, service_v2, filename):  # Get file_id based of filename and upload/update file
        file_id = GoogleApi.drive_file_id(service_v3, filename)
        if file_id is None:  # File does not exist, upload
            GoogleApi.drive_upload(service_v3, filename)
        else:  # File already exist, update
            GoogleApi.drive_update(service_v2, filename, file_id)

    @staticmethod  # Universal use
    def drive_file_id(service, filename):  # Get file_id based of filename
        # Get first 25 files on drive
        results = service.files().list(pageSize=25, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        file_id = None
        if not items:  # Empty drive, return none
            return None
        else:
            for item in items:  # Check if file already exist
                if item['name'] == filename:  # Get the file_id if exist
                    file_id = item['id']

        if file_id is None:  # File does not exist, return none
            return None
        else:  # File already exist, return file_id
            return file_id

    @staticmethod  # Universal use
    def sheet_clear(service, spreadsheet_id, sheet_id):  # Clear the entire spreadsheet values (format remain)
        sheet_body = {'requests': [{'updateCells': {'range': {'sheetId': sheet_id}, 'fields': 'userEnteredValue'}}]}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=sheet_body).execute()

    @staticmethod  # Universal use
    def sheet_read(service, spreadsheet_id, ranges):  # Read all of the values in the sheet
        read = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=ranges).execute()
        return read.get('values', [])

    @staticmethod  # Universal use
    def sheet_write_row(service, spreadsheet_id, ranges, value):  # Write based on user entered in row terms
        sheet_body = {'majorDimension': 'ROWS', 'values': value}
        service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=ranges,
                                               valueInputOption='USER_ENTERED', body=sheet_body).execute()

    @staticmethod  # Customized to ID Scanner only
    def sheet_create_regular(service, inside_data):  # Create sheet for regular ID list for backup
        # Create new spreadsheet, set the entire sheets properties, and set a single cell properties
        spreadsheet_body = {'properties': {'title': 'Regular ID Access List', 
                                           'locale': 'en_US', 
                                           'autoRecalc': 'ON_CHANGE', 
                                           'timeZone': 
                                           'America/New_York'},
                            'sheets': [{'properties': {'sheetId': 0, 
                                                       'title': 'Regular ID Access List', 
                                                       'gridProperties': {'columnCount': 9, 'frozenRowCount': 1}},
                                        'protectedRanges': [{'protectedRangeId': 0, 
                                                             'range': {'sheetId': 0, 'startRowIndex': 0,
                                                                       'startColumnIndex': 0, 'endColumnIndex': 4},
                                                             'description': 'Do not change!',
                                                             'warningOnly': True}]},
                                       {'properties': {'sheetId': 1, 
                                                       'title': 'Class Type', 
                                                       'gridProperties': {'rowCount': 21, 'columnCount': 1,
                                                                          'frozenRowCount': 1}},
                                        'data': [{'startRow': 0,
                                                  'startColumn': 0,
                                                  'rowData': [{'values': [{'userEnteredFormat': {
                                                      'horizontalAlignment': 'CENTER',
                                                      'wrapStrategy': 'WRAP',
                                                      'textFormat': {'bold': True}}}]}],
                                                  'columnMetadata': [{'pixelSize': 200}]}]}]}
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        # Set multiple cells properties for 'Regular ID Access List'
        sheet1_dimensions = {'properties': {'pixelSize': 199},
                             'fields': 'pixelSize',
                             'range': {'sheetId': 0, 'dimension': 'COLUMNS', 'startIndex': 0}}
        sheet1_title_format = {'range': {'sheetId': 0, 'endRowIndex': 1},
                               'cell': {'userEnteredFormat': {'horizontalAlignment': 'CENTER',
                                                              'textFormat': {'bold': True}}},
                               'fields': 'userEnteredFormat'}
        sheet1_validation1 = {'range': {'sheetId': 0, 'startRowIndex': 1, 'startColumnIndex': 7, 'endColumnIndex': 8},
                              'rule': {'condition': {'type': 'ONE_OF_RANGE',
                                                     'values': [{'userEnteredValue': "='Class Type'!A2:A21"}]},
                                       'inputMessage': 'Click and enter a value from the "Class Type" Tab',
                                       'showCustomUi': True}}
        sheet1_validation2 = {'range': {'sheetId': 0, 'startRowIndex': 1, 'startColumnIndex': 8, 'endColumnIndex': 9},
                              'rule': {'condition': {'type': 'ONE_OF_LIST',
                                                     'values': [{'userEnteredValue': "YES"}]},
                                       'inputMessage': 'If "YES", this user access will be revoked',
                                       'showCustomUi': True}}
        sheet1_band = {'bandedRange': {'bandedRangeId': 0,
                                       'range': {'sheetId': 0, 'startRowIndex': 0, 'startColumnIndex': 0},
                                       'rowProperties': {'headerColorStyle': {'themeColor': 'ACCENT1'},
                                                         'firstBandColorStyle': {'themeColor': 'BACKGROUND'},
                                                         'secondBandColorStyle': {'rgbColor': {'red': 23,
                                                                                               'green': 15,
                                                                                               'blue': 1,
                                                                                               'alpha': 0.5}}}}}
        sheet1_body = {'requests': [{'updateDimensionProperties': sheet1_dimensions},
                                    {'repeatCell': sheet1_title_format},
                                    {'setDataValidation': sheet1_validation1},
                                    {'setDataValidation': sheet1_validation2},
                                    {'addBanding': sheet1_band}]}
        sheet1 = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=sheet1_body).execute()

        # Input basic data for 'Regular ID Access List'
        sheet1_values = [['Date Added', 'Date of Last Access', 'Facility Access Code #', 'Card ID #',
                          'First Name', 'Last Name', 'School E-mail Address', 'Class Type', 'Delete?']]
        for row in inside_data:
            tmp = ["=TODAY()", ""]
            tmp.extend(row.split(':'))
            tmp.extend([""] * 5)
            sheet1_values += [tmp]
        GoogleApi.sheet_write_row(service, spreadsheet_id, 'Regular ID Access List!A1', sheet1_values)

        # Input basic data for 'Class Type'
        sheet2_values = [['Class Type (Add student class/roles below)', 'Basic EE Lab I', 'Basic EE Lab II',
                          'Electronics I Lab', 'Electronics II Lab', 'Grader', 'Others', 'Staff', 'TA']]
        sheet2_body = {'majorDimension': 'COLUMNS', 'values': sheet2_values}
        sheet2 = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range='Class Type!A1',
                                                        valueInputOption='USER_ENTERED', body=sheet2_body).execute()

        print('{0} cells updated.'.format(sheet2.get('updatedCells')))

    @staticmethod  # Customized to ID Scanner only
    def sheet_create_admin(service, inside_data):  # Create sheet for admin ID list for backup
        # Create new spreadsheet, set the entire sheets properties, and set a single cell properties
        spreadsheet_body = {'properties': {'title': 'Admin ID Access List', 
                                           'locale': 'en_US', 
                                           'autoRecalc': 'ON_CHANGE', 
                                           'timeZone': 
                                           'America/New_York'},
                            'sheets': [{'properties': {'sheetId': 0, 
                                                       'title': 'Admin ID Access List', 
                                                       'gridProperties': {'rowCount': 35, 'columnCount': 5,
                                                                          'frozenRowCount': 1}},
                                        'protectedRanges': [{'protectedRangeId': 0, 
                                                             'range': {'sheetId': 0, 'startRowIndex': 0,
                                                                       'startColumnIndex': 0, 'endColumnIndex': 1},
                                                             'description': 'Change with care!',
                                                             'warningOnly': True}]}]}
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        # Set multiple cells properties for 'Admin ID Access List'
        sheet_title_format = {'range': {'sheetId': 0, 'startRowIndex': 1, 'startColumnIndex': 1},
                              'cell': {'userEnteredFormat': {'numberFormat': {'type': 'TEXT'}}},
                              'fields': 'userEnteredFormat.numberFormat'}
        sheet_band = {'bandedRange': {'bandedRangeId': 0,
                                      'range': {'sheetId': 0, 'startRowIndex': 0, 'startColumnIndex': 0},
                                      'rowProperties': {'headerColorStyle': {'themeColor': 'ACCENT3'},
                                                        'firstBandColorStyle': {'themeColor': 'BACKGROUND'},
                                                        'secondBandColorStyle': {'rgbColor': {'red': 5,
                                                                                              'green': 6,
                                                                                              'blue': 25,
                                                                                              'alpha': 0.5}}}}}
        sheet_body = {'requests': [{'repeatCell': sheet_title_format}, {'addBanding': sheet_band}]}
        sheet = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=sheet_body).execute()

        # Set multiple cells properties for 'Admin ID Access List'
        sheet_dimensions = {'properties': {'pixelSize': 255},
                            'fields': 'pixelSize',
                            'range': {'sheetId': 0, 'dimension': 'COLUMNS', 'startIndex': 0}}
        sheet_title_format = {'range': {'sheetId': 0, 'endRowIndex': 1},
                              'cell': {'userEnteredFormat': {'horizontalAlignment': 'CENTER',
                                                             'textFormat': {'bold': True}}},
                              'fields': 'userEnteredFormat'}
        sheet_body = {'requests': [{'updateDimensionProperties': sheet_dimensions}, {'repeatCell': sheet_title_format}]}
        sheet = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=sheet_body).execute()

        # Input basic data for 'Admin ID Access List'
        sheet_values = [['Date of Last Access', 'ID # (Copy and Paste from "ID_log.log")',
                         'First Name', 'Last Name', 'School E-mail Address']]
        for row in inside_data:
            tmp = [""]
            tmp.extend([row])
            tmp.extend([""] * 3)
            sheet_values += [tmp]

        GoogleApi.sheet_write_row(service, spreadsheet_id, 'Admin ID Access List!A1', sheet_values)
        
        print('sheet_create_admin: {0} cells updated.'.format(sheet.get('updatedCells')))

    @staticmethod  # Customized to ID Scanner only
    def sheet_update_regular(service_drive, service_sheet, filename, inside_data):
        spreadsheet_id = GoogleApi.drive_file_id(service_drive, filename)
        if spreadsheet_id is None:  # If spreadsheet not found, create and restore
            GoogleApi.sheet_create_regular(service_sheet)
            print("sheet_update_regular: Successfully created")
        else:  # If spreadsheet found, get new data to compare with local
            read = GoogleApi.sheet_read(service_sheet, spreadsheet_id, 'Regular ID Access List')
            # read = service_sheet.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
            #                                                  range='Regular ID Access List').execute().get('values', [])
            if len(read[0]) != len(read[1]):  # Assumes row 0 has more than row 1
                read[1].extend([""] * (len(read[0]) - len(read[1])))  # Fill in the rest of column with empty string

            for row in read:
                print(row)
            df = pd.DataFrame(read[1:], columns=read[0])
            df['outside_data'] = df['Facility Access Code #']+":"+df['Card ID #']  # Add column (match local data style)
            for number in inside_data:  # Admin add new user via ID scanner
                if number not in df['outside_data'].values:  # If local data not found, add to the df
                    data = pd.DataFrame({'Date Added': ['=TODAY()'], 'Facility Access Code #': number.split(':')[0],
                                         'Card ID #': number.split(':')[1], 'outside_data': number})
                    df = df.append(data, ignore_index=True)

            for number in df['outside_data'].values:  # Admin remove user via ID scanner
                if number not in inside_data:  # If df data not found in local, remove from local
                    df = df[df['outside_data'] != number]
            df = df[df['Delete?'] != "YES"]  # Remove those data that admin remove user via sheet marking
            res = df['outside_data'].tolist()  # Get the new local data
            df.drop(['outside_data'], axis=1, inplace=True)  # Cleaning data to original format
            df = df.fillna("")   # Replace 'NaN' with empty string
            GoogleApi.sheet_clear(service_sheet, spreadsheet_id, 0)  # Clear entire sheet
            GoogleApi.sheet_write_row(service_sheet, spreadsheet_id, 'Regular ID Access List', [read[0]]+df.values.tolist())
            print("sheet_update_regular: Successfully updated")
            return res  # Return the updated list of regular user for local data

    @staticmethod  # Customized to ID Scanner only
    def sheet_update_admin(service_drive, service_sheet, filename):  # Get new admin list from google spreadsheet
        spreadsheet_id = GoogleApi.drive_file_id(service_drive, filename)
        if spreadsheet_id is None:  # If spreadsheet not found, create and restore
            GoogleApi.sheet_create_admin(service_sheet)
            print("sheet_update_admin: Successfully created")
        else:  # Pull new information from spreadsheet to update local admin list
            read = GoogleApi.sheet_read(service_sheet, spreadsheet_id, 'Admin ID Access List')
            # read = service_sheet.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
            #                                                  range='Admin ID Access List').execute().get('values', [])
            df = pd.DataFrame(read[1:], columns=read[0])
            res = df['ID # (Copy and Paste from "ID_log.log")'].tolist()
            print("sheet_update_admin: Successfully updated")
            return res  # Return the new admin list for local data

    @staticmethod  # Customized to ID Scanner only
    def sheet_update_date(service_drive, service_sheet, filename, data):
        spreadsheet_id = GoogleApi.drive_file_id(service_drive, filename)
        read = GoogleApi.sheet_read(service_sheet, spreadsheet_id, filename)
        # read = service_sheet.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=filename).execute().get('values', [])
        print(read)
        if len(read[0]) != len(read[1]):  # assumes row 0 has more than row 1
            read[1].extend([""] * (len(read[0]) - len(read[1])))

        df = pd.DataFrame(read[1:], columns=read[0])
        if filename == 'Regular ID Access List':
            row = df.loc[(df['Facility Access Code #'] == data.split(':')[0]) & (df['Card ID #'] == data.split(':')[1])].index.array[0]
            sheet_body = {'range': filename+'!B'+str(row+2), 'values': [['=TODAY()']]}
            service_sheet.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=filename+'!B'+str(row+2),
                                                         valueInputOption='USER_ENTERED', body=sheet_body).execute()
        elif filename == 'Regular ID Access List':
            row = df.loc(df['ID # (Copy and Paste from "ID_log.log")'] == data).index.array[0]
            sheet_body = {'range': filename+'!A'+str(row+2), 'values': [['=TODAY()']]}
            service_sheet.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=filename+'!A'+str(row+2),
                                                         valueInputOption='USER_ENTERED', body=sheet_body).execute()
        else:
            print("Error: sheet_update_date")


if __name__ == '__main__':
    drive_service_v3 = GoogleApi.login('credentials_drive.json', 'drive_v3')
    # drive_service_v2 = GoogleApi.login('credentials_drive.json', 'drive_v2')
    # GoogleApi.drive_file_list(drive_service_v3)
    # GoogleApi.drive_file_sync(drive_service_v3, drive_service_v2, 'ID_log.log')
    # GoogleApi.drive_file_list(drive_service_v3)
    sheets_service = GoogleApi.login('credentials_drive.json', 'sheets')
    # file_id = GoogleApi.drive_file_id(drive_service_v3, 'Test')
    # file_id = GoogleApi.drive_file_id(drive_service_v3, 'Regular ID Access List')
    # file_id = GoogleApi.drive_file_id(drive_service_v3, 'Admin ID Access List')

    fake_user_ids = ['12312:23743', '5656:465', '123144:2314356', '4512656:55143', '2:2', "text:fortesting"]
    GoogleApi.sheet_create_regular(sheets_service, fake_user_ids)
    # GoogleApi.sheet_create_admin(sheets_service, fake_user_ids)

    # GoogleApi.sheet_update_regular(drive_service_v3, sheets_service, 'Regular ID Access List', fake_user_ids)
    # GoogleApi.sheet_update_admin(drive_service_v3, sheets_service, 'Admin ID Access List')
    # GoogleApi.sheet_update_date(drive_service_v3, sheets_service, 'Regular ID Access List', '2:2')
