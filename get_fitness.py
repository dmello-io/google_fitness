#!/home/kayden/Projects/Google/Fit/venv/bin/python

from __future__ import print_function

from datetime import datetime
import datetime as dtm
import os
import requests
import sys

import mysql.connector as database

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
    start_date = end_date - dtm.timedelta(days=3)
    str_start_date = start_date.strftime("%Y-%m-%d %H:00:00")
    str_end_date = end_date.strftime("%Y-%m-%d %H:00:00")
    token = check_oauth()
    data = get_fitness_data(token, .25, str_start_date, str_end_date)
    parsed = parse_data(data)
    update_database(parsed)


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
        "bucketByTime": {"durationMillis": hours_to_millis(bucket)},
        "startTimeMillis": date_to_millis(start_date),
        "endTimeMillis": date_to_millis(end_date)
    }

    response = requests.post(url, headers=headers, json=body)
    payload = response.json()

    return(payload)


def parse_data(data):
    parsed = []

    class entry:
        data_type = None
        start_time = None
        end_time = None
        average = None
        maximum = None
        minimum = None
        total = None

    for bucket in data['bucket']:
        for dataset in bucket['dataset']:
            if dataset['point']:
                row = entry()
                i = 0
                row.start_time = date_from_millis(bucket['startTimeMillis'])
                row.end_time = date_from_millis(bucket['endTimeMillis'])
                row.data_type = dataset['point'][i]['dataTypeName']
                point = dataset['point'][i]['value']

                if len(point) == 1:
                    if 'fpVal' in point[0]:
                        row.total = point[0]['fpVal']
                    elif 'intVal' in point[0]:
                        row.total = point[0]['intVal']
                elif len(point) == 3:
                    row.average = point[0]['fpVal']
                    row.maximum = point[1]['fpVal']
                    row.minimum = point[2]['fpVal']

                i = i + 1
                parsed.append(row.__dict__)
    return(parsed)


def update_database(parsed_data):
    username = os.environ.get("pysql_username")
    password = os.environ.get("pysql_password")

    connection = database.connect(
        user=username,
        password=password,
        host="tofu",
        port=3306,
        database="google_fitness"
    )

    cursor = connection.cursor()

    for row in parsed_data:
        split_row_type = row['data_type'].split('.')
        row_type = str(split_row_type[2]).replace("'", "")

        if row_type in ('weight', 'heart_rate', 'calories'):
            statement = "INSERT INTO {}(start_time, end_time, bucket, average, maximum, minimum, timestamp) \
                VALUES (%s, %s, %s, %s, %s, %s, %s) \
                ON DUPLICATE KEY UPDATE average=%s, maximum=%s, minimum=%s, timestamp=%s".format(row_type)

            data = (
                row['start_time'],
                row['end_time'],
                15,
                row['average'],
                row['maximum'],
                row['minimum'],
                None,
                row['average'],
                row['maximum'],
                row['minimum'],
                None
            )

        elif row_type in ('step_count', 'distance'):
            statement = "INSERT INTO {}(start_time, end_time, bucket, total, timestamp) \
                VALUES (%s, %s, %s, %s, %s) \
                ON DUPLICATE KEY UPDATE total=%s, timestamp=%s".format(row_type)

            data = (
                row['start_time'],
                row['end_time'],
                15,
                row['total'],
                None,
                row['total'],
                None
            )

        cursor.execute(statement, data)
        connection.commit()


def date_from_millis(millis):
    return str(dtm.datetime.fromtimestamp(int(millis)/1000.0))


def date_to_millis(date):
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


def hours_to_millis(hours):
    hr = int(hours * 60 * 60 * 1000)
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
