#!/usr/bin/env python3
"""
Test different scenarios for IFC coordinate transformation.
Investigates whether the site origin offset should be applied to Start Point coordinates.
"""

import math

# ============================================================================
# DATA FROM IFC FILE: 4.023_PR_RW Points_S-BD_RW2.ifc
# ============================================================================

# Site Origin at #25
SITE_ORIGIN = {
    'easting': 2081539.5615699999,   # meters
    'northing': 667013.22788000002,   # meters
    'elevation': 696.52140385999996   # meters
}

# Element Placement at #53 (negative of site origin)
ELEMENT_PLACEMENT = {
    'easting': -2081539.5615699999,   # meters
    'northing': -667013.22788000002,  # meters
    'elevation': -696.52140385999996  # meters
}

# Start Point for Station 0+000.00 (from line 88)
# This is the first station in the retaining wall
STATION_0_START_POINT = {
    'easting': 2081533.5399142911,    # meters
    'northing': 666940.64371720655,   # meters
    'elevation': 0                     # meters
}

# Since we don't have station 0+032.67 exactly, let's use station 0+043.89 which is close
# From the IFC file around line 228
STATION_043_START_POINT = {
    'easting': 2081545.6179682398,    # meters
    'northing': 666982.08735550242,   # meters
    'elevation': 0                     # meters
}

# ============================================================================
# DATA FROM CONTROL POINTS: Control Points.csv
# ============================================================================

# CM 10.99 from Control Points.csv (line 14)
# These appear to be in California State Plane Zone 2 US Survey Feet (EPSG:2226)
CM_10_99_FEET = {
    'northing': 2187051.01,  # US Survey Feet
    'easting': 6829001.34,   # US Survey Feet
    'elevation': 2235.97     # US Survey Feet
}

# Convert CM 10.99 to meters (EPSG:2767)
# US Survey Foot = 0.3048006096012192 meters
US_SURVEY_FOOT_TO_METER = 0.3048006096012192

CM_10_99_METERS = {
    'northing': CM_10_99_FEET['northing'] * US_SURVEY_FOOT_TO_METER,
    'easting': CM_10_99_FEET['easting'] * US_SURVEY_FOOT_TO_METER,
    'elevation': CM_10_99_FEET['elevation'] * US_SURVEY_FOOT_TO_METER
}

print("=" * 80)
print("IFC SITE ORIGIN OFFSET INVESTIGATION")
print("=" * 80)
print()

print("DATA SUMMARY")
print("-" * 80)
print(f"Site Origin (EPSG:2767 meters):")
print(f"  Easting:  {SITE_ORIGIN['easting']:15.2f} m")
print(f"  Northing: {SITE_ORIGIN['northing']:15.2f} m")
print(f"  Elevation: {SITE_ORIGIN['elevation']:14.2f} m")
print()

print(f"Element Placement (negative of site origin):")
print(f"  Easting:  {ELEMENT_PLACEMENT['easting']:15.2f} m")
print(f"  Northing: {ELEMENT_PLACEMENT['northing']:15.2f} m")
print(f"  Elevation: {ELEMENT_PLACEMENT['elevation']:14.2f} m")
print()

print(f"RW Station 0+000.00 Start Point:")
print(f"  Easting:  {STATION_0_START_POINT['easting']:15.2f} m")
print(f"  Northing: {STATION_0_START_POINT['northing']:15.2f} m")
print(f"  Elevation: {STATION_0_START_POINT['elevation']:14.2f} m")
print()

print(f"RW Station 0+043.89 Start Point (closest to 0+032.67):")
print(f"  Easting:  {STATION_043_START_POINT['easting']:15.2f} m")
print(f"  Northing: {STATION_043_START_POINT['northing']:15.2f} m")
print(f"  Elevation: {STATION_043_START_POINT['elevation']:14.2f} m")
print()

print(f"CM 10.99 (converted to EPSG:2767 meters from US Survey Feet):")
print(f"  Easting:  {CM_10_99_METERS['easting']:15.2f} m")
print(f"  Northing: {CM_10_99_METERS['northing']:15.2f} m")
print(f"  Elevation: {CM_10_99_METERS['elevation']:14.2f} m")
print()

# Expected distance from user
EXPECTED_DISTANCE_FT = 83.0
print(f"Expected distance from CM 10.99 to RW Sta ~0+032.67: {EXPECTED_DISTANCE_FT} ft")
print()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_distance(point1, point2):
    """Calculate 3D Euclidean distance between two points."""
    dx = point2['easting'] - point1['easting']
    dy = point2['northing'] - point1['northing']
    dz = point2['elevation'] - point1['elevation']
    return math.sqrt(dx**2 + dy**2 + dz**2)

