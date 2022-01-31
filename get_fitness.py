from __future__ import print_function

from datetime import datetime
import datetime as dtm
import os.path
import requests
import sys
import argparse
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.blood_glucose.read',
    'https://www.googleapis.com/auth/fitness.blood_pressure.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.body_temperature.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read',
    'https://www.googleapis.com/auth/fitness.location.read',
    'https://www.googleapis.com/auth/fitness.nutrition.read',
    'https://www.googleapis.com/auth/fitness.oxygen_saturation.read',
    'https://www.googleapis.com/auth/fitness.reproductive_health.read',
    'https://www.googleapis.com/auth/fitness.sleep.read'
]


def main():
    end_date = datetime.now()
    start_date = end_date - dtm.timedelta(hours=24)

    str_start_date = start_date.strftime("%Y-%m-%d %H:00:00")
    str_end_date = end_date.strftime("%Y-%m-%d %H:00:00")

    token = check_oauth()
    data = get_fitness_data(token, 1, str_start_date, str_end_date)
    parse_data(data)


def check_oauth():
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
        return(creds.token)

    except HttpError as error:
        fatal_error(error)


def get_fitness_data(token, bucket, start_date, end_date):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"

    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json;encoding=utf-8',
    }

    body = {
        "aggregateBy": [{
            "dataTypeName": "com.google.weight",
            "dataSourceId": "derived:com.google.weight:com.google.android.gms:merge_weight"
        }, {
            "dataTypeName": "com.google.heart_rate.bpm",
            "dataSourceId": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
        }, {
            "dataTypeName": "com.google.step_count.delta",
            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
        }, {
            "dataTypeName": "com.google.distance.delta",
            "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta"
        }, {
            "dataTypeName": "com.google.calories.expended",
            "dataSourceId": "derived:com.google.calories.bmr:com.google.android.gms:merged"
        }],
        "bucketByTime": {"durationMillis": millihours(bucket)},
        "startTimeMillis": millidate(start_date),
        "endTimeMillis": millidate(end_date)
    }

    response = requests.post(url, headers=headers, json=body)
    payload = response.json()

    return(payload)

# very dirty but just for visualisation (temporary) 
def parse_data(data):

    for bucket in data['bucket']:
        print("")
        print(" ", str(dtm.datetime.fromtimestamp(int(bucket['startTimeMillis'])/1000.0)))
        print(" ", str(dtm.datetime.fromtimestamp(int(bucket['endTimeMillis'])/1000.0)))
        print("")
        for dataset in bucket['dataset']:
            if dataset['point']:
                for point in dataset['point']:
                    print("  ", str(dtm.datetime.fromtimestamp(int(point['startTimeNanos'])/1000000000.0)))
                    print("  ", str(dtm.datetime.fromtimestamp(int(point['endTimeNanos'])/1000000000.0)))
                    print("  ", point['dataTypeName'])
                    #print("  ", point['originDataSourceId'])
                    print("")
                    for value in point['value']:
                        if 'intVal' in value:
                            print("   ", value['intVal'])
                        if 'fpVal' in value:
                            print("   ", value['fpVal'])
                    print("")
        print("----------------------------------------------------------------------")


def millidate(date):
    try:
        if len(date) == 10:
            dt = datetime.strptime(date, '%Y-%m-%d')
        elif len(date) == 19:
            dt = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        else:
            raise ValueError(
                "time data '%s' does not match format '%%Y-%%m-%%d' OR '%%Y-%%m-%%d %%H:%%M:%%S'" % (date))

        return(int(dt.timestamp() * 1000))

    except ValueError as error:
        fatal_error(error)


def millihours(hours):
    hr = hours * 60 * 60 * 1000
    return(hr)


def fatal_error(error):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    err_ln = ("%s | %s %s" % (dt_string, error, "\n"))

    print(err_ln)

    with open('errors.txt', 'a') as err_log:
        err_log.write(err_ln)

    sys.exit(1)


if __name__ == '__main__':
    main()
