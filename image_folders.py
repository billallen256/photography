#!/usr/bin/env python

# vim: expandtab tabstop=4 shiftwidth=4

from datetime import datetime

import exifread
import logging
import os
import shutil
import sys

logging.basicConfig(level=logging.INFO)

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

def make_output_dir(output_dir, dt):
    #new_dir = '{Y:02d}.{m:02d}.{d:02d}'.format(Y=dt.year, m=dt.month, d=dt.day)
    new_dir = dt.strftime('%Y.%m.%d')
    full_path = output_dir + os.sep + new_dir

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
            shutil.copy2(file_path, possible_path)
            break

if __name__ == "__main__":
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    files = os.listdir(input_dir)
    files = ( input_dir + os.sep + f for f in files )
    files = ( f for f in files if os.path.isfile(f) )
    dated_files = ( (get_date(f), f) for f in files )
    dated_files = ( df for df in dated_files if df[0] is not None )

    for dt, file in dated_files:
        directory = make_output_dir(output_dir, dt)
        output_file_name = make_name(file, dt)
        copy_file(file, directory, output_file_name)
