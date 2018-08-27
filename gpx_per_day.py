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

$ python3 gpx_per_day.py <input_gpx_file> <prefix_to_use_for_output_gpx_files>
'''

from datetime import datetime
from xml.etree import ElementTree as ET

import os
import sys

def find_children_ending_with(elem, s):
    for child in elem:
        if child.tag.endswith(s):
            yield child

def find_first_child_ending_with(elem, s):
    for child in elem:
        if child.tag.endswith(s):
            return child

def get_date_for_trkseg(trkseg):
    max_date = datetime(1970, 1, 1)

    for trkpt in trkseg:
        date_elem = find_first_child_ending_with(trkpt, 'time')
        date = datetime.strptime(date_elem.text, '%Y-%m-%dT%H:%M:%SZ')

        if date > max_date:
            max_date = date

    return max_date

def remove_trkseg_namespaces(trkseg):
    trkseg.tag = 'trkseg'

    for trkpt in trkseg:
        trkpt.tag = 'trkpt'
        ele = find_first_child_ending_with(trkpt, 'ele')
        ele.tag = 'ele'
        time = find_first_child_ending_with(trkpt, 'time')
        time.tag = 'time'

class Track:
    def __init__(self, date):
        self.date = date
        self.track_segments = []

    def __str__(self):
        return 'Track for {0} with {1} segments'.format(self.date, len(self.track_segments))

    def add_track_segment(self, ts):
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

if __name__ == "__main__":
    infile_name = sys.argv[1]
    outfile_base_name = sys.argv[2]
    orig_root = ET.parse(infile_name).getroot()
    tracks = {}

    for trk in find_children_ending_with(orig_root, 'trk'):
        for trkseg in find_children_ending_with(trk, 'trkseg'):
            dt = get_date_for_trkseg(trkseg)

            if dt.date() in tracks:
                tracks[dt.date()].add_track_segment(trkseg)
            else:
                new_track = Track(dt.date())
                new_track.add_track_segment(trkseg)
                tracks[dt.date()] = new_track

    for date, track in tracks.items():
        dt = datetime(date.year, date.month, date.day)
        outfile_name = '{0}-{1}.gpx'.format(outfile_base_name, dt.strftime('%Y%m%d'))

        if os.path.exists(outfile_name):
            print('{0} already exists.  Skipping...'.format(outfile_name))
            continue

        print(outfile_name)

        with open(outfile_name, 'wb') as f:
            f.write(track.xml())
