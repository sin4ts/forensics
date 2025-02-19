#!/usr/bin/python3
# -* coding: utf-8 -*-

import argparse
import csv
from datetime import datetime
import hashlib
import libs.magic as magic
import os
import shutil
import subprocess
import tempfile
import traceback

def md5sum(filepath):
    with open(filepath, 'rb') as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()

def count_extension(input_filepath):
    count = {}
    print(input_filepath)
    for root, dir_list, file_list in os.walk(input_filepath):
        for filename in file_list:
            current_filepath = os.path.join(root, filename)
            extension = filename.split('.')[-1]
            if not extension in count.keys():
                count[extension] = 0
            count[extension] += 1
    for key, value in count.items():
        print(f'{key}: {value}')

def do_system_command(command, stdin=None, env={}):
    '''
    stdin can be a file descriptor
    '''
    for key, value in os.environ.items():
        env[key] = value
    print(' '.join([f'"{X}"' if ' ' in X else X for X in command]))
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

def summary_file(input_filepath, input_root, csv_writer, tmp_directory, remove_source=False):
    relative_path = None
    if input_root:
        relative_path = os.path.dirname(os.path.relpath(input_filepath, input_root))
    filename = os.path.basename(input_filepath)

    res, stdout, stderr, code, tmp_filepath, extension = process_file(input_filepath, tmp_directory, root=input_root, copy_unknown_file=False, remove_source=False)
    filepath = input_filepath
    if tmp_filepath and os.path.exists(tmp_filepath):
        filepath = tmp_filepath
    size = None
    mimetype = None
    md5_sum = None
    if os.path.isfile(filepath):
        size = os.path.getsize(filepath)
        mimetype = magic.from_file(filepath, mime=True)
        md5_sum = md5sum(filepath)
    csv_writer.writerow([input_filepath, relative_path, filename, extension, tmp_filepath, mimetype, size, md5_sum, code, not res, stdout if not res else '', stderr if not res else ''])
    if res:
        if tmp_filepath and os.path.exists(tmp_filepath):
            if os.path.isdir(tmp_filepath):
                summary_directory(tmp_filepath, tmp_directory, csv_writer, tmp_directory, remove_source=True)
            else:
                os.unlink(tmp_filepath)

def summary_directory(input_directory, input_root, csv_writer, tmp_directory, remove_source=False):
    for root, dir_list, file_list in os.walk(input_directory):
        for filename in file_list:
            filepath = os.path.join(root, filename)
            summary_file(filepath, input_root, csv_writer, tmp_directory, remove_source=remove_source)

def summary(target, output_filepath=None, tmp_directory=None, remove_source=False):
    if not output_filepath:
        output_filepath = f'summary_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.csv'
    with open(output_filepath, 'w') as f:
        csv_writer = csv.writer(f, delimiter=',')
        csv_writer.writerow(['Input Full Path', 'Input Path', 'Input File Name', 'Input File Extension', 'Output Full Path', 'Mime Type', 'Size', 'MD5', 'Code', 'Error', 'Stdout', 'Stderr'])
        if not tmp_directory:
             tmp_directory = tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)).name
        if not os.path.exists(tmp_directory):
             os.makedirs(tmp_directory)
        count = 0
        try:
            if os.path.isfile(target):
                summary_file(target, None, csv_writer, tmp_directory, remove_source=False)
            else:
                summary_directory(target, target, csv_writer, tmp_directory, remove_source=False)
        except:
            traceback.print_exc()
        shutil.rmtree(tmp_directory)
        print(f'Data written to {output_filepath}')
        
def extract_zst(filepath, output_dir, relative_path, filename):
    output_directory = os.path.join(output_dir, relative_path)
    zstd_path = '/usr/bin/zstd'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    output_filepath = os.path.join(output_dir, relative_path, filename)[:-4]
    stdout, stderr, code = do_system_command([zstd_path, '-d', '-f', '-o', output_filepath, filepath])
    if code == 0:
        return True, stdout, stderr, code, output_filepath, 'zst'
    else:
        print(stderr)
        return False, stdout, stderr, code, output_filepath, 'zst'

