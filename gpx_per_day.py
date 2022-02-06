# vim: expandtab tabstop=4 shiftwidth=4

'''
I dumped two years of tracklogs off my Garmin eTrex Venture HC
using GPSBabel to create a big GPX file.  I needed a way to take
that big GPX file and break it down into a bunch of daily GPX files,
so I created this script.
'''

from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from xml.etree import ElementTree as ET

def get_date_for_trkseg(trkseg, utc_offset, epoch_offset, namespaces) -> datetime:
    max_date = datetime(1970, 1, 1)
    utc_offset = timedelta(hours=utc_offset)
    epoch_offset = timedelta(days=1024*7*epoch_offset)

    for trkpt in trkseg:
        time_elem = trkpt.find('gpx:time', namespaces)
        dt = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
        dt += utc_offset + epoch_offset

        if dt > max_date:
            max_date = dt

    return max_date

def apply_epoch_offset(trkseg, epoch_offset, namespaces):
    for trkpt in trkseg:
        time_elem = trkpt.find('gpx:time', namespaces)
        orig_time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
        new_time = orig_time + timedelta(days=1024*7*epoch_offset)
        time_elem.text = new_time.strftime('%Y-%m-%dT%H:%M:%SZ')

def remove_trkseg_namespaces(trkseg, namespaces):
    trkseg.tag = 'trkseg'

    for trkpt in trkseg:
        trkpt.tag = 'trkpt'
        ele = trkpt.find('gpx:ele', namespaces)
        ele.tag = 'ele'
        time = trkpt.find('gpx:time', namespaces)
        time.tag = 'time'

class Track:
    def __init__(self, date, namespaces):
        self.date = date
        self.namespaces = namespaces
        self.track_segments = []

    def __str__(self):
        return 'Track for {0} with {1} segments'.format(self.date, len(self.track_segments))

    def add_track_segment(self, trkseg, epoch_offset):
        apply_epoch_offset(trkseg, epoch_offset, self.namespaces)
        remove_trkseg_namespaces(trkseg, self.namespaces)
        self.track_segments.append(trkseg)

    def xml(self):
        gpx = ET.Element('gpx', attrib={
            'version': '1.0',
            'creator': 'https://github.com/billallen256/photography/blob/master/gpx_per_day.py',
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

def check_utc_offset(offset: int) -> None:
    if offset < -12 or offset > 12:
        raise Exception('UTC offset too large')

def setup_argparser():
    parser = ArgumentParser(description='Breaks a single GPX file into separate GPX files for each day.')
    parser.add_argument('--input',
                        required=True,
                        help='Input GPX file')
    parser.add_argument('--suffix',
                        default='',
                        required=False,
                        help='Suffix that will be placed onto the name of each file')
    parser.add_argument('--utc_offset',
                        default=0,
                        type=int,
                        required=False,
                        help="UTC offset in hours, in case you're far from the prime meridian")
    parser.add_argument('--epoch_offset',
                        default=0,
                        type=int,
                        required=False,
                        help='Epoch offset in units of 1024-weeks (10-bits week count from ICD-200)')
    parsed = parser.parse_args()
    return parsed

def get_namespaces(infile_path: Path) -> Dict[str, str]:
    return dict([node for _, node in ET.iterparse(infile_path, events=['start-ns'])])

def gpx_schema_namespace(namespaces: Dict[str, str]) -> str:
    for _, namespace in namespaces.items():
        if namespace.startswith('http://www.topografix.com/GPX/1'):
            return namespace

    raise Exception(f'Could not find gpx namespace in {namespaces}')

def main():
    args = setup_argparser()
    infile_path = Path(args.input)
    outfile_suffix = args.suffix.strip()
    check_utc_offset(args.utc_offset)
    epoch_offset = args.epoch_offset

    gpx_namespace = gpx_schema_namespace(get_namespaces(infile_path))
    print(f'Using gpx namespace {gpx_namespace}')
    namespaces = {'gpx': gpx_namespace}

    orig_root = ET.parse(infile_path).getroot()
    tracks = {}

    for trk in orig_root.findall('gpx:trk', namespaces):
        for trkseg in trk.findall('gpx:trkseg', namespaces):
            dt = get_date_for_trkseg(trkseg, args.utc_offset, epoch_offset, namespaces)

            if dt.date() in tracks:
                tracks[dt.date()].add_track_segment(trkseg, epoch_offset)
            else:
                new_track = Track(dt.date(), namespaces)
                new_track.add_track_segment(trkseg, epoch_offset)
                tracks[dt.date()] = new_track

    for date, track in tracks.items():
        dt = datetime(date.year, date.month, date.day)

        sep = ''

        if len(outfile_suffix) > 0:
            sep = '-'

        outfile_path = Path('{}{}{}.gpx'.format(dt.strftime('%Y%m%d'), sep, outfile_suffix))

        if outfile_path.exists():
            print(f'{outfile_path} already exists.  Skipping...')
            continue

        print(outfile_path)
        outfile_path.write_bytes(track.xml())

if __name__ == "__main__":
    main()