def calculate_horizontal_distance(point1, point2):
    """Calculate 2D horizontal distance between two points."""
    dx = point2['easting'] - point1['easting']
    dy = point2['northing'] - point1['northing']
    return math.sqrt(dx**2 + dy**2)

def meters_to_feet(meters):
    """Convert meters to US Survey Feet."""
    return meters / US_SURVEY_FOOT_TO_METER

def feet_to_meters(feet):
    """Convert US Survey Feet to meters."""
    return feet * US_SURVEY_FOOT_TO_METER

# ============================================================================
# SCENARIO TESTING
# ============================================================================

print("=" * 80)
print("TESTING COORDINATE TRANSFORMATION SCENARIOS")
print("=" * 80)
print()

# Interpolate a point at station ~0+032.67 between 0+000.00 and 0+043.89
# 32.67 ft = 9.96 m along the alignment
# 43.89 ft = 13.38 m total length
# Ratio: 9.96 / 13.38 = 0.744

def interpolate_station(station_name, target_station_ft):
    """Interpolate a point along the retaining wall at the target station."""
    # Get station values in meters
    station_0_ft = 0.0
    station_043_ft = 43.89

    # Calculate interpolation factor
    if target_station_ft < station_0_ft or target_station_ft > station_043_ft:
        print(f"Warning: Station {target_station_ft} is outside range [{station_0_ft}, {station_043_ft}]")

    factor = (target_station_ft - station_0_ft) / (station_043_ft - station_0_ft)

    # Interpolate coordinates
    interpolated = {
        'easting': STATION_0_START_POINT['easting'] + factor * (STATION_043_START_POINT['easting'] - STATION_0_START_POINT['easting']),
        'northing': STATION_0_START_POINT['northing'] + factor * (STATION_043_START_POINT['northing'] - STATION_0_START_POINT['northing']),
        'elevation': STATION_0_START_POINT['elevation'] + factor * (STATION_043_START_POINT['elevation'] - STATION_0_START_POINT['elevation'])
    }

    return interpolated

# Interpolate station 0+032.67
RW_STA_032_67_INTERPOLATED = interpolate_station("0+032.67", 32.67)

print(f"Interpolated RW Station 0+032.67:")
print(f"  Easting:  {RW_STA_032_67_INTERPOLATED['easting']:15.2f} m")
print(f"  Northing: {RW_STA_032_67_INTERPOLATED['northing']:15.2f} m")
print(f"  Elevation: {RW_STA_032_67_INTERPOLATED['elevation']:14.2f} m")
print()

# ============================================================================
# SCENARIO A: Start Point is already in world coordinates (CURRENT ASSUMPTION)
# ============================================================================

print("-" * 80)
print("SCENARIO A: Start Point is already in world coordinates")
print("-" * 80)
print("Assumption: The Start Point values are already in EPSG:2767 (meters)")
print("            and need NO transformation.")
print()

rw_sta_scenario_a = RW_STA_032_67_INTERPOLATED.copy()

distance_a_3d = calculate_distance(CM_10_99_METERS, rw_sta_scenario_a)
distance_a_2d = calculate_horizontal_distance(CM_10_99_METERS, rw_sta_scenario_a)

print(f"RW Sta 0+032.67 coordinates (Scenario A):")
print(f"  Easting:  {rw_sta_scenario_a['easting']:15.2f} m")
print(f"  Northing: {rw_sta_scenario_a['northing']:15.2f} m")
print()
print(f"Distance from CM 10.99 to RW Sta 0+032.67:")
print(f"  3D Distance:   {distance_a_3d:10.2f} m = {meters_to_feet(distance_a_3d):10.2f} ft")
print(f"  2D Horizontal: {distance_a_2d:10.2f} m = {meters_to_feet(distance_a_2d):10.2f} ft")
print()
print(f"Comparison to expected {EXPECTED_DISTANCE_FT} ft:")
print(f"  Difference: {abs(meters_to_feet(distance_a_2d) - EXPECTED_DISTANCE_FT):10.2f} ft")
print(f"  Match: {'YES' if abs(meters_to_feet(distance_a_2d) - EXPECTED_DISTANCE_FT) < 5 else 'NO'}")
print()

