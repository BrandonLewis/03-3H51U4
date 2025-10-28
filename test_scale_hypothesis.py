#!/usr/bin/env python3
"""
Focused test of the 2x scale hypothesis for CM 10.99 to RW Sta 0+035.11.
This script tests different scale factors to find which produces ~83 ft.
"""

import math
import ifcopenshell

IFC_FILE = "/home/user/03-3H51U4/DATA/4.013_PR_RW Points_S-BD_RW1.ifc"

print("=" * 80)
print("FOCUSED SCALE FACTOR TEST")
print("Problem: CM 10.99 to RW Sta 0+035.11")
print("Expected from plans: ~83 ft")
print("=" * 80)

# ============================================================================
# METHOD 1: Using user-provided coordinates
# ============================================================================
print("\nMETHOD 1: User-Provided Coordinates")
print("-" * 80)

# From user's problem statement
rw_sta_0035 = (2081471.89, 666616.08, 0)  # meters
site_origin = (2081539.56, 667013.23, 0)  # meters
expected_ft = 83.0

print(f"RW Sta 0+035.11: E={rw_sta_0035[0]:.2f}, N={rw_sta_0035[1]:.2f}")
print(f"Site Origin:     E={site_origin[0]:.2f}, N={site_origin[1]:.2f}")

# Calculate offset
offset_e = rw_sta_0035[0] - site_origin[0]
offset_n = rw_sta_0035[1] - site_origin[1]

print(f"\nOffset from Site Origin:")
print(f"  ΔE = {offset_e:.2f} m")
print(f"  ΔN = {offset_n:.2f} m")

# Direct distance (current approach)
distance_m = math.sqrt(offset_e**2 + offset_n**2)
distance_ft = distance_m * 3.28084

print(f"\nDirect distance:")
print(f"  {distance_m:.2f} m = {distance_ft:.2f} ft")
print(f"  Error from expected: {abs(distance_ft - expected_ft):.2f} ft")
print(f"  This is {distance_ft/expected_ft:.2f}x the expected distance")

# ============================================================================
# Test multiple scale factors
# ============================================================================
print("\n" + "=" * 80)
print("TESTING DIFFERENT SCALE FACTORS")
print("=" * 80)

test_factors = [
    0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7,
    1.0, 1.5, 2.0, 2.11, 2.5, 3.0, 3.28084
]

print(f"\nTarget distance: {expected_ft:.2f} ft")
print("-" * 80)

best_match = None
best_error = float('inf')

for factor in test_factors:
    scaled_e = offset_e * factor
    scaled_n = offset_n * factor
    scaled_dist_m = math.sqrt(scaled_e**2 + scaled_n**2)
    scaled_dist_ft = scaled_dist_m * 3.28084
    error = abs(scaled_dist_ft - expected_ft)
    error_pct = (error / expected_ft) * 100

    if error < best_error:
        best_error = error
        best_match = factor

    marker = " ✓✓✓" if error < 1.0 else (" ✓" if error < 5.0 else "")
    print(f"Factor {factor:6.3f}x: {scaled_dist_ft:8.2f} ft  (error: {error:6.2f} ft, {error_pct:5.1f}%){marker}")

print(f"\nBest match: {best_match}x with error of {best_error:.2f} ft")

# ============================================================================
# What factor is needed for exact match?
# ============================================================================
print("\n" + "=" * 80)
print("EXACT FACTOR CALCULATION")
print("=" * 80)

# We want: sqrt((offset_e * k)^2 + (offset_n * k)^2) * 3.28084 = 83
# This simplifies to: k * sqrt(offset_e^2 + offset_n^2) * 3.28084 = 83
# So: k = 83 / (sqrt(offset_e^2 + offset_n^2) * 3.28084)

exact_factor = expected_ft / (math.sqrt(offset_e**2 + offset_n**2) * 3.28084)
print(f"Exact factor needed: {exact_factor:.6f}x")

