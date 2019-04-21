# vim: expandtab tabstop=4 shiftwidth=4

'''
I dumped two years of tracklogs off my Garmin eTrex Venture HC
using GPSBabel to create a big GPX file.  I needed a way to take
that big GPX file and break it down into a bunch of daily GPX files,
so I created this script.  It's more of a hack than I would like,
especially around XML namespaces; ElementTree doesn't eat its own
dogfood, so parsed input doesn't preserve each attribute's
namespace, causing the ElementTree.write() to error out when the
default_namespace is set.
'''

from argparse import ArgumentParser
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import os
import sys

namespaces = { 'gpx': 'http://www.topografix.com/GPX/1/0' }

def get_date_for_trkseg(trkseg, utc_offset, epoch_offset):
    max_date = datetime(1970, 1, 1)
    utc_offset = timedelta(hours=utc_offset)
    epoch_offset = timedelta(days=1024*7*epoch_offset)

    for trkpt in trkseg:
        time_elem = trkpt.find('gpx:time', namespaces)
        date = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
        date += utc_offset + epoch_offset

        if date > max_date:
            max_date = date

    return max_date

def apply_epoch_offset(trkseg, epoch_offset):
    for trkpt in trkseg:
        time_elem = trkpt.find('gpx:time', namespaces)
        orig_time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
        new_time = orig_time + timedelta(days=1024*7*epoch_offset)
        time_elem.text = new_time.strftime('%Y-%m-%dT%H:%M:%SZ')

def remove_trkseg_namespaces(trkseg):
    trkseg.tag = 'trkseg'

    for trkpt in trkseg:
        trkpt.tag = 'trkpt'
        ele = trkpt.find('gpx:ele', namespaces)
        ele.tag = 'ele'
        time = trkpt.find('gpx:time', namespaces)
        time.tag = 'time'

class Track:
    def __init__(self, date):
        self.date = date
        self.track_segments = []

    def __str__(self):
        return 'Track for {0} with {1} segments'.format(self.date, len(self.track_segments))

    def add_track_segment(self, ts, epoch_offset):
        apply_epoch_offset(ts, epoch_offset)
        remove_trkseg_namespaces(ts)
        self.track_segments.append(ts)

    def xml(self):
        gpx = ET.Element('gpx', attrib={
            'version': '1.0',
            'creator': 'https://github.com/gershwinlabs/photography/blob/master/gpx_per_day.py',
            'xmlns': 'http://www.topografix.com/GPX/1/0',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd',
        })

        trk = ET.SubElement(gpx, 'trk')
        name = ET.SubElement(trk, 'name')
        name.text = str(self.date)

        for track_segment in self.track_segments:
            trk.append(track_segment)

        return ET.tostring(gpx, encoding='UTF-8')

def check_utc_offset(offset):
    if offset < -12 or offset > 12:
        return 0, 'UTC offset too large'

    return offset, None

def setup_argparser():
    parser = ArgumentParser(description='Breaks a single GPX file into separate GPX files for each day.')
    parser.add_argument('--input', required=True, help='Input GPX file')
    parser.add_argument('--prefix', default='', required=False, help='Prefix that will be placed onto the name of each file')
    parser.add_argument('--utc_offset', default=0, type=int, required=False, help="UTC offset in hours, in case you're far from the prime meridian")
    parser.add_argument('--epoch_offset', default=0, type=int, required=False, help='Epoch offset in units of 1024-weeks (10-bits week count from ICD-200)')
    parsed = parser.parse_args()
    return parsed

if __name__ == "__main__":
    args = setup_argparser()
    infile_name = args.input
    outfile_prefix = args.prefix
    utc_offset, err = check_utc_offset(args.utc_offset)
    epoch_offset = args.epoch_offset
    
    if err != None:
        print(err)
        sys.exit(1)

    orig_root = ET.parse(infile_name).getroot()
    tracks = {}

    for trk in orig_root.findall('gpx:trk', namespaces):
        for trkseg in trk.findall('gpx:trkseg', namespaces):
            dt = get_date_for_trkseg(trkseg, utc_offset, epoch_offset)

            if dt.date() in tracks:
                tracks[dt.date()].add_track_segment(trkseg, epoch_offset)
            else:
                new_track = Track(dt.date())
                new_track.add_track_segment(trkseg, epoch_offset)
                tracks[dt.date()] = new_track

    for date, track in tracks.items():
        dt = datetime(date.year, date.month, date.day)
        outfile_name = '{0}-{1}.gpx'.format(outfile_prefix, dt.strftime('%Y%m%d'))

        if os.path.exists(outfile_name):
            print('{0} already exists.  Skipping...'.format(outfile_name))
            continue

        print(outfile_name)

        with open(outfile_name, 'wb') as f:
            f.write(track.xml())
