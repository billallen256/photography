# vim: expandtab tabstop=4 shiftwidth=4

'''
I dumped two years of tracklogs off my Garmin eTrex Venture HC
using GPSBabel to create a big GPX file.  I needed a way to take
that big GPX file and break it down into a bunch of daily GPX files,
so I created this script.
'''

from argparse import ArgumentParser
from csv import DictReader
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List
from xml.etree import ElementTree as ET

from georgio import great_circle_distance

@dataclass
class Point:
    latitude: float
    longitude: float

@dataclass
class PrivacyZone:
    name: str
    radius_meters: float
    point: Point

def offset_datetime(dt: datetime, epoch_offset: int) -> datetime:
    epoch_offset_delta = timedelta(days=1024*7*epoch_offset)
    return dt + epoch_offset_delta

def trkpt_has_time(trkpt: ET.ElementTree, namespaces) -> bool:
    return trkpt.find('gpx:time', namespaces) is not None

def trkpt_datetime(trkpt: ET.ElementTree, namespaces: Dict[str, str]) -> datetime:
    time_elem = trkpt.find('gpx:time', namespaces)
    return datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')

def should_separate(trkpt1: ET.ElementTree, trkpt2: ET.ElementTree, namespaces: Dict[str, str]) -> bool:
    '''
    Returns True if the points are separated by a significant
    time such that a new trkseg should be started.
    '''
    time1 = trkpt_datetime(trkpt1, namespaces)
    time2 = trkpt_datetime(trkpt2, namespaces)

    if time2 < time1:
        print('Starting new track because next point is before previous point')
        return True

    td = time2 - time1

    if td > timedelta(minutes=60):
        print(f'Starting new track because next point is {td} from previous point')
        return True

    point1 = trkpt_to_point(trkpt1)
    point2 = trkpt_to_point(trkpt2)
    distance = great_circle_distance(
        point1.longitude,
        point1.latitude,
        point2.longitude,
        point2.latitude,
    )

    if distance > 1000:
        print(f'Starting new track because next point is {distance} meters from previous point')
        return True

    return False

def get_trk_name(trk: ET.ElementTree, namespaces) -> str:
    name = trk.find('gpx:name', namespaces)
    return name.text

def get_trkpts(root: Iterable[ET.ElementTree], namespaces: Dict[str, str]) -> Iterable[ET.ElementTree]:
    for trk in root.findall('gpx:trk', namespaces):
        print(f'Found track {get_trk_name(trk, namespaces)}')

        for trkseg in trk.findall('gpx:trkseg', namespaces):
            for trkpt in trkseg:
                yield trkpt

def remove_trkpt_namespaces(trkpt: ET.ElementTree, namespaces: Dict[str, str]) -> None:
    '''
    By default the each trkpt and their sub-elements would have an
    "ns0:" prefix on them.  We don't want that, so we set the tag
    manually.
    '''
    trkpt.tag = 'trkpt'
    ele = trkpt.find('gpx:ele', namespaces)
    ele.tag = 'ele'
    time = trkpt.find('gpx:time', namespaces)
    time.tag = 'time'

class Track:
    def __init__(self, date, namespaces):
        self.date = date
        self.namespaces = namespaces
        self.trkpts = []

    def __str__(self):
        return f'Track for {self.date} with {len(self.trkpts)} trkpts'

    def add_trkpt(self, trkpt):
        self.trkpts.append(trkpt)

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
        trkseg = ET.SubElement(trk, 'trkseg')

        for trkpt in self.trkpts:
            remove_trkpt_namespaces(trkpt, self.namespaces)
            trkseg.append(trkpt)

        return ET.tostring(gpx, encoding='UTF-8')

    def write(self, outfile_suffix: str) -> None:
        file_dt = datetime(self.date.year, self.date.month, self.date.day)
        outfile_path = get_unique_path(file_dt, outfile_suffix)
        print(f'Writing {outfile_path} with {len(self.trkpts)} points')
        outfile_path.write_bytes(self.xml())

def setup_argparser():
    parser = ArgumentParser(description='Breaks a single GPX file into separate GPX files for each day.')
    parser.add_argument('--input',
                        required=True,
                        help='Input GPX file')
    parser.add_argument('--suffix',
                        default='',
                        required=False,
                        help='Suffix that will be placed onto the name of each file')
    parser.add_argument('--privacy_zones',
                        default='',
                        required=False,
                        help='Path to CSV file containing privacy zones (name,radius_meters,latitude,longitude)')
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

def get_unique_path(file_dt: datetime, suffix: str) -> Path:
    dedup_suffix = ''
    sep = ''

    if len(suffix) > 0:
        sep = '-'

    while True:
        outfile_path = Path('{}{}{}{}.gpx'.format(file_dt.strftime('%Y%m%d'), sep, suffix, dedup_suffix))

        if outfile_path.exists() and dedup_suffix == '':
            dedup_suffix = 1
            continue

        if outfile_path.exists():
            dedup_suffix += 1
            continue

        break

    return outfile_path

def get_privacy_zones(csv_file_path_str: str) -> List[PrivacyZone]:
    if csv_file_path_str == '':
        return []

    csv_file_path = Path(csv_file_path_str)
    privacy_zones = []

    if not csv_file_path.exists():
        raise Exception(f'Privacy zone CSV files does not exist at {csv_file_path_str}')

    with csv_file_path.open('r') as csv_file:
        reader = DictReader(csv_file)

        for entry in reader:
            privacy_zones.append(
                PrivacyZone(
                    entry['name'],
                    float(entry['radius_meters']),
                    Point(float(entry['latitude']), float(entry['longitude'])),
            ))

    return privacy_zones

def in_privacy_zone(point: Point, privacy_zone: PrivacyZone) -> bool:
    return great_circle_distance(
        point.longitude,
        point.latitude,
        privacy_zone.point.longitude,
        privacy_zone.point.latitude) <= privacy_zone.radius_meters

def in_any_privacy_zone(point: Point, privacy_zones: List[PrivacyZone]) -> bool:
    for privacy_zone in privacy_zones:
        if in_privacy_zone(point, privacy_zone):
            print(f'Found {point} in {privacy_zone.name}')
            return True

    return False

def trkpt_to_point(trkpt) -> Point:
    return Point(
        float(trkpt.attrib['lat']),
        float(trkpt.attrib['lon']),
    )

def main():
    args = setup_argparser()
    infile_path = Path(args.input)
    outfile_suffix = args.suffix.strip()
    privacy_zones = get_privacy_zones(args.privacy_zones)
    epoch_offset = args.epoch_offset

    gpx_namespace = gpx_schema_namespace(get_namespaces(infile_path))
    print(f'Using gpx namespace {gpx_namespace}')
    namespaces = {'gpx': gpx_namespace}

    orig_root = ET.parse(infile_path).getroot()
    prev_trkpt = None
    current_track = None

    for trkpt in get_trkpts(orig_root, namespaces):
        if not trkpt_has_time(trkpt, namespaces):
            continue

        if in_any_privacy_zone(trkpt_to_point(trkpt), privacy_zones):
            continue

        if prev_trkpt is None or (prev_trkpt is not None and should_separate(prev_trkpt, trkpt, namespaces)):
            if current_track is not None:
                current_track.write(outfile_suffix)

            current_track = Track(
                offset_datetime(trkpt_datetime(trkpt, namespaces), epoch_offset),
                namespaces,
            )

        current_track.add_trkpt(trkpt)
        prev_trkpt = trkpt

    current_track.write(outfile_suffix)

if __name__ == "__main__":
    main()
