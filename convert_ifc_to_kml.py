#!/usr/bin/env python3
"""
Convert IFC (Industry Foundation Classes) files to KML for viewing in Google Earth.
Transforms coordinates from EPSG:2767 (California State Plane Zone II in meters) to WGS84.

This script extracts geometric elements from IFC files and converts them to KML format.
Uses clampToGround altitude mode for simplicity.

Note: IFC base units are meters, so we use EPSG:2767 (CA Zone 2 in meters) directly.
"""

import ifcopenshell
import ifcopenshell.geom
from pyproj import Transformer
import os
import sys
import math


def setup_ifc_settings():
    """Configure IFC geometry processing settings."""
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    settings.set(settings.WELD_VERTICES, False)
    return settings


def transform_point(x, y, z, source_epsg='EPSG:2767', target_epsg='EPSG:4326'):
    """
    Transform a single point from source CRS to target CRS.

    Args:
        x, y, z: Coordinates in source CRS (Easting, Northing, Elevation)
        source_epsg: Source coordinate system (default: EPSG:2767 - CA State Plane Zone II in meters)
        target_epsg: Target coordinate system (default: EPSG:4326 - WGS84)

    Returns:
        Tuple of (longitude, latitude, elevation)
    """
    transformer = Transformer.from_crs(source_epsg, target_epsg, always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lon, lat, z


def extract_geometry_from_ifc(ifc_file):
    """
    Extract geometric elements from an IFC file.

    Args:
        ifc_file: Path to the IFC file

    Returns:
        Dictionary containing lines, points, and other geometric elements
    """
    ifc = ifcopenshell.open(ifc_file)
    settings = setup_ifc_settings()

    lines = []
    points = []
    polygons = []

    # Get project/site information
    project = ifc.by_type("IfcProject")[0] if ifc.by_type("IfcProject") else None
    project_name = project.Name if project else "IFC Model"

    # First, try to extract points from property sets (common for survey data)
    # Build a map of elements to their properties
    element_properties = {}

    for rel in ifc.by_type("IfcRelDefinesByProperties"):
        pset = rel.RelatingPropertyDefinition
        if hasattr(pset, 'HasProperties'):
            for obj in rel.RelatedObjects:
                if obj.id() not in element_properties:
                    element_properties[obj.id()] = {}

                # Extract all properties
                for prop in pset.HasProperties:
                    if hasattr(prop, 'Name') and hasattr(prop, 'NominalValue'):
                        prop_name = prop.Name
                        if hasattr(prop.NominalValue, 'wrappedValue'):
                            prop_value = prop.NominalValue.wrappedValue
                        else:
                            prop_value = str(prop.NominalValue)
                        element_properties[obj.id()][prop_name] = prop_value

    # Now extract points with all their properties
    property_sets = ifc.by_type("IfcPropertySet")
    for pset in property_sets:
        if hasattr(pset, 'HasProperties'):
            for prop in pset.HasProperties:
                if hasattr(prop, 'Name') and prop.Name == 'Start Point':
                    if hasattr(prop, 'NominalValue') and hasattr(prop.NominalValue, 'wrappedValue'):
                        coord_str = prop.NominalValue.wrappedValue
                        # Parse coordinate string like "2081533.5399142911,666940.64371720655,0"
                        try:
                            coords = [float(x.strip()) for x in coord_str.split(',')]
                            if len(coords) >= 3:
                                # IFC coordinates are X,Y,Z (Easting, Northing, Elevation) in meters
                                # Get the element this property belongs to
                                for rel in ifc.by_type("IfcRelDefinesByProperties"):
                                    if rel.RelatingPropertyDefinition == pset:
                                        for obj in rel.RelatedObjects:
                                            # Get station if available
                                            props = element_properties.get(obj.id(), {})
                                            station = props.get('Station', '')
                                            feature_name = props.get('Feature Name', '')

                                            # Use station as name if available, otherwise use feature name or object name
                                            if station:
                                                name = f"RW Sta {station}"
                                            elif feature_name:
                                                name = feature_name
                                            elif hasattr(obj, 'Name') and obj.Name:
                                                name = obj.Name
                                            else:
                                                name = f"{obj.is_a()}"

                                            points.append({
                                                'name': name,
                                                'type': obj.is_a() if hasattr(obj, 'is_a') else 'Unknown',
                                                'coords': (coords[0], coords[1], coords[2]),  # Already in meters
                                                'station': station,
                                                'properties': props
                                            })
                                            break
                        except:
                            pass

    # If we found points from properties, return early
    if points:
        return {
            'project_name': project_name,
            'lines': lines,
            'points': points,
            'polygons': polygons
        }

    # Otherwise, extract all products with geometric representation
    products = ifc.by_type("IfcProduct")

    for product in products:
        try:
            # Skip if no placement or representation
            if not hasattr(product, 'ObjectPlacement') or not hasattr(product, 'Representation'):
                continue

            if product.ObjectPlacement is None or product.Representation is None:
                continue

            # Try to get geometry
            try:
                shape = ifcopenshell.geom.create_shape(settings, product)
                geometry = shape.geometry

                # Get vertices
                verts = geometry.verts
                edges = geometry.edges
                faces = geometry.faces

                # Group vertices into triplets (x, y, z)
                vertices = [(verts[i], verts[i+1], verts[i+2]) for i in range(0, len(verts), 3)]

                # Extract lines from edges
                if edges:
                    for i in range(0, len(edges), 2):
                        if i+1 < len(edges):
                            v1_idx = edges[i]
                            v2_idx = edges[i+1]
                            if v1_idx < len(vertices) and v2_idx < len(vertices):
                                v1 = vertices[v1_idx]
                                v2 = vertices[v2_idx]
                                lines.append({
                                    'name': product.Name or f"{product.is_a()}",
                                    'type': product.is_a(),
                                    'points': [v1, v2]
                                })

                # Extract faces/polygons
                if faces and len(faces) >= 3:
                    # Group faces into triangles
                    for i in range(0, len(faces), 3):
                        if i+2 < len(faces):
                            tri_indices = [faces[i], faces[i+1], faces[i+2]]
                            if all(idx < len(vertices) for idx in tri_indices):
                                triangle = [vertices[idx] for idx in tri_indices]
                                polygons.append({
                                    'name': product.Name or f"{product.is_a()}",
                                    'type': product.is_a(),
                                    'points': triangle
                                })

                # If we have vertices but no edges, treat as points
                if vertices and not edges and not faces:
                    for v in vertices:
                        points.append({
                            'name': product.Name or f"{product.is_a()}",
                            'type': product.is_a(),
                            'coords': v
                        })

            except Exception as e:
                # If geometry extraction fails, try to get placement coordinates
                if hasattr(product, 'ObjectPlacement'):
                    try:
                        placement = product.ObjectPlacement
                        if hasattr(placement, 'RelativePlacement'):
                            rel_placement = placement.RelativePlacement
                            if hasattr(rel_placement, 'Location'):
                                location = rel_placement.Location
                                if hasattr(location, 'Coordinates'):
                                    coords = location.Coordinates
                                    if len(coords) >= 3:
                                        points.append({
                                            'name': product.Name or f"{product.is_a()}",
                                            'type': product.is_a(),
                                            'coords': (coords[0], coords[1], coords[2])
                                        })
                    except:
                        pass

        except Exception as e:
            continue

    return {
        'project_name': project_name,
        'lines': lines,
        'points': points,
        'polygons': polygons
    }


def create_kml_from_geometry(geometry_data, output_file):
    """
    Create a KML file from extracted IFC geometry.

    Args:
        geometry_data: Dictionary containing geometric elements
        output_file: Path to output KML file
    """
    project_name = geometry_data['project_name']
    lines = geometry_data['lines']
    points = geometry_data['points']
    polygons = geometry_data['polygons']

    # Extract file name for better layer naming
    import os
    file_basename = os.path.splitext(os.path.basename(output_file))[0]

    # Build KML content
    kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{file_basename}</name>
    <description>Retaining Wall (RW) points from IFC file. Coordinates in EPSG:2767 (CA State Plane Zone II, meters) converted to WGS84.</description>

    <Style id="lineStyle">
      <LineStyle>
        <color>ff00ffff</color>
        <width>2</width>
      </LineStyle>
    </Style>

    <Style id="rwPointStyle">
      <IconStyle>
        <color>ff0000ff</color>
        <scale>1.0</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <color>ffffffff</color>
        <scale>0.8</scale>
      </LabelStyle>
    </Style>

    <Style id="polygonStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>1</width>
      </LineStyle>
      <PolyStyle>
        <color>7f0000ff</color>
      </PolyStyle>
    </Style>
'''

    # Add lines organized in a folder
    if lines:
        kml_content += f'''
    <Folder>
      <name>Lines</name>
      <description>{len(lines)} line features</description>
      <open>0</open>
'''
        for idx, line in enumerate(lines):
            name = line['name'] or f"Line {idx+1}"
            line_type = line['type']
            coords = []

            for point in line['points']:
                lon, lat, elev = transform_point(point[0], point[1], point[2])
                coords.append(f'{lon},{lat},0')

            kml_content += f'''
      <Placemark>
        <name>{name}</name>
        <description>Type: {line_type}</description>
        <styleUrl>#lineStyle</styleUrl>
        <LineString>
          <extrude>0</extrude>
          <tessellate>1</tessellate>
          <altitudeMode>clampToGround</altitudeMode>
          <coordinates>
            {' '.join(coords)}
          </coordinates>
        </LineString>
      </Placemark>
'''
        kml_content += '''    </Folder>
'''

    # Add points organized in a folder
    if points:
        kml_content += f'''
    <Folder>
      <name>Retaining Wall Points</name>
      <description>{len(points)} retaining wall station points</description>
      <open>1</open>
'''
        for idx, point in enumerate(points):
            name = point['name'] or f"Point {idx+1}"
            point_type = point['type']
            lon, lat, elev = transform_point(point['coords'][0], point['coords'][1], point['coords'][2])

            # Build description with properties
            station = point.get('station', 'N/A')
            props = point.get('properties', {})

            description_lines = [
                f"Station: {station}",
                f"Type: {point_type}",
                f"Coordinates (State Plane EPSG:2767):",
                f"  Easting: {point['coords'][0]:.2f} m",
                f"  Northing: {point['coords'][1]:.2f} m"
            ]

            # Add additional properties if available
            if 'Direction' in props:
                description_lines.append(f"Direction: {props['Direction']}")
            if 'Length' in props:
                description_lines.append(f"Length: {props['Length']}")
            if 'Horizontal Offset' in props:
                description_lines.append(f"Horizontal Offset: {props['Horizontal Offset']}")

            description = '\n'.join(description_lines)

            kml_content += f'''
      <Placemark>
        <name>{name}</name>
        <description>{description}</description>
        <styleUrl>#rwPointStyle</styleUrl>
        <Point>
          <altitudeMode>clampToGround</altitudeMode>
          <coordinates>{lon},{lat},0</coordinates>
        </Point>
      </Placemark>
'''
        kml_content += '''    </Folder>
'''

    # Add polygons organized in a folder
    if polygons:
        kml_content += f'''
    <Folder>
      <name>Polygons</name>
      <description>{len(polygons)} polygon features</description>
      <open>0</open>
'''
        for idx, polygon in enumerate(polygons):
            name = polygon['name'] or f"Polygon {idx+1}"
            polygon_type = polygon['type']
            coords = []

            for point in polygon['points']:
                lon, lat, elev = transform_point(point[0], point[1], point[2])
                coords.append(f'{lon},{lat},0')

            # Close the polygon
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])

            kml_content += f'''
      <Placemark>
        <name>{name}</name>
        <description>Type: {polygon_type}</description>
        <styleUrl>#polygonStyle</styleUrl>
        <Polygon>
          <extrude>0</extrude>
          <tessellate>1</tessellate>
          <altitudeMode>clampToGround</altitudeMode>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                {' '.join(coords)}
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
'''
        kml_content += '''    </Folder>
'''

    kml_content += '''  </Document>
</kml>
'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)

    print(f"Created KML file: {output_file}")
    print(f"  Lines: {len(lines)}")
    print(f"  Points: {len(points)}")
    print(f"  Polygons: {len(polygons)}")


def convert_ifc_to_kml(ifc_file, output_file=None):
    """
    Convert an IFC file to KML format.

    Args:
        ifc_file: Path to input IFC file
        output_file: Path to output KML file (default: same name with .kml extension)
    """
    if output_file is None:
        output_file = os.path.splitext(ifc_file)[0] + '.kml'

    print(f"\nProcessing: {ifc_file}")

    # Extract geometry from IFC
    geometry_data = extract_geometry_from_ifc(ifc_file)
    print(f"  Project: {geometry_data['project_name']}")

    # Create KML file
    create_kml_from_geometry(geometry_data, output_file)

    return output_file


def main():
    """Main function to process IFC files."""

    # Look for IFC files in DATA directory
    data_dir = 'DATA'

    if len(sys.argv) > 1:
        # Process specific file(s) from command line
        ifc_files = sys.argv[1:]
    else:
        # Auto-discover IFC files in DATA directory
        if not os.path.exists(data_dir):
            print(f"ERROR: {data_dir} directory not found!")
            sys.exit(1)

        ifc_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.ifc')]

    if not ifc_files:
        print("ERROR: No IFC files found!")
        print("\nUsage: python3 convert_ifc_to_kml.py [ifc_file1] [ifc_file2] ...")
        sys.exit(1)

    print("IFC to KML Converter")
    print("=" * 60)
    print(f"Found {len(ifc_files)} IFC file(s) to convert")

    # Process each IFC file
    kml_files = []
    for ifc_file in sorted(ifc_files):
        if not os.path.exists(ifc_file):
            print(f"WARNING: File not found: {ifc_file}")
            continue

        try:
            kml_file = convert_ifc_to_kml(ifc_file)
            kml_files.append(kml_file)
        except Exception as e:
            print(f"ERROR processing {ifc_file}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Conversion complete! Created {len(kml_files)} KML file(s):")
    for kml_file in kml_files:
        print(f"  - {kml_file}")
    print("\nYou can now open these files in Google Earth to view the IFC geometry.")


if __name__ == '__main__':
    main()