# Verify
scaled_e = offset_e * exact_factor
scaled_n = offset_n * exact_factor
scaled_dist_m = math.sqrt(scaled_e**2 + scaled_n**2)
scaled_dist_ft = scaled_dist_m * 3.28084
print(f"Verification: {scaled_dist_ft:.2f} ft (should be {expected_ft:.2f} ft)")

# ============================================================================
# METHOD 2: Extract actual coordinates from IFC
# ============================================================================
print("\n" + "=" * 80)
print("METHOD 2: Extract Coordinates from IFC")
print("=" * 80)

ifc = ifcopenshell.open(IFC_FILE)

# Find RW Sta 0+035.11 in the IFC
print("\nSearching for RW Sta 0+035.11 in IFC...")
found_point = None

elements = ifc.by_type("IfcBuildingElementProxy")
for element in elements:
    for definition in element.IsDefinedBy:
        if definition.is_a("IfcRelDefinesByProperties"):
            property_set = definition.RelatingPropertyDefinition
            if property_set.is_a("IfcPropertySet"):
                station_val = None
                start_point_val = None

                for prop in property_set.HasProperties:
                    if prop.Name == "Station":
                        station_val = prop.NominalValue.wrappedValue
                    if prop.Name == "Start Point":
                        start_point_val = prop.NominalValue.wrappedValue

                # Check if this is our station
                if station_val and "0+035" in station_val:
                    print(f"  Found: {element.Name}")
                    print(f"  Station: {station_val}")
                    if start_point_val:
                        coords = [float(x) for x in start_point_val.split(',')]
                        print(f"  Start Point: E={coords[0]:.2f}, N={coords[1]:.2f}, Z={coords[2]:.2f}")
                        found_point = coords

# Also find CM 10.99 from Control Points or other source
print("\nSearching for CM 10.99 reference...")
print("(CM points are in Control Points CSV with different coordinate system)")

# ============================================================================
# HYPOTHESIS: IFC coordinates are scaled by 0.5 (or need to be doubled)
# ============================================================================
print("\n" + "=" * 80)
print("KEY HYPOTHESIS")
print("=" * 80)

print(f"""
The exact factor needed is {exact_factor:.6f}x

Possible explanations:
1. IFC coordinates are in a different unit than declared
   - Declared as meters but actually in some other unit

2. IFC export applied a scale factor during export
   - Civil 3D may have applied a transformation

3. Site origin is incorrect
   - The reference point used for offset calculation is wrong

4. Coordinate reference frame mismatch
   - IFC uses local project coordinates
   - Plans use different reference system

5. The distance measurement is ALONG THE ALIGNMENT, not straight-line
   - If the alignment is curved, straight-line distance ≠ station distance
   - This could explain the discrepancy!
""")

# ============================================================================
# Test if distance is along alignment vs straight-line
# ============================================================================
print("=" * 80)
print("ALIGNMENT DISTANCE vs STRAIGHT-LINE DISTANCE")
print("=" * 80)

print("""
CRITICAL QUESTION: How was the 83 ft measured?

Option A: Straight-line distance (Euclidean)
  - sqrt((ΔE)^2 + (ΔN)^2)
  - This is what we've been calculating

Option B: Distance along alignment (station distance)
  - Following the curve/line of the road
  - Could be different from straight-line if alignment is curved

Option C: Horizontal distance only (ignoring elevation)
  - We've been doing this already (Z=0)

If the 83 ft is measured ALONG THE ALIGNMENT:
  - We should be comparing station values, not coordinate distances
  - The curve of the alignment would make the station distance longer
    than the straight-line coordinate distance

ACTION NEEDED:
  - Clarify how the 83 ft was measured
  - Check if CM 10.99 and RW Sta 0+035.11 are on the same alignment
  - If they're on different alignments, we need to find the relationship
""")

print("\n" + "=" * 80)
print("END OF SCALE FACTOR TEST")
print("=" * 80)
