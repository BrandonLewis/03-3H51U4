#!/usr/bin/env python3
"""
Convert DXF files containing retaining wall points to KML format.
Coordinates are in EPSG:2871 (NAD83(HARN) California Zone 2, US Survey Feet).
"""

import ezdxf
from pyproj import Transformer
import sys
import os
import math

def get_transformer(source_epsg='EPSG:2871', target_epsg='EPSG:4326'):
    """
    Create a coordinate transformer (cached to reuse).

    Args:
        source_epsg: Source coordinate system (default: EPSG:2871)
        target_epsg: Target coordinate system (default: WGS84)

    Returns:
        Transformer object
    """
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)

def transform_point(x, y, z, transformer):
    """
    Transform coordinates from EPSG:2871 (US Survey Feet) to WGS84.

    Args:
        x: Easting in US Survey Feet
        y: Northing in US Survey Feet
        z: Elevation in feet
        transformer: pyproj Transformer object

    Returns:
        tuple: (longitude, latitude, elevation)
    """
    lon, lat = transformer.transform(x, y)
    return lon, lat, z

def calculate_cumulative_distances(points):
    """
    Calculate cumulative distance along a series of points.

    Args:
        points: List of tuples (x, y, z, layer)

    Returns:
        list: Cumulative distances in feet
    """
    if not points:
        return []

    distances = [0.0]  # First point is at distance 0

    for i in range(1, len(points)):
        x1, y1, z1, _ = points[i-1]
        x2, y2, z2, _ = points[i]

        # Calculate 2D distance (x, y only)
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        distances.append(distances[-1] + dist)

    return distances

