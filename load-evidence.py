#!/usr/bin/python3
# -* coding: utf-8 -*-

import argparse
import csv
from datetime import datetime
import hashlib
import json
import libs.magic as magic
import os
import shutil
import subprocess

COMMON_EXTENSION_LIST = []
with open('mimetype.json', 'r') as fd:
    mimetype_dict = json.load(fd)
    for mimemtype, extension_list in mimetype_dict.items():
        for extension in extension_list:
            if not extension.lower() in COMMON_EXTENSION_LIST:
                COMMON_EXTENSION_LIST.append(extension.lower())
COMMON_EXTENSION_LIST = sorted([X if X.startswith('.') else f'.{X}' for X in COMMON_EXTENSION_LIST], key=len)[::-1]

IMPORTED_FILE = []

def compute_md5sum(filepath):
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

def get_next_available_path(path, delimiter='_', mkdir_parent=False, mkdir=False, extension=None, merge_dir=False):
    '''
    check if path exists and increment the base name if needed
    '''
    if type(path) is list:
        path = os.path.join(*[X for X in path if X])
    path = os.path.normpath(path)
    if os.path.exists(path) and not merge_dir:
            index = 1
            if extension:
                new_path = f'{path[:-len(extension)]}{delimiter}{index}{extension}'
            else:
                new_path = f'{path}{delimiter}{index}'
            while os.path.exists(new_path):
                index += 1
                if extension:
                    new_path = f'{path[:-len(extension)]}{delimiter}{index}{extension}'
                else:
                    new_path = f'{path}{delimiter}{index}'
            path = new_path
    if mkdir:
        if not os.path.exists(path):
            os.makedirs(path)
    elif mkdir_parent:
        parent_path = os.path.dirname(path)
        if not os.path.exists(parent_path):
            os.makedirs(parent_path)
    return path  

def explode_filepath(filepath):
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    filename = basename
    extension = None
    lower_basename = basename.lower()
    if '.' in basename:
        for ext in COMMON_EXTENSION_LIST:
            if lower_basename.endswith(ext):
                extension = basename[-len(ext):]
                filename = basename[:-len(ext)]
                break
        if not extension:
            extension = f'.{basename.split(".")[-1]}'
            filename = basename[:-len(extension)]
    return dirname, basename, filename, extension
        
