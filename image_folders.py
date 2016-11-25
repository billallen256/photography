#!/usr/bin/env python

# vim: expandtab tabstop=4 shiftwidth=4

from datetime import datetime

import exifread
import logging
import os
import shutil
import sys

logging.basicConfig(level=logging.INFO)

min_datetime = datetime(2015, 1, 1)
output_prefix = 'WPA'

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
    exif_date = get_exif_date(file_path)

    if exif_date is not None:
        return exif_date

    return datetime.fromtimestamp(os.path.getmtime(file_path))

def get_exif_date(file_path):
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

def determine_output_dir(output_dir, dt, default_event):
    new_dir = dt.strftime('%Y.%m.%d') + '.' + default_event
    return output_dir + os.sep + new_dir

def make_output_dir(full_path):
    if not os.path.exists(full_path):
        logging.info('Making directory {0}'.format(full_path))
        #os.mkdir(full_path, mode=0o755)

def make_name(dt):
    return output_prefix + dt.strftime('%Y%m%d%H%M%S')

def copy_file(from_path, to_path):
    logging.info('Copying {0} to {1}'.format(from_path, to_path))
    #shutil.copy2(file_path, possible_path)

def group_files(files):
    groups = {}

    for f in files:
        basename, ext = os.path.splitext(f)

        if basename not in groups:
            groups[basename] = set()

        if len(ext) > 0:
            groups[basename].add(ext)

    return groups

def transpose_dict(d):
    ret = {}

    for k, v in d.items():
        if v not in ret:
            ret[v] = set()

        ret[v].add(k)

    return ret

def generate_move_ops(output_paths, file_groups):
    for output_path, basenames in output_paths.items():
        seq = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        seq_counter = 0

        # sort the basenames to preserve sequencing of files captured in the same second
        for basename in sorted(basenames):
            for ext in file_groups[basename]:
                from_path = basename + ext
                to_path = (output_path + seq[seq_counter]).strip() + ext
                yield (from_path, to_path)
            seq_counter += 1

if __name__ == "__main__":
    input_directory = sys.argv[1]
    output_directory = sys.argv[2]
    default_event = sys.argv[3]
    files = os.listdir(input_directory)
    files = ( input_directory + os.sep + f for f in files )
    files = ( f for f in files if os.path.isfile(f) )
    file_groups = group_files(files)

    capture_times = { basename: determine_capture_time(basename, extensions) for basename, extensions in file_groups.items() }
    file_groups = { basename: extensions for basename, extensions in file_groups.items() if capture_times[basename] is not None }
    output_dirs = { basename: determine_output_dir(output_directory, capture_times[basename], default_event) for basename in file_groups }

    # need to ensure the new filenames containing the capture time don't conflict
    # within their new output directories
    output_paths = { basename: output_dirs[basename]+os.sep+make_name(capture_times[basename]) for basename in file_groups }
    output_paths = transpose_dict(output_paths) # transpose so we can generate the move operations as a reduce

    for d in set(output_dirs.values()):
        make_output_dir(d)

    for from_path, to_path in generate_move_ops(output_paths, file_groups):
        copy_file(from_path, to_path)
