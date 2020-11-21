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


class googleCamera:
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

    @staticmethod  # Sync camera files from a folder in pi to google drive
    def camera(service):
        # Get list of filenames in local folder at a directory
        local_file = []
        for file in os.listdir("/home/pi/Desktop/cabinet"):
            local_file.append(file)

        # Get list of filenames in google drive folder
        response = service.files().list(q="mimeType='video/h264'", spaces='drive',
                                        fields='nextPageToken, files(id, name)').execute()
        google_file = pd.DataFrame.from_dict(response)
        # for file in response.get('files', []):
        #     google_file.append(file.get('name'))
        #     print('Found file: %s (%s)' % (file.get('name'), file.get('id')))

        # Upload new file to google drive
        for local in local_file:  # Go through the list of local file
            if local not in google_file['filename'].values:  # If that local file is not in google file list, upload
                file_metadata = {'name': local}  # Filename record
                media = MediaFileUpload(os.path.join("/home/pi/Desktop/cabinet", local))  # Get new file location
                service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                google_file.append(local)  # Update google_file list to include the file being uploaded

        # Delete old file from google drive
        for external in google_file['filename'].values:  # Go through the list of new file in google
            if external not in local_file:
                service.files().delete(fileID=google_file['fileID'].values).execute()


if __name__ == '__main__':
	# Initialize to link with google account
    drive_service_v3 = googleCamera.login('credentials_drive.json', 'drive_v3')
    # Run this to sync the file.
    googleCamera.drive_file_list(drive_service_v3)
