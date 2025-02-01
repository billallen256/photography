from math import sqrt
from pathlib import Path

import sys

from georgio import bounding_box_for_point

DISTANCE = sqrt(500**2 + 500**2)

def render_placemark(center_lat, center_lon, name):
    west, south, east, north = bounding_box_for_point(center_lon, center_lat, 500)

    return f'''
  <Placemark>
    <name>{name}</name>
    <styleUrl>#yellow</styleUrl>
    <LineString>
      <extrude>1</extrude>
      <altitudeMode>relativeToGround</altitudeMode>
          <coordinates>
            {east},{north},100
            {east},{south},100
            {west},{south},100
            {west},{north},100
            {east},{north},100
          </coordinates>
    </LineString>
  </Placemark>
  '''

def main():
    csv_path = Path(sys.argv[1])
    lines = csv_path.read_text().split('\n')

    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Style id="yellow">
      <LineStyle>
        <color>7f00ffff</color>
        <width>4</width>
      </LineStyle>
  </Style>
  <Folder>
    '''

    for line in lines:
        if not line:
            continue

        if line.startswith('lat'):
            continue

        lat_str, lon_str, name = line.split(',')
        lat = float(lat_str)
        lon = float(lon_str)

        xml += render_placemark(lat, lon, name)

    xml += '</Folder></kml>'
    print(xml)


if __name__ == "__main__":
    main()
