#!/usr/bin/env python3
"""
Critical investigation of IFC coordinate scale issue.
Testing hypothesis that coordinates have a 2x scale problem.
"""

import ifcopenshell
import math
import csv
from pathlib import Path

# Constants
IFC_FILE = "/home/user/03-3H51U4/DATA/4.013_PR_RW Points_S-BD_RW1.ifc"
CONTROL_POINTS_CSV = "/home/user/03-3H51U4/DATA/Control Points.csv"

# Known measurements from plans
EXPECTED_DISTANCE_FT = 83.0  # Distance from CM 10.99 to RW Sta 0+035.11 per plans
MEASURED_DISTANCE_FT = 39.34  # Distance calculated from coordinates
SCALE_RATIO = EXPECTED_DISTANCE_FT / MEASURED_DISTANCE_FT  # ~2.11x

print("=" * 80)
print("IFC COORDINATE SCALE INVESTIGATION")
print("=" * 80)
print()

# ============================================================================
# PART 1: DETAILED UNIT ANALYSIS FROM IFC FILE
# ============================================================================
print("PART 1: DETAILED UNIT ANALYSIS")
print("-" * 80)

ifc = ifcopenshell.open(IFC_FILE)

# Get all unit assignments
unit_assignments = ifc.by_type("IfcUnitAssignment")
for unit_assignment in unit_assignments:
    print(f"Unit Assignment: {unit_assignment}")
    for unit in unit_assignment.Units:
        print(f"\n  Unit: {unit.is_a()}")
        if unit.is_a("IfcSIUnit"):
            print(f"    Unit Type: {unit.UnitType}")
            print(f"    Name: {unit.Name}")
            print(f"    Prefix: {unit.Prefix}")
        elif unit.is_a("IfcConversionBasedUnit"):
            print(f"    Unit Type: {unit.UnitType}")
            print(f"    Name: {unit.Name}")
            print(f"    Conversion Factor: {unit.ConversionFactor}")
            if hasattr(unit.ConversionFactor, 'ValueComponent'):
                value = unit.ConversionFactor.ValueComponent.wrappedValue
                print(f"    Value: {value}")
                if hasattr(unit.ConversionFactor, 'UnitComponent'):
                    base_unit = unit.ConversionFactor.UnitComponent
                    print(f"    Base Unit: {base_unit}")

# Check for any scale factors in geometric representation contexts
print("\n" + "-" * 80)
print("GEOMETRIC REPRESENTATION CONTEXTS:")
contexts = ifc.by_type("IfcGeometricRepresentationContext")
for context in contexts:
    print(f"\n  Context: {context.ContextType}")
    print(f"    Precision: {context.Precision}")
    if context.WorldCoordinateSystem:
        print(f"    World Coordinate System: {context.WorldCoordinateSystem}")

# ============================================================================
# PART 2: EXTRACT SITE ORIGIN AND IFC COORDINATE DATA
# ============================================================================
print("\n" + "=" * 80)
print("PART 2: SITE ORIGIN AND IFC COORDINATES")
print("-" * 80)

# Get site placement
sites = ifc.by_type("IfcSite")
site_origin = None
if sites:
    site = sites[0]
    if site.ObjectPlacement:
        placement = site.ObjectPlacement
        if placement.is_a("IfcLocalPlacement") and placement.RelativePlacement:
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'Location'):
                location = rel_placement.Location
                if hasattr(location, 'Coordinates'):
                    coords = location.Coordinates
                    site_origin = (coords[0], coords[1], coords[2] if len(coords) > 2 else 0)
                    print(f"Site Origin (from IFC): {site_origin}")
                    print(f"  E: {site_origin[0]:.2f} m")
                    print(f"  N: {site_origin[1]:.2f} m")
                    print(f"  Z: {site_origin[2]:.2f} m")

# Extract Start Point coordinates from property sets
print("\n" + "-" * 80)
print("START POINTS FROM IFC PROPERTY SETS:")
print("-" * 80)