def extract_rar(filepath, output_dir, relative_path, filename):
    output_directory = os.path.join(output_dir, relative_path, filename[:-4])
    bin_path = '/usr/bin/tar'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    stdout, stderr, code = do_system_command([bin_path, 'xvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory, 'rar'
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory, 'rar'

def extract_zip(filepath, output_dir, relative_path, filename):
    output_directory = os.path.join(output_dir, relative_path, filename[:-4])
    bin_path = '/usr/bin/unzip'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    stdout, stderr, code = do_system_command([bin_path, '-o', '-d', output_directory, filepath])
    if code == 0:
        return True, stdout, stderr, code, output_directory, 'zip'
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory, 'zip'

def extract_7z(filepath, output_dir, relative_path, filename):
    output_directory = os.path.join(output_dir, relative_path, filename[:-3])
    bin_path = '/usr/bin/7z'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    stdout, stderr, code = do_system_command([bin_path, '-y', '-o', output_directory, 'x', filepath])
    if code == 0:
        return True, stdout, stderr, code, output_directory, 'zip'
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory, 'zip'

def extract_gz(filepath, output_dir, relative_path, filename):
    output_directory = os.path.join(output_dir, relative_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if filepath.lower().endswith('.tar.gz'):
        output = os.path.join(output_dir, relative_path, filename)[:-7]
        bin_path = '/usr/bin/tar'
        extension = 'tar.gz'
        index = 0
        original_output = output
        while os.path.exists(output):
            index += 1
            output_filepath = f'{original_output}.{index}'
        os.makedirs(output)
        stdout, stderr, code = do_system_command([bin_path, 'xvf', filepath, '-C', output])
    else:
        output = os.path.join(output_dir, relative_path, filename)[:-3]
        bin_path = '/usr/bin/gzip'
        extension = 'gz'
        stdout, stderr, code = do_system_command([bin_path, '-d', '-k', '-f', '-o', output, filepath])
    if code == 0:
        return True, stdout, stderr, code, output, extension
    else:
        print(stderr)
        return False, stdout, stderr, code, output, extension

def process_file(input_filepath, output_directory, root=None, remove_source=False, copy_unknown_file=True, extension_whitelist=[], extension_blacklist=[]):
    print(f'Processing {input_filepath}')
    if root:
        relative_path = os.path.dirname(os.path.relpath(input_filepath, root))
    else:
        relative_path = None
    filename = os.path.basename(input_filepath)
    extension = filename.split('.')[-1]
    res = None
    stderr = None
    stdout = None
    code = None
    output_filepath = None
    extension = filename.split('.')[-1]
    original_extension = extension
    mimetype = magic.from_file(input_filepath, mime=True)

    if (not extension_whitelist or original_extension in extension_whitelist) and (not extension_blacklist or original_extension not in extension_blacklist):
        if original_extension == 'zst':
            res, stderr, stdout, code, output_filepath, extension = extract_zst(input_filepath, output_directory, relative_path, filename)
        if original_extension == 'gz':
            res, stderr, stdout, code, output_filepath, extension = extract_gz(input_filepath, output_directory, relative_path, filename)
        if original_extension == '7z':
            res, stderr, stdout, code, output_filepath, extension = extract_7z(input_filepath, output_directory, relative_path, filename)
        if original_extension == 'rar':
            res, stderr, stdout, code, output_filepath, extension = extract_rar(input_filepath, output_directory, relative_path, filename)
        if original_extension == 'zip':
            res, stderr, stdout, code, output_filepath, extension = extract_zip(input_filepath, output_directory, relative_path, filename)
    if res is None:
        res = True
        if copy_unknown_file:
            output_filepath = os.path.join(output_directory, relative_path, filename)
            shutil.copyfile(input_filepath, output_filepath)
    if remove_source:
        os.unlink(input_filepath)
    return res, stdout, stderr, code, output_filepath, extension

def extract_file(input_filepath, input_root, output_directory, remove_source=False):
    res, stdout, stderr, code, output_filepath, extension = process_file(input_filepath, output_directory, root=input_root, copy_unknown_file=False, remove_source=False)
    if res and output_filepath and os.path.isdir(output_filepath):
        extract_directory(output_filepath, output_directory, output_directory, remove_source=True)

def extract_directory(input_directory, input_root, tmp_directory, remove_source=False):
    for root, dir_list, file_list in os.walk(input_directory):
        for filename in file_list:
            filepath = os.path.join(root, filename)
            extract_file(filepath, input_root, tmp_directory, remove_source=remove_source)

def extract(target, output_directory=None):
    if not output_directory:
        output_directory = f'extracted_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if os.path.isfile(target):
        extract_file(target, None, output_directory, remove_source=False)
    else:
        extract_directory(target, target, output_directory, remove_source=False)
    print(f'Data extracted to {output_directory}')

if __name__ == '__main__':
    # Parse commmand line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--output', help='Output path')
    parser.add_argument('input', nargs=1, help='My first positional argument')
    parser.add_argument('action', nargs='?', help='My first positional argument')

    args = parser.parse_args()
    action = 'count'
    if args.action:
        action = args.action.lower()
    input_filepath = args.input[0]

    if action == 'count':
        count_extension(input_filepath)
    elif action == 'extract':
        extract(input_filepath, output_directory=args.output)
    elif action == 'summary':
        summary(input_filepath, output_filepath=args.output)

