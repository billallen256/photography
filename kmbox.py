from math import sqrt
from pathlib import Path

import sys

from georgio import bounding_box_for_point

def render_placemark(center_lat, center_lon, name):
    west, south, east, north = bounding_box_for_point(center_lon, center_lat, 500)

    return f'''
      <Placemark>
        <name>{name}</name>
        <styleUrl>#boxStyle</styleUrl>
        <MultiGeometry>
          <LineString>
            <extrude>0</extrude>
            <altitudeMode>relativeToGround</altitudeMode>
                <coordinates>
                  {west},{center_lat},1
                  {east},{center_lat},1
                </coordinates>
          </LineString>
          <LineString>
            <extrude>0</extrude>
            <altitudeMode>relativeToGround</altitudeMode>
                <coordinates>
                  {center_lon},{north},1
                  {center_lon},{south},1
                </coordinates>
          </LineString>
          <LineString>
            <extrude>0</extrude>
            <altitudeMode>relativeToGround</altitudeMode>
                <coordinates>
                  {east},{north},1
                  {east},{south},1
                  {west},{south},1
                  {west},{north},1
                  {east},{north},1
                </coordinates>
          </LineString>
        </MultiGeometry>
      </Placemark>
  '''

def main():
    csv_path = Path(sys.argv[1])
    lines = csv_path.read_text().split('\n')

    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="boxStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>2</width>
      </LineStyle>
    </Style>
    <Folder>
    '''

    for line in lines:
        if not line:
            continue

        # skip over column name header
        if line.startswith('lat'):
            continue

        lat_str, lon_str, name = line.split(',')
        lat = float(lat_str)
        lon = float(lon_str)

        xml += render_placemark(lat, lon, name)

    xml += '</Folder></Document></kml>'
    print(xml)


if __name__ == "__main__":
    main()