start_points = []
elements = ifc.by_type("IfcBuildingElementProxy")
for element in elements[:5]:  # Just first 5 for testing
    # Get property sets
    for definition in element.IsDefinedBy:
        if definition.is_a("IfcRelDefinesByProperties"):
            property_set = definition.RelatingPropertyDefinition
            if property_set.is_a("IfcPropertySet"):
                if property_set.Name == "SupportLine Rule":
                    # Look for Start Point property
                    for prop in property_set.HasProperties:
                        if prop.Name == "Start Point":
                            coord_str = prop.NominalValue.wrappedValue
                            coords = [float(x) for x in coord_str.split(',')]
                            start_points.append({
                                'element': element.Name,
                                'coords': coords,
                                'coord_str': coord_str
                            })
                            print(f"\n{element.Name}:")
                            print(f"  Start Point: {coord_str}")
                            print(f"  Parsed: E={coords[0]:.2f}, N={coords[1]:.2f}, Z={coords[2]:.2f}")

                        # Also get station info
                        if prop.Name == "Station":
                            station = prop.NominalValue.wrappedValue
                            print(f"  Station: {station}")

# ============================================================================
# PART 3: TEST SCALE FACTOR HYPOTHESIS
# ============================================================================
print("\n" + "=" * 80)
print("PART 3: SCALE FACTOR TESTING")
print("=" * 80)

# Test case: RW Sta 0+035.11
# According to user, this should be ~83 ft from CM 10.99
# But current calculation gives 39.34 ft

# Let's use example coordinates from the IFC
# RW Sta 0+035.11 mentioned by user: (2081471.89m E, 666616.08m N)
# Site Origin from user: (2081539.56m E, 667013.23m N)

rw_sta_0035 = (2081471.89, 666616.08, 0)  # User provided
site_origin_user = (2081539.56, 667013.23, 0)  # User provided

print("\nTEST CASE: CM 10.99 to RW Sta 0+035.11")
print("-" * 80)
print(f"RW Sta 0+035.11 coords: E={rw_sta_0035[0]:.2f}, N={rw_sta_0035[1]:.2f}")
print(f"Site Origin (user):     E={site_origin_user[0]:.2f}, N={site_origin_user[1]:.2f}")
print(f"Expected distance:      {EXPECTED_DISTANCE_FT:.2f} ft")
print(f"Measured distance:      {MEASURED_DISTANCE_FT:.2f} ft")
print(f"Ratio:                  {SCALE_RATIO:.2f}x")

# Calculate offset from site origin
offset_e = rw_sta_0035[0] - site_origin_user[0]
offset_n = rw_sta_0035[1] - site_origin_user[1]
print(f"\nOffset from Site Origin:")
print(f"  ΔE: {offset_e:.2f} m")
print(f"  ΔN: {offset_n:.2f} m")

# Calculate distance using current approach
current_distance_m = math.sqrt(offset_e**2 + offset_n**2)
current_distance_ft = current_distance_m * 3.28084
print(f"\nCurrent calculation:")
print(f"  Distance: {current_distance_m:.2f} m = {current_distance_ft:.2f} ft")

print("\n" + "-" * 80)
print("HYPOTHESIS TEST: Double the offset from site origin")
print("-" * 80)

# Test 1: Double the offset, then calculate distance
doubled_offset_e = offset_e * 2.0
doubled_offset_n = offset_n * 2.0
print(f"Doubled offset:")
print(f"  ΔE: {doubled_offset_e:.2f} m")
print(f"  ΔN: {doubled_offset_n:.2f} m")

doubled_distance_m = math.sqrt(doubled_offset_e**2 + doubled_offset_n**2)
doubled_distance_ft = doubled_distance_m * 3.28084
print(f"  Distance: {doubled_distance_m:.2f} m = {doubled_distance_ft:.2f} ft")
print(f"  Error from expected: {abs(doubled_distance_ft - EXPECTED_DISTANCE_FT):.2f} ft")