# ============================================================================
# SCENARIO B: Start Point is in local coordinates, ADD site origin
# ============================================================================

print("-" * 80)
print("SCENARIO B: Start Point is in local coordinates, ADD site origin")
print("-" * 80)
print("Assumption: The Start Point values are in local coordinates relative to")
print("            the site origin. We ADD the site origin to get world coords.")
print()

rw_sta_scenario_b = {
    'easting': RW_STA_032_67_INTERPOLATED['easting'] + SITE_ORIGIN['easting'],
    'northing': RW_STA_032_67_INTERPOLATED['northing'] + SITE_ORIGIN['northing'],
    'elevation': RW_STA_032_67_INTERPOLATED['elevation'] + SITE_ORIGIN['elevation']
}

distance_b_3d = calculate_distance(CM_10_99_METERS, rw_sta_scenario_b)
distance_b_2d = calculate_horizontal_distance(CM_10_99_METERS, rw_sta_scenario_b)

print(f"RW Sta 0+032.67 coordinates (Scenario B):")
print(f"  Easting:  {rw_sta_scenario_b['easting']:15.2f} m")
print(f"  Northing: {rw_sta_scenario_b['northing']:15.2f} m")
print()
print(f"Distance from CM 10.99 to RW Sta 0+032.67:")
print(f"  3D Distance:   {distance_b_3d:10.2f} m = {meters_to_feet(distance_b_3d):10.2f} ft")
print(f"  2D Horizontal: {distance_b_2d:10.2f} m = {meters_to_feet(distance_b_2d):10.2f} ft")
print()
print(f"Comparison to expected {EXPECTED_DISTANCE_FT} ft:")
print(f"  Difference: {abs(meters_to_feet(distance_b_2d) - EXPECTED_DISTANCE_FT):10.2f} ft")
print(f"  Match: {'YES' if abs(meters_to_feet(distance_b_2d) - EXPECTED_DISTANCE_FT) < 5 else 'NO'}")
print()

# ============================================================================
# SCENARIO C: Start Point is in local coordinates, SUBTRACT site origin
# ============================================================================

print("-" * 80)
print("SCENARIO C: Start Point is in local coordinates, SUBTRACT site origin")
print("-" * 80)
print("Assumption: The Start Point values need to have the site origin")
print("            SUBTRACTED to get world coords (opposite direction).")
print()

rw_sta_scenario_c = {
    'easting': RW_STA_032_67_INTERPOLATED['easting'] - SITE_ORIGIN['easting'],
    'northing': RW_STA_032_67_INTERPOLATED['northing'] - SITE_ORIGIN['northing'],
    'elevation': RW_STA_032_67_INTERPOLATED['elevation'] - SITE_ORIGIN['elevation']
}

distance_c_3d = calculate_distance(CM_10_99_METERS, rw_sta_scenario_c)
distance_c_2d = calculate_horizontal_distance(CM_10_99_METERS, rw_sta_scenario_c)

print(f"RW Sta 0+032.67 coordinates (Scenario C):")
print(f"  Easting:  {rw_sta_scenario_c['easting']:15.2f} m")
print(f"  Northing: {rw_sta_scenario_c['northing']:15.2f} m")
print()
print(f"Distance from CM 10.99 to RW Sta 0+032.67:")
print(f"  3D Distance:   {distance_c_3d:10.2f} m = {meters_to_feet(distance_c_3d):10.2f} ft")
print(f"  2D Horizontal: {distance_c_2d:10.2f} m = {meters_to_feet(distance_c_2d):10.2f} ft")
print()
print(f"Comparison to expected {EXPECTED_DISTANCE_FT} ft:")
print(f"  Difference: {abs(meters_to_feet(distance_c_2d) - EXPECTED_DISTANCE_FT):10.2f} ft")
print(f"  Match: {'YES' if abs(meters_to_feet(distance_c_2d) - EXPECTED_DISTANCE_FT) < 5 else 'NO'}")
print()

# ============================================================================
# SCENARIO D: Start Point is relative to element placement
# ============================================================================

print("-" * 80)
print("SCENARIO D: Start Point is relative to element placement")
print("-" * 80)
print("Assumption: Start Point coordinates are relative to the element placement")
print("            at #53, which itself is relative to the site origin at #27.")
print("            We add ELEMENT_PLACEMENT to the Start Point.")
print()

