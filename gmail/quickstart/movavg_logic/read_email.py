from __future__ import print_function

import json
import numpy as np
import os.path
import pickle
import time
from apiclient import errors, discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import zmq_constants
import logging

logger = logging.getLogger(__name__)


# If modifying these scopes, delete the file token.pickle.
#SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPES = ['https://mail.google.com/']


class read_unread_mail():

    def __init__(self, label='UNREAD'):
        self.service = None
        self.messages = None
        self.label = label
        self.msg = None
        self.userId = 'me'

    def ModifyMessage(service, user_id, msg_id, msg_labels):
        # https://developers.google.com/gmail/api/v1/reference/users/messages/modify#python

        try:
            message = service.users().messages().modify(userId=user_id, id=msg_id,
                                                        body=msg_labels).execute()

            # label_ids = message['labelIds']
            # print('Message ID: %s - Marked as read.' % (msg_id))
            return message
        except errors.HttpError as error:
            logger.debug('An error occurred: %s' % error)
            return None

    def read(self):
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

        self.service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        # Call the Gmail API to fetch INBOX
        results = self.service.users().messages().list(userId=self.userId, labelIds=[self.label]).execute()
        messages = results.get('messages', [])
        _ = time.time()
        # print(np.round(_-start,2))
        print_msg = ''
        if not messages:
            # print("No messages found")
            return zmq_constants.constants().unread_message
        else:
            return messages

    def get_msg_body(self, msg):
        _msg = self.service.users().messages().get(userId=self.userId, id=msg['id']).execute()
        msg_body = _msg['snippet']
        # Mark email as read
        try:
            msg_labels = {'removeLabelIds': [self.label]}
            message = self.service.users().messages().modify(userId=self.userId, id=msg['id'],
                                                             body=msg_labels).execute()
            # print('Message ID: %s - Marked as read.' % (msg_id))
        except errors.HttpError as error:
            logger.debug('An error occurred: %s' % error)
            return None

        return msg_body


"""
        for msg in messages:
            _msg = service.users().messages().get(userId='me', id=msg['id']).execute()
            msg_body = _msg['snippet']
            if zmq_constants.constants().msg_scope in msg_body:
                if zmq_constants.constants().BUY_SEARCH in msg_body:
                    print_msg = "%s %s" % 
                    (zmq_constants.constants().zmq_buy_filter, msg_body.split()[2])
                elif zmq_constants.constants().SELL_SEARCH in msg_body:
                    print_msg = "%s %s" % 
                    (zmq_constants.constants().zmq_sell_filter, msg_body.split()[2])
            else:
                print(msg_body)
                return None
            # Mark email as read
            _msg = ModifyMessage(service, user_id='me', msg_id=msg['id'], msg_labels={'removeLabelIds': [label]})
    end = time.time()
    # print("Time taken:", np.round(end-start,2),"Seconds")
    return print_msg
"""