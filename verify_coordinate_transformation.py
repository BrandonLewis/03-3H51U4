#!/usr/bin/env python3
"""
Critical verification: Transform CM 10.99 from EPSG:2871 (feet) to EPSG:2767 (meters)
and calculate the ACTUAL distance to RW Sta 0+035.11.

This will determine if the coordinate system mismatch is the root cause.
"""

from pyproj import Transformer
import math
import csv

print("=" * 80)
print("CRITICAL COORDINATE TRANSFORMATION VERIFICATION")
print("=" * 80)

# ============================================================================
# PART 1: Transform CM 10.99 from EPSG:2871 to EPSG:2767
# ============================================================================

print("\nPART 1: Transform CM 10.99 to matching coordinate system")
print("-" * 80)

# CM 10.99 from Control Points CSV (in EPSG:2871 feet)
cm_easting_ft = 6829001.34
cm_northing_ft = 2187051.01

print(f"\nCM 10.99 (from Control Points CSV in EPSG:2871):")
print(f"  Easting:  {cm_easting_ft:.2f} ft")
print(f"  Northing: {cm_northing_ft:.2f} ft")

# Transform from EPSG:2871 (feet) to EPSG:2767 (meters)
trans_ft_to_m = Transformer.from_crs('EPSG:2871', 'EPSG:2767', always_xy=True)
cm_easting_m, cm_northing_m = trans_ft_to_m.transform(cm_easting_ft, cm_northing_ft)

print(f"\nCM 10.99 transformed to EPSG:2767:")
print(f"  Easting:  {cm_easting_m:.2f} m")
print(f"  Northing: {cm_northing_m:.2f} m")

# ============================================================================
# PART 2: Get RW Sta 0+035.11 coordinates from IFC
# ============================================================================

print("\n" + "=" * 80)
print("PART 2: RW Sta 0+035.11 coordinates from IFC")
print("-" * 80)

# From IFC file (already in EPSG:2767 meters, according to our analysis)
rw_easting_m = 2081471.89
rw_northing_m = 666616.08

print(f"\nRW Sta 0+035.11 (from IFC in EPSG:2767):")
print(f"  Easting:  {rw_easting_m:.2f} m")
print(f"  Northing: {rw_northing_m:.2f} m")

# ============================================================================
# PART 3: Calculate distance in EPSG:2767 (both in meters now)
# ============================================================================

print("\n" + "=" * 80)
print("PART 3: Calculate distance (both in EPSG:2767)")
print("-" * 80)

delta_e = cm_easting_m - rw_easting_m
delta_n = cm_northing_m - rw_northing_m

print(f"\nOffset from RW to CM:")
print(f"  ΔE = {delta_e:.2f} m")
print(f"  ΔN = {delta_n:.2f} m")

distance_m = math.sqrt(delta_e**2 + delta_n**2)
distance_ft = distance_m * 3.28084

print(f"\nDistance (Euclidean):")
print(f"  {distance_m:.2f} m")
print(f"  {distance_ft:.2f} ft")

print(f"\nComparison:")
print(f"  Expected (from plans): 83 ft")
print(f"  Calculated: {distance_ft:.2f} ft")
print(f"  Error: {abs(distance_ft - 83):.2f} ft")

if abs(distance_ft - 83) < 10:
    print("\n  ✓✓✓ SUCCESS! Distance matches expected value!")
elif abs(distance_ft - 39.34) < 5:
    print(f"\n  ⚠ Matches user's reported measurement of 39.34 ft")
    print(f"  But this is still 2x off from expected 83 ft")
else:
    print(f"\n  ✗ Does not match either expected (83 ft) or measured (39.34 ft)")

# ============================================================================
# PART 4: Alternative - Transform RW to EPSG:2871 and compare there
# ============================================================================

print("\n" + "=" * 80)
print("PART 4: Alternative - Transform RW to EPSG:2871 (feet)")
print("-" * 80)

trans_m_to_ft = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
rw_easting_ft, rw_northing_ft = trans_m_to_ft.transform(rw_easting_m, rw_northing_m)

print(f"\nRW Sta 0+035.11 transformed to EPSG:2871:")
print(f"  Easting:  {rw_easting_ft:.2f} ft")
print(f"  Northing: {rw_northing_ft:.2f} ft")

print(f"\nCM 10.99 (in EPSG:2871):")
print(f"  Easting:  {cm_easting_ft:.2f} ft")
print(f"  Northing: {cm_northing_ft:.2f} ft")

delta_e_ft = cm_easting_ft - rw_easting_ft
delta_n_ft = cm_northing_ft - rw_northing_ft

print(f"\nOffset:")
print(f"  ΔE = {delta_e_ft:.2f} ft")
print(f"  ΔN = {delta_n_ft:.2f} ft")

distance_ft_alt = math.sqrt(delta_e_ft**2 + delta_n_ft**2)

print(f"\nDistance:")
print(f"  {distance_ft_alt:.2f} ft")

print(f"\nVerification:")
print(f"  Method 1 (both in meters): {distance_ft:.2f} ft")
print(f"  Method 2 (both in feet):   {distance_ft_alt:.2f} ft")
print(f"  Difference: {abs(distance_ft - distance_ft_alt):.4f} ft")

if abs(distance_ft - distance_ft_alt) < 0.1:
    print("  ✓ Both methods agree (as they should)")
else:
    print("  ✗ Methods disagree - transformation error!")

# ============================================================================
# PART 5: Check all CM points to find which gives ~83 ft
# ============================================================================

print("\n" + "=" * 80)
print("PART 5: Find which CM point gives ~83 ft distance")
print("-" * 80)

