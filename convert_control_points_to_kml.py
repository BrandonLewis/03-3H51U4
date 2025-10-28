#!/usr/bin/env python3
"""
Convert Control Points CSV to KML for viewing in Google Earth.
Transforms coordinates from EPSG:2871 (California State Plane Zone II) to WGS84.

CSV Format:
- Has a header row
- Column indices: station name (1), northing (3), easting (4), elevation (5)
"""

import csv
import os
import sys
from pyproj import Transformer


def read_control_points(csv_file):
    """
    Read control points from a CSV file.

    Args:
        csv_file: Path to the CSV file

    Returns:
        List of dicts with station name, easting, northing, and elevation
    """
    control_points = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        # Skip header row
        next(reader)

        for row in reader:
            if len(row) >= 6:  # Make sure we have enough columns
                try:
                    station_name = row[1].strip()
                    northing = float(row[3])
                    easting = float(row[4])
                    elevation = float(row[5])

                    control_points.append({
                        'name': station_name,
                        'easting': easting,
                        'northing': northing,
                        'elevation': elevation
                    })
                except (ValueError, IndexError) as e:
                    print(f"Warning: Skipping row due to error: {e}")
                    continue

    return control_points


def transform_point(easting, northing, source_epsg='EPSG:2871', target_epsg='EPSG:4326'):
    """
    Transform a single point from source CRS to target CRS.

    Args:
        easting: Easting coordinate in source CRS
        northing: Northing coordinate in source CRS
        source_epsg: Source coordinate system (default: EPSG:2871 - CA State Plane Zone II)
        target_epsg: Target coordinate system (default: EPSG:4326 - WGS84)

    Returns:
        Tuple of (longitude, latitude)
    """
    transformer = Transformer.from_crs(source_epsg, target_epsg, always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return lon, lat


def create_kml(control_points, output_file):
    """
    Create a KML file from control points.

    Args:
        control_points: List of control point dicts
        output_file: Path to output KML file
    """
    # Build KML content
    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Control Points</name>
    <description>Survey control points from EPSG:2871 (CA State Plane Zone II)</description>

    <Style id="controlPointStyle">
      <IconStyle>
        <color>ff0000ff</color>
        <scale>1.2</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <color>ffffffff</color>
        <scale>0.9</scale>
      </LabelStyle>
    </Style>
'''

    # Transform and add each control point
    for point in control_points:
        lon, lat = transform_point(point['easting'], point['northing'])
        elevation = point['elevation']
        name = point['name']

        # Create description with coordinate info
        description = f"""
Station: {name}
Easting: {point['easting']:.3f}
Northing: {point['northing']:.3f}
Elevation: {elevation:.3f} ft
"""

        kml_content += f'''
    <Placemark>
      <name>{name}</name>
      <description>{description.strip()}</description>
      <styleUrl>#controlPointStyle</styleUrl>
      <Point>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>{lon},{lat},0</coordinates>
      </Point>
    </Placemark>
'''

    kml_content += '''  </Document>
</kml>
'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)

    print(f"Created KML file: {output_file}")
    print(f"  Control points: {len(control_points)}")


def convert_control_points_to_kml(csv_file, output_file=None):
    """
    Convert a control points CSV file to KML format.

    Args:
        csv_file: Path to input CSV file
        output_file: Path to output KML file (default: same name with .kml extension)
    """
    if output_file is None:
        output_file = os.path.splitext(csv_file)[0] + '.kml'

    print(f"\nProcessing: {csv_file}")

    # Read control points
    control_points = read_control_points(csv_file)
    print(f"  Found {len(control_points)} control points")

    if not control_points:
        print("ERROR: No valid control points found in CSV file!")
        return None

    # Create KML file
    create_kml(control_points, output_file)

    return output_file


def main():
    """Main function to process Control Points CSV file."""

    # Look for Control Points.csv in common locations
    possible_locations = [
        'Control Points.csv',
        'DATA/Control Points.csv',
        'control_points.csv',
        'DATA/control_points.csv'
    ]

    csv_file = None
    for location in possible_locations:
        if os.path.exists(location):
            csv_file = location
            break

    # Allow user to specify file as command line argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]

    if not csv_file or not os.path.exists(csv_file):
        print("ERROR: Control Points.csv file not found!")
        print("\nSearched locations:")
        for loc in possible_locations:
            print(f"  - {loc}")
        print("\nUsage: python3 convert_control_points_to_kml.py [path_to_csv]")
        sys.exit(1)

    print("Control Points CSV to KML Converter")
    print("=" * 60)

    try:
        kml_file = convert_control_points_to_kml(csv_file)

        if kml_file:
            print("\n" + "=" * 60)
            print(f"Conversion complete!")
            print(f"Output: {kml_file}")
            print("\nYou can now open this file in Google Earth to view the control points.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