# Test 2: What if we apply a 2.11x factor?
scaled_offset_e = offset_e * SCALE_RATIO
scaled_offset_n = offset_n * SCALE_RATIO
scaled_distance_m = math.sqrt(scaled_offset_e**2 + scaled_offset_n**2)
scaled_distance_ft = scaled_distance_m * 3.28084
print(f"\n2.11x scaled offset:")
print(f"  ΔE: {scaled_offset_e:.2f} m")
print(f"  ΔN: {scaled_offset_n:.2f} m")
print(f"  Distance: {scaled_distance_m:.2f} m = {scaled_distance_ft:.2f} ft")
print(f"  Error from expected: {abs(scaled_distance_ft - EXPECTED_DISTANCE_FT):.2f} ft")

# ============================================================================
# PART 4: UNIT CONVERSION ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("PART 4: UNIT CONVERSION ANALYSIS")
print("=" * 80)

# US Survey foot definition from IFC
us_survey_inch_to_m = 0.025400050800101603
us_survey_ft_to_m = us_survey_inch_to_m * 12.0
international_ft_to_m = 0.3048

print(f"\nUnit conversions:")
print(f"  US Survey inch to meters: {us_survey_inch_to_m:.15f}")
print(f"  US Survey foot to meters: {us_survey_ft_to_m:.15f}")
print(f"  International foot to meters: {international_ft_to_m:.15f}")
print(f"  Ratio (US Survey / International): {us_survey_ft_to_m / international_ft_to_m:.10f}")

# Check if there's a double conversion happening
print(f"\nDouble conversion test:")
print(f"  If coordinates are in US Survey feet but treated as meters:")
value_in_us_ft = 100.0
if_treated_as_meters = value_in_us_ft
actual_meters = value_in_us_ft * us_survey_ft_to_m
error_factor = if_treated_as_meters / actual_meters
print(f"    100 US Survey feet = {actual_meters:.2f} m")
print(f"    If wrongly treated as meters: {if_treated_as_meters:.2f} m")
print(f"    Error factor: {error_factor:.4f}x")

# ============================================================================
# PART 5: CHECK IF COORDINATES ARE ACTUALLY IN DIFFERENT UNITS
# ============================================================================
print("\n" + "=" * 80)
print("PART 5: COORDINATE UNIT HYPOTHESIS")
print("=" * 80)

print("\nHypothesis: What if IFC coordinates are in US Survey FEET, not meters?")
print("-" * 80)

# If the coordinates are actually in US Survey feet:
rw_in_us_ft = rw_sta_0035[0]  # Treating the value as US Survey feet
site_in_us_ft = site_origin_user[0]

# Convert to meters
rw_in_m = rw_in_us_ft * us_survey_ft_to_m
site_in_m = site_in_us_ft * us_survey_ft_to_m

print(f"If coordinates are in US Survey feet:")
print(f"  RW Sta E-coord: {rw_in_us_ft:.2f} ft = {rw_in_m:.2f} m")
print(f"  Site Origin E: {site_in_us_ft:.2f} ft = {site_in_m:.2f} m")

# But that doesn't make sense because the values are too large for feet...
# Let's check coordinate magnitude
print(f"\nCoordinate magnitude check:")
print(f"  E-coordinate: {rw_sta_0035[0]:.0f}")
print(f"  If this is meters: reasonable for state plane")
print(f"  If this is feet: reasonable for state plane")
print(f"  => Coordinate magnitude alone doesn't tell us the unit")

# ============================================================================
# PART 6: IFCOPENSHELL UNIT INTERPRETATION TEST
# ============================================================================
print("\n" + "=" * 80)
print("PART 6: IFCOPENSHELL UNIT SCALE")
print("=" * 80)

