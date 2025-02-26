from datetime import datetime
from zoneinfo import ZoneInfo

import hashlib
import logging
import secrets
import subprocess
import re
import os

def utc_timestamp_to_datetime(utc_timestamp, tz=ZoneInfo('UTC'), format_string=None):
    '''
    Transform a UTC timestamp to a datetime object. If timezone is None, then the UTC timzone is used
    tz must be a string or a ZoneInfo object
    '''
    if type(tz) is str:
        tz = ZoneInfo(tz.replace(' ', '_'))
    elif tz is None:
        tz = ZoneInfo('UTC')
    dt = datetime.fromtimestamp(utc_timestamp).astimezone(tz)
    if format_string is None:
        return dt
    else:
        return dt.strftime(format_string)

def get_utc_timestamp():
    # return UTC timestamp in second
    return int(datetime.now().astimezone(ZoneInfo('UTC')).timestamp())

def string_to_timestamp(data, tz=ZoneInfo('UTC')):
    '''
    Transform a string to a datetime object. If timezone is None, then the UTC timzone is used
    tz must be a string or a ZoneInfo object
    '''
    if type(tz) is str:
        tz = ZoneInfo(tz)
    elif tz is None:
        tz = ZoneInfo('UTC')
    if type(data) is datetime:
        return data.astimezone(tz).timestamp()
    elif data is None:
        return None
    else:
        data = data.strip()
    if data == '':
        return None
    try:
        return datetime.strptime(data, '%Y-%m-%d').astimezone(tz).timestamp()
    except:
        return datetime.strptime(data, '%Y-%m-%d %H:%M:%S').astimezone(tz).timestamp()

def generate_token(length=80):
    return ''.join((secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890') for i in range(length)))

def is_valid_email(email):
    return re.match(r'^[\w\-\.\+]+@([\w-]+\.)+[\w\-]{2,4}$', email)

def parse_boolean_string(data, none=False):
    if data is None:
        return none
    return str(data).lower().strip() in ['true', 'ok', 'o', 't', 'on']

def get_random(length=20, choice='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-+=*!@#$%^&(){}[]|:;,.?/"\''):
    return ''.join((secrets.choice(choice) for i in range(length)))

def do_system_command(command, stdin=None, env={}):
    '''
    stdin can be a file descriptor
    '''
    for key, value in os.environ.items():
        env[key] = value
    logging.debug('Executing system command: ' + ' '.join([f'"{X}"' if ' ' in X else X for X in command]))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=stdin, env=env)
    stdout, stderr = process.communicate()
    return_code = process.returncode
    if stdout is None:
        stdout = ''
    else:
        stdout = stdout.decode()
    if stderr is None:
        stderr = ''
    else:
        stderr = stderr.decode()
    return stdout, stderr, return_code

def compute_md5sum(filepath):
    with open(filepath, 'rb') as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()