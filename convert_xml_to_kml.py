#!/usr/bin/env python3
"""
Convert LandXML alignment files to KML for viewing in Google Earth.
Transforms coordinates from EPSG:2871 (California State Plane Zone II) to WGS84.

Note: LandXML stores coordinates as Northing Easting (Y X) pairs in the text content
of Start, End, Center, and PI elements. This script swaps them to Easting Northing (X Y)
before passing to pyproj for transformation.
"""

import xml.etree.ElementTree as ET
from pyproj import Transformer
import os
import sys
import math


def interpolate_arc(center_x, center_y, start_x, start_y, end_x, end_y, radius, delta, rotation, num_points=50):
    """
    Interpolate points along a circular arc.

    Args:
        center_x, center_y: Center point of the arc (Easting, Northing)
        start_x, start_y: Start point of the arc (Easting, Northing)
        end_x, end_y: End point of the arc (Easting, Northing)
        radius: Radius of the arc
        delta: Sweep angle in degrees
        rotation: 'ccw' for counter-clockwise, 'cw' for clockwise
        num_points: Number of points to interpolate along the arc

    Returns:
        List of (x, y) tuples representing points along the arc
    """
    # Calculate start angle from center to start point
    start_angle = math.atan2(start_y - center_y, start_x - center_x)

    # Convert delta to radians
    delta_rad = math.radians(delta)

    # Adjust direction based on rotation
    if rotation == 'cw':
        delta_rad = -delta_rad

    # Generate points along the arc
    arc_points = []
    for i in range(num_points + 1):
        # Calculate angle for this point
        fraction = i / num_points
        angle = start_angle + (delta_rad * fraction)

        # Calculate point on arc
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)

        arc_points.append((x, y))

    return arc_points


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
                    # XML format is: Northing Easting (Y X)
                    # Store as: Easting Northing (X Y)
                    coord_points.append((float(coords[1]), float(coords[0])))

            if end is not None:
                coords = end.text.strip().split()
                if len(coords) >= 2:
                    # XML format is: Northing Easting (Y X)
                    # Store as: Easting Northing (X Y)
                    coord_points.append((float(coords[1]), float(coords[0])))

        # Process Curve elements - interpolate points along the arc
        for curve in coord_geom.findall('landxml:Curve', ns):
            start_elem = curve.find('landxml:Start', ns)
            end_elem = curve.find('landxml:End', ns)
            center_elem = curve.find('landxml:Center', ns)

            # Get curve attributes
            radius = curve.get('radius')
            delta = curve.get('delta')
            rotation = curve.get('rot')

            if start_elem is not None and end_elem is not None and center_elem is not None and radius and delta:
                # Parse start point (Northing Easting -> Easting Northing)
                start_coords = start_elem.text.strip().split()
                start_x = float(start_coords[1])  # Easting
                start_y = float(start_coords[0])  # Northing

                # Parse end point (Northing Easting -> Easting Northing)
                end_coords = end_elem.text.strip().split()
                end_x = float(end_coords[1])  # Easting
                end_y = float(end_coords[0])  # Northing

                # Parse center point (Northing Easting -> Easting Northing)
                center_coords = center_elem.text.strip().split()
                center_x = float(center_coords[1])  # Easting
                center_y = float(center_coords[0])  # Northing

                # Convert radius and delta to float
                radius_val = float(radius)
                delta_val = float(delta)

                # Interpolate points along the arc
                arc_points = interpolate_arc(
                    center_x, center_y,
                    start_x, start_y,
                    end_x, end_y,
                    radius_val, delta_val, rotation,
                    num_points=50
                )

                # Add all arc points
                coord_points.extend(arc_points)
            else:
                # Fallback: if curve data is incomplete, just use start and end
                if start_elem is not None:
                    coords = start_elem.text.strip().split()
                    if len(coords) >= 2:
                        coord_points.append((float(coords[1]), float(coords[0])))

                if end_elem is not None:
                    coords = end_elem.text.strip().split()
                    if len(coords) >= 2:
                        coord_points.append((float(coords[1]), float(coords[0])))

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
    Transform 2D coordinates from source CRS to target CRS.

    Note: This function handles horizontal alignments only (no elevation).
    LandXML alignment files typically contain only 2D horizontal geometry.

    Args:
        points: List of (easting, northing) tuples in source CRS (X, Y order)
        source_epsg: Source coordinate system (default: EPSG:2871 - CA State Plane Zone II)
        target_epsg: Target coordinate system (default: EPSG:4326 - WGS84)

    Returns:
        List of (lon, lat) tuples in target CRS (2D only)
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