# Try to get unit information
try:
    from ifcopenshell.util import unit as ifc_unit
    length_unit = ifc_unit.get_project_unit(ifc, "LENGTHUNIT")
    print(f"Project length unit from ifcopenshell: {length_unit}")
    unit_scale = ifc_unit.calculate_unit_scale(ifc)
    print(f"Unit scale factor: {unit_scale}")
    print(f"  This means: 1 model unit = {unit_scale} meters")
except Exception as e:
    print(f"Could not get unit scale from ifcopenshell: {e}")
    print("Continuing with manual unit analysis...")

# ============================================================================
# PART 7: COMPARISON WITH DIFFERENT SCALE SCENARIOS
# ============================================================================
print("\n" + "=" * 80)
print("PART 7: SCENARIO COMPARISON")
print("=" * 80)

scenarios = [
    ("Current approach (no scaling)", 1.0),
    ("Double offset", 2.0),
    ("Ratio scaling (2.11x)", SCALE_RATIO),
    ("Half the coordinates", 0.5),
]

print(f"\nTest: CM 10.99 to RW Sta 0+035.11")
print(f"Expected: {EXPECTED_DISTANCE_FT:.2f} ft")
print("-" * 80)

for scenario_name, scale_factor in scenarios:
    scaled_offset_e = offset_e * scale_factor
    scaled_offset_n = offset_n * scale_factor
    distance_m = math.sqrt(scaled_offset_e**2 + scaled_offset_n**2)
    distance_ft = distance_m * 3.28084
    error = abs(distance_ft - EXPECTED_DISTANCE_FT)
    error_pct = (error / EXPECTED_DISTANCE_FT) * 100

    print(f"\n{scenario_name}:")
    print(f"  Scale factor: {scale_factor:.2f}x")
    print(f"  Distance: {distance_ft:.2f} ft")
    print(f"  Error: {error:.2f} ft ({error_pct:.1f}%)")

    if error < 5.0:  # Within 5 feet
        print(f"  ✓ MATCHES EXPECTED! (within 5 ft)")

# ============================================================================
# PART 8: EXAMINE CONTROL POINTS CSV
# ============================================================================
print("\n" + "=" * 80)
print("PART 8: CONTROL POINTS ANALYSIS")
print("=" * 80)

