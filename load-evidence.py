#!/usr/bin/python3
# -* coding: utf-8 -*-

import argparse
import csv
from datetime import datetime
import json
import libs.magic as magic
import logging
import os
import shutil
import sys

import utils

from libs.logger import init_logging
from config import CONFIG

COMMON_EXTENSION_LIST = []
with open(os.path.join(CONFIG.PROJECT_DIR, 'mimetype.json'), 'r') as fd:
    mimetype_dict = json.load(fd)
    for mimemtype, extension_list in mimetype_dict.items():
        for extension in extension_list:
            if not extension.lower() in COMMON_EXTENSION_LIST:
                COMMON_EXTENSION_LIST.append(extension.lower())
COMMON_EXTENSION_LIST = sorted([X if X.startswith('.') else f'.{X}' for X in COMMON_EXTENSION_LIST], key=len)[::-1]

IMPORTED_FILE = []

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
    '''
    /path/subfolder/file.ext
    dirname = /path/subfolder
    basename = file.ext
    filename = file
    extension = .ext
    '''
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
    
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.zstd'], '-d', '-f', '-o', output_filepath, filepath])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.tar'], 'xvf', filepath, '-C', output_directory])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.unzip'], '-o', '-d', output_directory, filepath])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.sevenz'], '-y', f'-o{output_directory}', 'x', filepath])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.tar'], 'xvf', filepath, '-C', output_directory])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.tar'], 'xzvf', filepath, '-C', output_directory])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.tar'], 'xzvf', filepath, '-C', output_directory])
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
    stdout, stderr, code = utils.do_system_command([CONFIG['bin.tar'], 'xjvf', filepath, '-C', output_directory])
    if code == 0:
        return True, stdout, stderr, code, output_directory
    else:
        print(stderr)
        return False, stdout, stderr, code, output_directory

def process_file(input_filepath, output_root, input_root=None, remove_source=False, merge_dir=False, mimetype_whitelist=[], mimetype_blacklist=[]):
    '''
    Process file depending on the mimetype. If no processing is needed, then res is None
    '''
    logging.info(f'Processing {input_filepath}')
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
                if not os.path.exists(os.path.dirname(output_filepath)):
                    os.makedirs(os.path.dirname(output_filepath))
                shutil.copyfile(input_filepath, output_filepath)
        if remove_source:
            os.unlink(input_filepath)
    return res, stdout, stderr, code, output_filepath

def extract_file(input_filepath, input_root, output_root, parent_in=None, parent_out=None, summary_file=None, remove_source=False, hash_max_size=None, merge_dir=False, keep_empty_dir=False, unique=False):
    already_processed = False
    if summary_file:
        mimetype = magic.from_file(input_filepath, mime=True)
        _, filename, _, extension = explode_filepath(input_filepath)
    if summary_file or unique:
        size = os.path.getsize(input_filepath)
        md5sum = None
        if not hash_max_size or size <= hash_max_size:
            md5sum = utils.compute_md5sum(input_filepath)
            if unique and md5sum in IMPORTED_FILE:
                logging.warning(f'File {input_filepath} already imported: skipping duplicate')
                already_processed = True
    
    if not already_processed:
        # res = True if input file was successfully processed, False if processing failed and None if no processing was needed
        res, stdout, stderr, code, output_path = process_file(input_filepath, output_root, input_root=input_root, merge_dir=merge_dir, remove_source=remove_source)
        if res != False and unique:
            IMPORTED_FILE.append(md5sum)
    else:
        res = None
        stdout = None
        stderr = None
        code = None
        output_path = 'n/a'

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
            logging.warning(f'Can not load empty directory "{input_directory}" to "{output_directory}" as destination path already exists')
    for child in os.listdir(input_directory):
        child_path = os.path.join(input_directory, child)
        if os.path.isdir(child_path):
            extract_directory(child_path, output_root, output_root, parent_in=parent_in, parent_out=parent_out, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)
        else:
            extract_file(child_path, output_root, output_root, parent_in=parent_in, parent_out=parent_out, summary_file=summary_file, remove_source=remove_source, merge_dir=merge_dir, keep_empty_dir=keep_empty_dir, unique=unique)

def extract(target, output_directory=None, summary_filepath=None, remove_source=False, merge_dir=False, keep_empty_dir=False, unique=False):
    global CONFIG

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

    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    parser.add_argument('-q', '--quiet', action='store_true', help='Enable quiet mode')
    parser.add_argument('-c', '--config', help='Configuration file to use')
    parser.add_argument('-o', '--output', help='Output path')
    parser.add_argument('-k', '--keep-empty-dir', action='store_true', help='Keep empty directories')
    # merge feature is unsecure at this time - do not use
    # parser.add_argument('-m', '--merge_dir', action='store_true', help='Merge directory in case of name conflict')
    parser.add_argument('-s', '--summary', help='Summary file path')
    parser.add_argument('-u', '--unique', action='store_true', help='Don\'t import duplicated files')
    parser.add_argument('input', nargs='+', help='File or folder to import')

    args = parser.parse_args()

    # Init config
    if args.config is not None and os.path.exists(args.config):
        # logging is not yet initialitzed
        print('Invalid configuration file path : {}'.format(args.config))
        sys.exit(1)
    CONFIG.populate(args.config, reload=True)

    # Init logging
    if args.verbose:
        init_logging(CONFIG['general.log_directory'], level=logging.DEBUG)
    elif args.quiet:
        init_logging(CONFIG['general.log_directory'], level=logging.WARNING)
    else:
        init_logging(CONFIG['general.log_directory'], level=logging.INFO)

    for target in args.input:
        logging.info(f'Loading evidence from {target}')
        output_directory, summary_filepath = extract(target, output_directory=args.output, summary_filepath=args.summary, keep_empty_dir=args.keep_empty_dir, unique=args.unique)
    logging.info(f'Evidence loaded to {output_directory}')
    if summary_filepath:
        logging.info(f'Summary written to {summary_filepath}')





