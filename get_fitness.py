from __future__ import print_function

import datetime
import time
import os.path
import requests
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly'
    ,'https://www.googleapis.com/auth/fitness.body.read'
    ,'https://www.googleapis.com/auth/fitness.activity.read'
    ,'https://www.googleapis.com/auth/fitness.blood_glucose.read'
    ,'https://www.googleapis.com/auth/fitness.blood_pressure.read'
    ,'https://www.googleapis.com/auth/fitness.body.read'
    ,'https://www.googleapis.com/auth/fitness.body_temperature.read'
    ,'https://www.googleapis.com/auth/fitness.heart_rate.read'
    ,'https://www.googleapis.com/auth/fitness.location.read'
    ,'https://www.googleapis.com/auth/fitness.nutrition.read'
    ,'https://www.googleapis.com/auth/fitness.oxygen_saturation.read'
    ,'https://www.googleapis.com/auth/fitness.reproductive_health.read'
    ,'https://www.googleapis.com/auth/fitness.sleep.read'
    ]

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        
        headers = {
            'Authorization': f"Bearer {str(creds.token)}",
            'Content-Type' : 'application/json;encoding=utf-8',
        }

        body = {
                "aggregateBy": [{
                    "dataTypeName": "com.google.weight",
                    "dataSourceId": "derived:com.google.weight:com.google.android.gms:merge_weight"
                },{
                    "dataTypeName": "com.google.heart_rate.bpm",
                    "dataSourceId": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
                },{
                    "dataTypeName": "com.google.step_count.delta",
                    "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
                },{
                    "dataTypeName": "com.google.distance.delta",
                    "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta"
                },{
                    "dataTypeName": "com.google.calories.expended",
                    "dataSourceId": "derived:com.google.calories.bmr:com.google.android.gms:merged"
                }],
            "bucketByTime": { "durationMillis": 86400000/24},
            "startTimeMillis": round((time.time() * 1000) - (86400000*20)),
            "endTimeMillis": round(time.time() * 1000)
        }

        response = requests.post(url, headers=headers, json=body)

        print(response.text)
        
    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()