def extract_zst(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    compression only
    '''
    output_filepath = get_next_available_path([output_dir, relative_path, filename], mkdir_parent=True, merge_dir=merge_dir)
    
    zstd_path = '/usr/bin/zstd'
    stdout, stderr, code = do_system_command([zstd_path, '-d', '-f', '-o', output_filepath, filepath])
    if code == 0:
        return True, stdout, stderr, code, output_filepath
    else:
        print(stderr)
        return False, stdout, stderr, code, output_filepath

def extract_rar(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving and compression
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/tar'
    stdout, stderr, code = do_system_command([bin_path, 'xvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def extract_zip(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving and compression
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/unzip'
    stdout, stderr, code = do_system_command([bin_path, '-o', '-d', output_directory, filepath])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def extract_7z(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving and compression
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/7z'
    stdout, stderr, code = do_system_command([bin_path, '-y', f'-o{output_directory}', 'x', filepath])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def extract_tar(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving only
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/tar'
    stdout, stderr, code = do_system_command([bin_path, 'xvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory
    
def extract_gz(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    compression only
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/tar'
    stdout, stderr, code = do_system_command([bin_path, 'xzvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def extract_tgz(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving and compression
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/tar'
    stdout, stderr, code = do_system_command([bin_path, 'xzvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def extract_bz2(filepath, output_dir, relative_path, filename, extension, basename, merge_dir=False):
    '''
    archiving and compression
    '''
    output_directory = get_next_available_path([output_dir, relative_path, filename], mkdir=True, merge_dir=merge_dir)
    bin_path = '/usr/bin/tar'
    stdout, stderr, code = do_system_command([bin_path, 'xjvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def process_file(input_filepath, output_root, input_root=None, remove_source=False, merge_dir=False, mimetype_whitelist=[], mimetype_blacklist=[]):
    '''
    Process file depending on the mimetype. If no processing is needed, then res is None
    '''
    print(f'Processing {input_filepath}')
    if input_root:
        relative_path = os.path.dirname(os.path.relpath(input_filepath, input_root))
    else:
        relative_path = None
    # here filename is basename without the extension
    _, basename, filename, extension = explode_filepath(input_filepath)
    res = None
    stderr = None
    stdout = None
    code = None
    output_filepath = None
    mimetype = magic.from_file(input_filepath, mime=True).lower().strip()

    if (not mimetype_whitelist or mimetype in mimetype_whitelist) and (not mimetype_blacklist or mimetype not in mimetype_blacklist):
        if mimetype == 'application/zstd':
            res, stderr, stdout, code, output_filepath = extract_zst(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/gzip':
            res, stderr, stdout, code, output_filepath = extract_gz(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-gtar':
            res, stderr, stdout, code, output_filepath = extract_tgz(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-tar':
            res, stderr, stdout, code, output_filepath = extract_tar(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-7z-compressed':
            res, stderr, stdout, code, output_filepath = extract_7z(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-rar-compressed':
            res, stderr, stdout, code, output_filepath = extract_rar(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/zip':
            res, stderr, stdout, code, output_filepath = extract_zip(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-bzip2':
            res, stderr, stdout, code, output_filepath = extract_bz2(input_filepath, output_root, relative_path, filename, extension, basename, merge_dir=merge_dir)
        elif mimetype == 'application/x-xz':
            pass
        elif mimetype == 'application/java-archive':
            pass

        if res is None:
            if relative_path:
                output_filepath = os.path.normpath(os.path.join(output_root, relative_path, basename))
            else:
                output_filepath = os.path.normpath(os.path.join(output_root, basename))
            if output_filepath != os.path.normpath(input_filepath):
                output_filepath = get_next_available_path([output_root, relative_path, basename], extension=extension)
                shutil.copyfile(input_filepath, output_filepath)
        if remove_source:
            os.unlink(input_filepath)
    return res, stdout, stderr, code, output_filepath, extension

def extract_file(input_filepath, input_root, output_root, parent_in=None, parent_out=None, summary_file=None, remove_source=False, hash_max_size=None, merge_dir=False, keep_empty_dir=False, unique=False):
    if summary_file:
        filename = os.path.basename(input_filepath)
        mimetype = magic.from_file(input_filepath, mime=True)
    if summary_file or unique:
        size = os.path.getsize(input_filepath)
        md5sum = None
        if not hash_max_size or size <= hash_max_size:
            md5sum = compute_md5sum(input_filepath)
            if unique and md5sum in IMPORTED_FILE:
                print(f'File {input_filepath} already imported: skipping duplicate')
                return
    # res = True if input file was successfully processed, False if processing failed and None if no processing was needed
    res, stdout, stderr, code, output_path, extension = process_file(input_filepath, output_root, input_root=input_root, merge_dir=merge_dir, remove_source=remove_source)
    if res != False and unique:
        IMPORTED_FILE.append(md5sum)

    original_filepath = input_filepath
    if parent_in and parent_out:
        original_filepath = input_filepath.replace(parent_out, parent_in)
    if summary_file:
        summary_file.writerow([os.path.normpath(original_filepath), filename, extension, output_path, mimetype, size, md5sum, code, '' if res is None else not res, stdout.strip() if not res and stdout else '', stderr.strip() if not res and stdout else ''])

    if res and output_path:
        if os.path.isdir(output_path):
            extract_directory(output_path, input_root, output_root, parent_in=original_filepath, parent_out=output_path, summary_file=summary_file, remove_source=False, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)
        else:
            extract_file(output_path, input_root, output_root, parent_in=original_filepath, parent_out=output_path, summary_file=summary_file, remove_source=False, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)

def extract_directory(input_directory, input_root, output_root, parent_in=None, parent_out=None, summary_file=None, remove_source=False, merge_dir=False, keep_empty_dir=False, unique=False):
    if keep_empty_dir and os.path.isdir(input_directory) and not os.listdir(input_directory):
        relative_path = os.path.relpath(input_directory, input_root)
        output_directory = os.path.normpath(os.path.join(output_root, relative_path))
        if os.path.exists(output_directory) and input_directory != output_directory:
            print(f'Warning: can not load empty directory "{input_directory}" to "{output_directory}" as destination path already exists')
    for child in os.listdir(input_directory):
        child_path = os.path.join(input_directory, child)
        if os.path.isdir(child_path):
            extract_directory(child_path, input_root, output_root, parent_in=parent_in, parent_out=parent_out, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)
        else:
            extract_file(child_path, input_root, output_root, parent_in=parent_in, parent_out=parent_out, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)

def extract(target, output_directory=None, summary_filepath=None, remove_source=False, merge_dir=False, keep_empty_dir=False, unique=False):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    if not output_directory:
        output_directory = f'extracted_{timestamp}'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    if not summary_filepath:
        summary_filepath = f'summary_{timestamp}.csv'
    
    with open(summary_filepath, 'w') as fd:
        summary_file = csv.writer(fd, delimiter=',')
        summary_file.writerow(['Input Full Path', 'Input File Name', 'Input File Extension', 'Output Full Path', 'Mime Type', 'Size', 'MD5', 'Code', 'Error', 'Stdout', 'Stderr'])

        if os.path.isfile(target):
            extract_file(target, None, output_directory, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)
        else:
            extract_directory(target, target, output_directory, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)
    return output_directory, summary_filepath
    

if __name__ == '__main__':
    # Parse commmand line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--output', help='Output path')
    parser.add_argument('-k', '--keep-empty-dir', action='store_true', help='Keep empty directories')
    # merge feature is unsecure at this time - do not use
    # parser.add_argument('-m', '--merge_dir', action='store_true', help='Merge directory in case of name conflict')
    parser.add_argument('-s', '--summary', help='Summary file path')
    parser.add_argument('-u', '--unique', action='store_true', help='Don\'t import duplicated files')
    parser.add_argument('input', nargs='+', help='File or folder to import')

    args = parser.parse_args()

    for target in args.input:
        print(f'Loading evidence from {target}')
        output_directory, summary_filepath = extract(target, output_directory=args.output, summary_filepath=args.summary, keep_empty_dir=args.keep_empty_dir, unique=args.unique)
    print(f'Evidence loaded to {output_directory}')
    if summary_filepath:
        print(f'Summary written to {summary_filepath}')