def format_station(station_feet):
    """
    Format station value in standard civil engineering format.

    Args:
        station_feet: Station in feet (e.g., 10048.77)

    Returns:
        str: Formatted station (e.g., "100+48.77")
    """
    hundreds = int(station_feet // 100)
    feet = station_feet % 100
    return f"{hundreds}+{feet:05.2f}"

def extract_points_from_dxf(dxf_file):
    """
    Extract point entities from DXF file.

    Args:
        dxf_file: Path to DXF file

    Returns:
        list: List of tuples (x, y, z, layer)
    """
    print(f"Reading DXF file: {dxf_file}")
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()

    points = []
    point_entities = list(msp.query('POINT'))

    print(f"Found {len(point_entities)} POINT entities")

    for entity in point_entities:
        loc = entity.dxf.location
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
        points.append((loc.x, loc.y, loc.z, layer))

    return points

def extract_polylines_from_dxf(dxf_file):
    """
    Extract polyline entities from DXF file.

    Args:
        dxf_file: Path to DXF file

    Returns:
        list: List of polylines, each containing list of (x, y, z) tuples
    """
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()

    polylines = []

    # Get LWPOLYLINE entities (lightweight polylines)
    for entity in msp.query('LWPOLYLINE'):
        coords = []
        for point in entity.get_points():
            # LWPOLYLINE points are (x, y) or (x, y, z) tuples
            x, y = point[0], point[1]
            z = point[2] if len(point) > 2 else 0
            coords.append((x, y, z))
        if coords:
            polylines.append(coords)

    # Get POLYLINE entities (3D polylines)
    for entity in msp.query('POLYLINE'):
        coords = []
        for vertex in entity.vertices:
            loc = vertex.dxf.location
            coords.append((loc.x, loc.y, loc.z))
        if coords:
            polylines.append(coords)

    print(f"Found {len(polylines)} polyline entities")
    return polylines

def create_kml(points, polylines, output_file, file_description, start_station=None, end_station=None):
    """
    Create KML file from points and polylines.

    Args:
        points: List of tuples (x, y, z, layer)
        polylines: List of polylines
        output_file: Output KML file path
        file_description: Description for the KML file
        start_station: Starting station in feet (e.g., 10000 for 100+00.00)
        end_station: Ending station in feet (e.g., 11048.77 for 110+48.77)
    """
    # Create transformer once and reuse
    print(f"  Creating coordinate transformer...")
    transformer = get_transformer()

    # Calculate cumulative distances for station interpolation
    if points and start_station is not None and end_station is not None:
        print(f"  Calculating cumulative distances...")
        cumulative_distances = calculate_cumulative_distances(points)
        total_distance = cumulative_distances[-1]
        print(f"  Total distance: {total_distance:.2f} feet")
        print(f"  Station range: {format_station(start_station)} to {format_station(end_station)}")

    # Use list for efficient string building
    kml_parts = []

    kml_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>{os.path.basename(output_file)}</name>
    <description>{file_description}</description>

    <Style id="pointStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <scale>0.6</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
            </Icon>
        </IconStyle>
        <LabelStyle>
            <scale>0.7</scale>
        </LabelStyle>
    </Style>

    <Style id="lineStyle">
        <LineStyle>
            <color>ff0000ff</color>
            <width>2</width>
        </LineStyle>
    </Style>
''')

    # Add points folder
    if points:
        print(f"  Processing {len(points)} points...")
        kml_parts.append(f'''
    <Folder>
        <name>Retaining Wall Points</name>
        <description>{len(points)} retaining wall points</description>
        <open>1</open>
''')

        for i, (x, y, z, layer) in enumerate(points):
            if i % 100 == 0 and i > 0:
                print(f"    Processed {i}/{len(points)} points...")

            lon, lat, elev = transform_point(x, y, z, transformer)

            # Calculate station value
            if start_station is not None and end_station is not None and cumulative_distances:
                # Interpolate station based on distance along alignment
                progress = cumulative_distances[i] / total_distance
                station_ft = start_station + (end_station - start_station) * progress
                station_str = format_station(station_ft)
            else:
                # Fallback to approximate station based on index
                station_ft = i * 8.0  # Approximate 8-foot spacing
                station_str = format_station(station_ft)

            kml_parts.append(f'''
        <Placemark>
            <name>RW Sta {station_str}</name>
            <description>
                Layer: {layer}
                Elevation: {elev:.2f} ft
                Original Coords: ({x:.2f}, {y:.2f}, {z:.2f})
            </description>
            <styleUrl>#pointStyle</styleUrl>
            <Point>
                <altitudeMode>clampToGround</altitudeMode>
                <coordinates>{lon:.10f},{lat:.10f},0</coordinates>
            </Point>
        </Placemark>
''')

        kml_parts.append('''    </Folder>
''')

    # Add polylines folder
    if polylines:
        print(f"  Processing {len(polylines)} polylines...")
        kml_parts.append(f'''
    <Folder>
        <name>Polylines</name>
        <description>{len(polylines)} polyline entities</description>
        <open>1</open>
''')

        for i, coords in enumerate(polylines):
            if i % 10 == 0 and i > 0:
                print(f"    Processed {i}/{len(polylines)} polylines...")

            kml_parts.append(f'''
        <Placemark>
            <name>Polyline {i+1}</name>
            <description>{len(coords)} vertices</description>
            <styleUrl>#lineStyle</styleUrl>
            <LineString>
                <altitudeMode>clampToGround</altitudeMode>
                <coordinates>
''')

            # Transform all coordinates at once for this polyline
            coord_strings = []
            for x, y, z in coords:
                lon, lat, elev = transform_point(x, y, z, transformer)
                coord_strings.append(f'{lon:.10f},{lat:.10f},0')

            kml_parts.append('\n'.join(f'                    {c}' for c in coord_strings))
            kml_parts.append('\n')

            kml_parts.append('''                </coordinates>
            </LineString>
        </Placemark>
''')

        kml_parts.append('''    </Folder>
''')

    kml_parts.append('''</Document>
</kml>
''')

    # Write to file
    print(f"  Writing KML file...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(kml_parts))

    print(f"Created KML file: {output_file}")
    print(f"  - {len(points)} points")
    print(f"  - {len(polylines)} polylines")

def convert_dxf_to_kml(dxf_file, output_file=None, start_station=None, end_station=None):
    """
    Convert DXF file to KML format.

    Args:
        dxf_file: Path to input DXF file
        output_file: Path to output KML file (optional)
        start_station: Starting station in feet (e.g., 10000 for 100+00.00)
        end_station: Ending station in feet (e.g., 11048.77 for 110+48.77)
    """
    if output_file is None:
        base_name = os.path.splitext(dxf_file)[0]
        output_file = f"{base_name}.kml"

    # Extract data from DXF
    points = extract_points_from_dxf(dxf_file)
    polylines = extract_polylines_from_dxf(dxf_file)

    # Create description
    file_name = os.path.basename(dxf_file)
    description = f"Converted from {file_name} - EPSG:2871 (NAD83(HARN) CA Zone 2, US Survey Feet) to WGS84"
    if start_station is not None and end_station is not None:
        description += f"\nStation range: {format_station(start_station)} to {format_station(end_station)}"

    # Create KML
    create_kml(points, polylines, output_file, description, start_station, end_station)

    return output_file

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Process specified files
        for dxf_file in sys.argv[1:]:
            if os.path.exists(dxf_file):
                convert_dxf_to_kml(dxf_file)
            else:
                print(f"Error: File not found: {dxf_file}")
    else:
        # Process all DXF files in DATA directory
        import glob
        dxf_files = glob.glob("/home/user/03-3H51U4/DATA/*.dxf")

        if not dxf_files:
            print("No DXF files found in DATA directory")
            sys.exit(1)

        print(f"Found {len(dxf_files)} DXF files to convert\n")

        for dxf_file in sorted(dxf_files):
            print(f"\n{'='*80}")
            convert_dxf_to_kml(dxf_file)

        print(f"\n{'='*80}")
        print("All conversions complete!")