rw_sta_scenario_d = {
    'easting': RW_STA_032_67_INTERPOLATED['easting'] + ELEMENT_PLACEMENT['easting'],
    'northing': RW_STA_032_67_INTERPOLATED['northing'] + ELEMENT_PLACEMENT['northing'],
    'elevation': RW_STA_032_67_INTERPOLATED['elevation'] + ELEMENT_PLACEMENT['elevation']
}

distance_d_3d = calculate_distance(CM_10_99_METERS, rw_sta_scenario_d)
distance_d_2d = calculate_horizontal_distance(CM_10_99_METERS, rw_sta_scenario_d)

print(f"RW Sta 0+032.67 coordinates (Scenario D):")
print(f"  Easting:  {rw_sta_scenario_d['easting']:15.2f} m")
print(f"  Northing: {rw_sta_scenario_d['northing']:15.2f} m")
print()
print(f"Distance from CM 10.99 to RW Sta 0+032.67:")
print(f"  3D Distance:   {distance_d_3d:10.2f} m = {meters_to_feet(distance_d_3d):10.2f} ft")
print(f"  2D Horizontal: {distance_d_2d:10.2f} m = {meters_to_feet(distance_d_2d):10.2f} ft")
print()
print(f"Comparison to expected {EXPECTED_DISTANCE_FT} ft:")
print(f"  Difference: {abs(meters_to_feet(distance_d_2d) - EXPECTED_DISTANCE_FT):10.2f} ft")
print(f"  Match: {'YES' if abs(meters_to_feet(distance_d_2d) - EXPECTED_DISTANCE_FT) < 5 else 'NO'}")
print()

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print(f"Expected distance: {EXPECTED_DISTANCE_FT:.2f} ft")
print()
print(f"Scenario A (current - no offset):          {meters_to_feet(distance_a_2d):10.2f} ft  Δ = {abs(meters_to_feet(distance_a_2d) - EXPECTED_DISTANCE_FT):6.2f} ft")
print(f"Scenario B (add site origin):              {meters_to_feet(distance_b_2d):10.2f} ft  Δ = {abs(meters_to_feet(distance_b_2d) - EXPECTED_DISTANCE_FT):6.2f} ft")
print(f"Scenario C (subtract site origin):         {meters_to_feet(distance_c_2d):10.2f} ft  Δ = {abs(meters_to_feet(distance_c_2d) - EXPECTED_DISTANCE_FT):6.2f} ft")
print(f"Scenario D (add element placement):        {meters_to_feet(distance_d_2d):10.2f} ft  Δ = {abs(meters_to_feet(distance_d_2d) - EXPECTED_DISTANCE_FT):6.2f} ft")
print()

# Find the best match
distances = [
    ('A (no offset)', distance_a_2d),
    ('B (add site origin)', distance_b_2d),
    ('C (subtract site origin)', distance_c_2d),
    ('D (add element placement)', distance_d_2d)
]

best_scenario = min(distances, key=lambda x: abs(meters_to_feet(x[1]) - EXPECTED_DISTANCE_FT))

print(f"BEST MATCH: Scenario {best_scenario[0]}")
print(f"  Distance: {meters_to_feet(best_scenario[1]):.2f} ft")
print(f"  Error: {abs(meters_to_feet(best_scenario[1]) - EXPECTED_DISTANCE_FT):.2f} ft")
print()

# Additional analysis
print("-" * 80)
print("ADDITIONAL OBSERVATIONS")
print("-" * 80)
print()
print(f"1. The IFC file has USE_WORLD_COORDS set to True in the converter.")
print(f"   This suggests ifcopenshell should handle coordinate transformations.")
print()
print(f"2. The site placement (#27) uses IFCAXIS2PLACEMENT3D with the site origin.")
print(f"   This establishes the world coordinate system origin.")
print()
print(f"3. The element placement (#55) uses IFCLOCALPLACEMENT referencing #27,")
print(f"   with an IFCAXIS2PLACEMENT3D at the negative of the site origin.")
print(f"   This suggests a double transformation: site origin -> element placement.")
print()
print(f"4. However, the Start Point property values already appear to be in")
print(f"   the vicinity of the site origin, suggesting they're already in world")
print(f"   coordinates and the element placement is NOT applied to them.")
print()
print(f"5. The ~2x discrepancy ({meters_to_feet(distance_a_2d):.2f} ft vs {EXPECTED_DISTANCE_FT:.2f} ft)")
print(f"   suggests a coordinate system issue, but none of the standard offset")
print(f"   scenarios produce the expected ~83 ft distance.")
print()
