from __future__ import print_function
import pickle
import json
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import time
import numpy as np
import zmq_constants

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
MSG_SCOPE = 'ALERT ON'
BUY_SEARCH = zmq_constants.constants().BUY_SEARCH
SELL_SEARCH = zmq_constants.constants().SELL_SEARCH

def ModifyMessage(service, user_id, msg_id, msg_labels):
    #https://developers.google.com/gmail/api/v1/reference/users/messages/modify#python

    try:
        message = service.users().messages().modify(userId=user_id, id=msg_id,
                                                    body=msg_labels).execute()

        #label_ids = message['labelIds']
        print('Message ID: %s - Marked as read.' % (msg_id))
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def read_email():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    start = time.time()
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    # Call the Gmail API to fetch INBOX
    results = service.users().messages().list(userId='me',labelIds = ['UNREAD']).execute()
    messages = results.get('messages', [])
    _ = time.time()
    #print(np.round(_-start,2))
    if not messages:
        #print("No messages found")
        print_msg = "No messages found."
    else:
        for msg in messages:
            _msg = service.users().messages().get(userId='me', id=msg['id']).execute()
            msg_body = _msg['snippet']
            if zmq_constants.constants().msg_scope in msg_body:
                if BUY_SEARCH in msg_body:
                    print_msg = "%s %s" % (zmq_constants.constants().zmq_buy_filter, msg_body.split()[2])
                elif SELL_SEARCH in msg_body:
                    print_msg = "%s %s" % (zmq_constants.constants().zmq_sell_filter, msg_body.split()[2])
            #Mark email as read
            ModifyMessage(service,user_id='me',msg_id=msg['id'], msg_labels={'removeLabelIds': ['UNREAD']})
    end = time.time()
    #print("Time taken:", np.round(end-start,2),"Seconds")
    return print_msg
