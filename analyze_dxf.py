#!/usr/bin/env python3
"""
Analyze DXF file structure to understand entities and coordinate system.
"""

import ezdxf
import sys

def analyze_dxf(dxf_file):
    """Analyze a DXF file and print information about its contents."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {dxf_file}")
    print(f"{'='*80}\n")

    # Load the DXF file
    doc = ezdxf.readfile(dxf_file)

    # Print DXF version
    print(f"DXF Version: {doc.dxfversion}")
    print(f"Units: {doc.units}")

    # Print header variables
    print("\n--- Header Variables ---")
    header = doc.header
    if '$INSUNITS' in header:
        print(f"INSUNITS: {header['$INSUNITS']}")
    if '$MEASUREMENT' in header:
        print(f"MEASUREMENT: {header['$MEASUREMENT']}")

    # Get modelspace
    msp = doc.modelspace()

    # Count entity types
    entity_counts = {}
    for entity in msp:
        entity_type = entity.dxftype()
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

    print("\n--- Entity Counts ---")
    for entity_type, count in sorted(entity_counts.items()):
        print(f"{entity_type}: {count}")

    # Examine sample entities
    print("\n--- Sample Entities ---")

    # Look at POINT entities
    points = list(msp.query('POINT'))
    if points:
        print(f"\nFound {len(points)} POINT entities")
        print("First 5 points:")
        for i, point in enumerate(points[:5]):
            loc = point.dxf.location
            print(f"  Point {i+1}: X={loc.x:.2f}, Y={loc.y:.2f}, Z={loc.z:.2f}")
            # Check for attributes
            if hasattr(point.dxf, 'layer'):
                print(f"    Layer: {point.dxf.layer}")

    # Look at TEXT entities
    texts = list(msp.query('TEXT'))
    if texts:
        print(f"\nFound {len(texts)} TEXT entities")
        print("First 10 text labels:")
        for i, text in enumerate(texts[:10]):
            print(f"  {i+1}. '{text.dxf.text}' at ({text.dxf.insert.x:.2f}, {text.dxf.insert.y:.2f})")

    # Look at MTEXT entities
    mtexts = list(msp.query('MTEXT'))
    if mtexts:
        print(f"\nFound {len(mtexts)} MTEXT entities")
        print("First 10 mtext labels:")
        for i, mtext in enumerate(mtexts[:10]):
            text_content = mtext.text[:50] if len(mtext.text) > 50 else mtext.text
            print(f"  {i+1}. '{text_content}' at ({mtext.dxf.insert.x:.2f}, {mtext.dxf.insert.y:.2f})")

    # Look for attribute definitions and block inserts
    inserts = list(msp.query('INSERT'))
    if inserts:
        print(f"\nFound {len(inserts)} INSERT (block) entities")
        print("First 10 block inserts with attributes:")
        for i, insert in enumerate(inserts[:10]):
            print(f"  {i+1}. Block: {insert.dxf.name} at ({insert.dxf.insert.x:.2f}, {insert.dxf.insert.y:.2f})")
            if insert.has_attrib:
                for attrib in insert.attribs:
                    print(f"      {attrib.dxf.tag}: {attrib.dxf.text}")

    # Look at layers
    print("\n--- Layers ---")
    for layer in doc.layers:
        print(f"  {layer.dxf.name}")

    # Check coordinate range
    print("\n--- Coordinate Range Analysis ---")
    all_x, all_y = [], []
    for entity in msp:
        if entity.dxftype() == 'POINT':
            loc = entity.dxf.location
            all_x.append(loc.x)
            all_y.append(loc.y)
        elif entity.dxftype() == 'INSERT':
            loc = entity.dxf.insert
            all_x.append(loc.x)
            all_y.append(loc.y)

    if all_x and all_y:
        print(f"X range: {min(all_x):.2f} to {max(all_x):.2f}")
        print(f"Y range: {min(all_y):.2f} to {max(all_y):.2f}")
        print(f"\nCoordinate magnitudes suggest EPSG:2767 or EPSG:2871")
        print(f"(California State Plane Zone 2, around 2M easting, 600K-700K northing)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for dxf_file in sys.argv[1:]:
            analyze_dxf(dxf_file)
    else:
        # Analyze all DXF files in DATA directory
        import glob
        dxf_files = glob.glob("/home/user/03-3H51U4/DATA/*.dxf")
        for dxf_file in sorted(dxf_files):
            analyze_dxf(dxf_file)