csv_file = "/home/user/03-3H51U4/DATA/Control Points.csv"
print(f"\nChecking all CM points from {csv_file}...")

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

cm_points = [row for row in rows if row['STATION DESIGNATION'].startswith('CM')]

print(f"Found {len(cm_points)} CM points\n")

print("Distances to RW Sta 0+035.11:")
print("-" * 80)

for cm_point in cm_points:
    name = cm_point['STATION DESIGNATION']
    e_ft = float(cm_point['EASTING'])
    n_ft = float(cm_point['NORTHING'])

    # Transform to EPSG:2767
    e_m, n_m = trans_ft_to_m.transform(e_ft, n_ft)

    # Calculate distance
    dist_m = math.sqrt((e_m - rw_easting_m)**2 + (n_m - rw_northing_m)**2)
    dist_ft = dist_m * 3.28084

    marker = ""
    if abs(dist_ft - 83) < 10:
        marker = " ✓✓✓ CLOSE TO 83 FT!"
    elif abs(dist_ft - 39.34) < 5:
        marker = " ⚠ Close to reported 39.34 ft"

    print(f"  {name:12s}: {dist_ft:8.2f} ft{marker}")

# ============================================================================
# PART 6: Check hypothesis about IFC coordinates being in feet
# ============================================================================

print("\n" + "=" * 80)
print("PART 6: Test if IFC coordinates are actually in FEET (EPSG:2871)")
print("-" * 80)

print("\nHypothesis: What if IFC 'Start Point' values are in EPSG:2871 (feet)")
print("            but declared as meters?")
print("-" * 80)

# Treat IFC values as if they're in feet (EPSG:2871)
rw_value_as_feet_e = rw_easting_m  # Same number, but interpret as feet
rw_value_as_feet_n = rw_northing_m

print(f"\nRW Sta 0+035.11 (treating IFC values as EPSG:2871 feet):")
print(f"  Easting:  {rw_value_as_feet_e:.2f} ft")
print(f"  Northing: {rw_value_as_feet_n:.2f} ft")

print(f"\nCM 10.99 (EPSG:2871):")
print(f"  Easting:  {cm_easting_ft:.2f} ft")
print(f"  Northing: {cm_northing_ft:.2f} ft")

# Direct distance (both interpreted as feet in same CRS)
dist_if_feet = math.sqrt((cm_easting_ft - rw_value_as_feet_e)**2 +
                         (cm_northing_ft - rw_value_as_feet_n)**2)

print(f"\nDistance (if IFC values are actually in EPSG:2871):")
print(f"  {dist_if_feet:.2f} ft")

print(f"\nComparison:")
print(f"  Expected: 83 ft")
print(f"  If IFC in feet: {dist_if_feet:.2f} ft")
print(f"  Error: {abs(dist_if_feet - 83):.2f} ft")

if abs(dist_if_feet - 83) < 10:
    print("\n  ✓✓✓ BREAKTHROUGH! This gives ~83 ft!")
    print("  IFC coordinates are likely in EPSG:2871 (feet) with wrong header!")
else:
    print(f"\n  ✗ Still doesn't match (off by {abs(dist_if_feet - 83):.2f} ft)")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
1. COORDINATE TRANSFORMATION RESULTS:
   CM 10.99: E={cm_easting_m:.2f} m, N={cm_northing_m:.2f} m (EPSG:2767)
   RW Sta 0+035.11: E={rw_easting_m:.2f} m, N={rw_northing_m:.2f} m (EPSG:2767)

2. DISTANCE CALCULATION (correct transformation):
   {distance_ft:.2f} ft

3. COMPARISON WITH EXPECTED:
   Expected: 83 ft
   Calculated: {distance_ft:.2f} ft
   Error: {abs(distance_ft - 83):.2f} ft
   {'✓ MATCH!' if abs(distance_ft - 83) < 10 else '✗ NO MATCH'}

4. HYPOTHESIS TEST (IFC values are feet, not meters):
   {dist_if_feet:.2f} ft
   {'✓✓✓ BREAKTHROUGH! This explains the issue!' if abs(dist_if_feet - 83) < 10 else '✗ Hypothesis rejected'}

CONCLUSION:
""")

if abs(dist_if_feet - 83) < 10:
    print("""
   The IFC file declares units as METRES but the coordinate values
   are actually in US SURVEY FEET (EPSG:2871).

   This is a CIVIL 3D EXPORT ERROR where:
   - Coordinates were exported in feet (EPSG:2871)
   - But the IFC header declares meters (wrong!)
   - This causes a ~3.28x scale error in conversions

   SOLUTION:
   - Treat IFC "Start Point" values as EPSG:2871 (feet)
   - Do NOT transform them
   - Use them directly with other EPSG:2871 data
    """)
elif abs(distance_ft - 83) < 10:
    print("""
   The coordinate transformation is correct. The IFC coordinates
   are in EPSG:2767 (meters) as declared, and transforming CM 10.99
   from EPSG:2871 (feet) produces the expected ~83 ft distance.

   The "2x scale issue" reported may have been due to:
   - Using wrong CM point coordinates
   - Not transforming between coordinate systems
   - Measurement error
    """)
else:
    print("""
   Neither hypothesis explains the discrepancy. The issue may be:
   - Wrong reference points (not actually CM 10.99 or RW Sta 0+035.11)
   - Distance measured along alignment, not straight-line
   - Different measurement method in the plans
   - Additional coordinate transformation we haven't identified

   RECOMMENDATION: Verify the source of "83 ft" measurement.
    """)

print("\n" + "=" * 80)
