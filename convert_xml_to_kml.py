#!/usr/bin/env python3
"""
Convert LandXML alignment files to KML for viewing in Google Earth.
Transforms coordinates from EPSG:2871 (California State Plane Zone II) to WGS84.
"""

import xml.etree.ElementTree as ET
from pyproj import Transformer
import os
import sys


def parse_landxml_alignment(xml_file):
    """
    Parse a LandXML file and extract alignment geometry.

    Args:
        xml_file: Path to the LandXML file

    Returns:
        dict with alignment name and list of coordinate points
    """
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Define the namespace
    ns = {'landxml': 'http://www.landxml.org/schema/LandXML-1.2'}

    # Find the alignment
    alignment = root.find('.//landxml:Alignment', ns)
    if alignment is None:
        raise ValueError(f"No alignment found in {xml_file}")

    alignment_name = alignment.get('name', 'Unknown')
    alignment_desc = alignment.get('desc', '')

    # Extract coordinate geometry
    coord_points = []
    coord_geom = alignment.find('.//landxml:CoordGeom', ns)

    if coord_geom is not None:
        # Process Line elements
        for line in coord_geom.findall('landxml:Line', ns):
            start = line.find('landxml:Start', ns)
            end = line.find('landxml:End', ns)

            if start is not None:
                coords = start.text.strip().split()
                if len(coords) >= 2:
                    coord_points.append((float(coords[0]), float(coords[1])))

            if end is not None:
                coords = end.text.strip().split()
                if len(coords) >= 2:
                    coord_points.append((float(coords[0]), float(coords[1])))

        # Process Curve elements
        for curve in coord_geom.findall('landxml:Curve', ns):
            start = curve.find('landxml:Start', ns)
            end = curve.find('landxml:End', ns)

            if start is not None:
                coords = start.text.strip().split()
                if len(coords) >= 2:
                    coord_points.append((float(coords[0]), float(coords[1])))

            if end is not None:
                coords = end.text.strip().split()
                if len(coords) >= 2:
                    coord_points.append((float(coords[0]), float(coords[1])))

    # Remove duplicate consecutive points
    unique_points = []
    for point in coord_points:
        if not unique_points or unique_points[-1] != point:
            unique_points.append(point)

    return {
        'name': alignment_name,
        'description': alignment_desc,
        'points': unique_points
    }


def transform_coordinates(points, source_epsg='EPSG:2871', target_epsg='EPSG:4326'):
    """
    Transform coordinates from source CRS to target CRS.

    Args:
        points: List of (x, y) tuples in source CRS
        source_epsg: Source coordinate system (default: EPSG:2871 - CA State Plane Zone II)
        target_epsg: Target coordinate system (default: EPSG:4326 - WGS84)

    Returns:
        List of (lon, lat) tuples in target CRS
    """
    transformer = Transformer.from_crs(source_epsg, target_epsg, always_xy=True)

    transformed_points = []
    for x, y in points:
        lon, lat = transformer.transform(x, y)
        transformed_points.append((lon, lat))

    return transformed_points


def create_kml(alignment_data, transformed_points, output_file):
    """
    Create a KML file from alignment data and transformed coordinates.

    Args:
        alignment_data: Dictionary with alignment name and description
        transformed_points: List of (lon, lat) tuples
        output_file: Path to output KML file
    """
    name = alignment_data['name']
    description = alignment_data['description']

    # Build KML content
    kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <description>{description}</description>
    <Style id="lineStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <Placemark>
      <name>Alignment: {name}</name>
      <description>{description}</description>
      <styleUrl>#lineStyle</styleUrl>
      <LineString>
        <extrude>0</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>
'''

    # Add coordinates (lon,lat,altitude format)
    for lon, lat in transformed_points:
        kml_content += f'          {lon},{lat},0\n'

    kml_content += '''        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)

    print(f"Created KML file: {output_file}")
    print(f"  Alignment: {name}")
    print(f"  Points: {len(transformed_points)}")


def convert_landxml_to_kml(xml_file, output_file=None):
    """
    Convert a LandXML file to KML format.

    Args:
        xml_file: Path to input LandXML file
        output_file: Path to output KML file (default: same name with .kml extension)
    """
    if output_file is None:
        output_file = os.path.splitext(xml_file)[0] + '.kml'

    print(f"\nProcessing: {xml_file}")

    # Parse the LandXML file
    alignment_data = parse_landxml_alignment(xml_file)
    print(f"  Found alignment: {alignment_data['name']}")
    print(f"  Original points: {len(alignment_data['points'])}")

    # Transform coordinates from State Plane to WGS84
    transformed_points = transform_coordinates(alignment_data['points'])

    # Create KML file
    create_kml(alignment_data, transformed_points, output_file)

    return output_file


def main():
    """Main function to process all XML files in DATA directory."""
    data_dir = 'DATA'

    if not os.path.exists(data_dir):
        print(f"ERROR: {data_dir} directory not found!")
        sys.exit(1)

    # Find all XML files
    xml_files = [f for f in os.listdir(data_dir) if f.endswith('.xml')]

    if not xml_files:
        print(f"ERROR: No XML files found in {data_dir} directory!")
        sys.exit(1)

    print(f"Found {len(xml_files)} XML file(s) to convert")
    print("=" * 60)

    # Process each XML file
    kml_files = []
    for xml_file in sorted(xml_files):
        xml_path = os.path.join(data_dir, xml_file)
        kml_path = os.path.join(data_dir, os.path.splitext(xml_file)[0] + '.kml')

        try:
            kml_file = convert_landxml_to_kml(xml_path, kml_path)
            kml_files.append(kml_file)
        except Exception as e:
            print(f"ERROR processing {xml_file}: {e}")

    print("\n" + "=" * 60)
    print(f"Conversion complete! Created {len(kml_files)} KML file(s):")
    for kml_file in kml_files:
        print(f"  - {kml_file}")
    print("\nYou can now open these files in Google Earth to view the alignments.")


if __name__ == '__main__':
    main()
