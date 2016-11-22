#!/usr/bin/env python

# vim: expandtab tabstop=4 shiftwidth=4

from datetime import datetime

import exifread
import logging
import os
import shutil
import sys

logging.basicConfig(level=logging.INFO)

min_datetime = datetime(2015)

def determine_capture_time(basename, extensions):
    capture_time = None
    possible_dates = ( get_date(basename+e) for e in extensions )
    possible_dates = ( dt for dt in possible_dates if dt is not None )
    possible_dates = [ dt for dt in possible_dates if dt > min_datetime ]

    if len(possible_dates) == 0:
        capture_time = None
    elif len(possible_dates) == 1:
        capture_time = possible_dates[0]
    else:
        capture_time = min(possible_dates)

    return capture_time

def get_date(file_path):
    time_field = 'Image DateTime'
    with open(file_path, 'rb') as f:
        try:
            tags = exifread.process_file(f, details=False, stop_tag=time_field)

            if time_field in tags:
                return datetime.strptime(tags[time_field].values, '%Y:%m:%d %H:%M:%S')
            else:
                return None
        except Exception as e:
            logging.error(str(e))
            return None

def determine_output_dir(output_dir, dt):
    new_dir = dt.strftime('%Y.%m.%d')
    return output_dir + os.sep + new_dir

def make_output_dir(full_path):
    if not os.path.exists(full_path):
        os.mkdir(full_path, mode=0o755)

    return full_path

def make_name(orig_name, dt):
    f, ext = os.path.splitext(orig_name)
    return 'WPA' + dt.strftime('%Y%m%d%H%M%S') + ext.lower()

def copy_file(file_path, to_dir, output_file_name):
    seq = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    output_paths = ( (to_dir + os.sep + output_file_name + s).strip() for s in seq )

    for possible_path in output_paths:
        if not os.path.exists(possible_path):
            logging.info('Copying {0} to {1}'.format(file_path, possible_path))
            #shutil.copy2(file_path, possible_path)
            break

def group_files(files):
    groups = {}

    for f in files:
        basename, ext = os.path.splitext(f)

        if basename not in groups:
            groups[basename] = set()

        if len(ext) > 0:
            groups[basename].add(ext)

    return groups

if __name__ == "__main__":
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    files = os.listdir(input_dir)
    files = ( input_dir + os.sep + f for f in files )
    files = ( f for f in files if os.path.isfile(f) )
    file_groups = group_files(files)

    capture_times = { basename:determine_capture_time(basename, extensions) for basename, extensions in file_groups }
    file_groups = { basename:extensions for basename, extensions in file_groups if capture_times[basename] is not None }
    output_dirs = { basename:determine_output_dir(output_dir, capture_times[basename]) for basename, _ in file_groups }

    for basename, extensions in file_groups:
        directory = make_output_dir(output_dir, capture_times[basename])
        file_name_map = make_names(basename, extensions, dt)

        for old_path, new_path in file_name_map:
            copy_file(old_path, directory, new_path)