print("\nReading Control Points CSV...")
with open(CONTROL_POINTS_CSV, 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Found {len(rows)} control points")
print("\nFirst few points:")
for row in rows[:5]:
    print(f"  {row['STATION DESIGNATION']}: E={row['EASTING']}, N={row['NORTHING']}")

# Check coordinate system
print("\nCoordinate range in Control Points CSV:")
eastings = [float(row['EASTING']) for row in rows if row['EASTING']]
northings = [float(row['NORTHING']) for row in rows if row['NORTHING']]
print(f"  Easting: {min(eastings):.0f} to {max(eastings):.0f}")
print(f"  Northing: {min(northings):.0f} to {max(northings):.0f}")

print("\nCoordinate range in IFC (Site Origin from user):")
print(f"  Easting: ~{site_origin_user[0]:.0f}")
print(f"  Northing: ~{site_origin_user[1]:.0f}")

print("\n" + "!" * 80)
print("OBSERVATION: IFC coordinates and Control Points use DIFFERENT coordinate systems!")
print(f"  IFC:           E ~{site_origin_user[0]:.0f}, N ~{site_origin_user[1]:.0f}")
print(f"  Control Points: E ~{northings[0]:.0f}, N ~{eastings[0]:.0f}")
print("  These appear to be different projections or the axes are swapped!")
print("!" * 80)

# ============================================================================
# PART 9: ALIGNMENT XML COORDINATE SYSTEM COMPARISON
# ============================================================================
print("\n" + "=" * 80)
print("PART 9: ALIGNMENT XML COORDINATE SYSTEM")
print("=" * 80)

import xml.etree.ElementTree as ET

xml_file = "/home/user/03-3H51U4/DATA/03-3H51U4-A.xml"
try:
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Namespace handling
    ns = {'lx': 'http://www.landxml.org/schema/LandXML-1.2'}

    # Get coordinate system info
    coord_sys = root.find('lx:CoordinateSystem', ns)
    if coord_sys is not None:
        print(f"\nAlignment XML Coordinate System:")
        print(f"  Description: {coord_sys.get('desc')}")
        print(f"  EPSG Code: {coord_sys.get('epsgCode')}")

    # Get units
    units = root.find('lx:Units/lx:Imperial', ns)
    if units is not None:
        print(f"\nAlignment XML Units:")
        print(f"  Linear Unit: {units.get('linearUnit')}")
        print(f"  Angular Unit: {units.get('angularUnit')}")

    # Get sample alignment coordinates
    alignment = root.find('.//lx:Alignment[@name="A"]', ns)
    if alignment is not None:
        lines = alignment.findall('.//lx:Line', ns)
        if lines:
            first_line = lines[0]
            start = first_line.find('lx:Start', ns)
            if start is not None and start.text:
                coords = start.text.split()
                print(f"\nFirst alignment point (from XML):")
                print(f"  Northing: {coords[0]}")
                print(f"  Easting: {coords[1]}")
                print(f"  (Note: In state plane coords these are typically N, E)")

    print("\n" + "-" * 80)
    print("CRITICAL FINDING:")
    print("-" * 80)
    print("XML uses EPSG:2871 (State Plane CA Zone II, US Survey Feet)")
    print("  Coordinates: N ~2,183,000 ft, E ~6,827,000 ft")
    print()
    print("IFC coordinates appear to be:")
    print("  Coordinates: E ~2,081,000, N ~666,000")
    print()
    print("These are COMPLETELY DIFFERENT coordinate systems!")
    print("The IFC likely uses EPSG:2767 (State Plane CA Zone II, METERS)")
    print()
    print("Coordinate system difference ratio:")
    xml_n = 2183846.396933
    xml_e = 6827025.598427
    ifc_e = 2081474.46679
    ifc_n = 666740.95433
    print(f"  XML N / IFC E = {xml_n / ifc_e:.4f}x")
    print(f"  XML E / IFC N = {xml_e / ifc_n:.4f}x")

except Exception as e:
    print(f"Error reading XML: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY OF FINDINGS")
print("=" * 80)

print("""
1. IFC FILE UNITS:
   - Base unit defined as METRE (IFCSIUNIT)
   - US Survey foot also defined (1 ft = 0.3048006096 m)
   - Unit scale from ifcopenshell: (see above)

2. COORDINATE SCALING ISSUE:
   - Current calculation: ~39.34 ft (WRONG)
   - Expected from plans: ~83 ft
   - Ratio: 2.11x discrepancy

3. SCALE FACTOR TESTS:
   - Doubling offsets from site origin gives ~{doubled_distance_ft:.1f} ft
   - This is {'MUCH CLOSER' if abs(doubled_distance_ft - EXPECTED_DISTANCE_FT) < 10 else 'NOT CLOSE'} to expected {EXPECTED_DISTANCE_FT:.1f} ft

4. COORDINATE SYSTEM MISMATCH:
   - IFC coordinates: E ~2,081,000 N ~666,000
   - Control Points: E ~6,800,000 N ~2,100,000
   - These are DIFFERENT coordinate systems!

5. NEXT STEPS:
   - Check alignment XML files for coordinate references
   - Verify which coordinate system is correct
   - Determine if there's a transformation matrix being applied
   - Check Civil 3D export settings for any scale factors
""".format(doubled_distance_ft=doubled_distance_ft, EXPECTED_DISTANCE_FT=EXPECTED_DISTANCE_FT))

print("\n" + "=" * 80)
print("END OF INVESTIGATION")
print("=" * 80)
