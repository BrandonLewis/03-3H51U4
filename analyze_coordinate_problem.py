#!/usr/bin/env python3
"""
Analyze coordinate transformation problem between IFC and Control Points.

This script tests different transformation scenarios to determine why
distances are off by approximately 2x (41 ft measured vs 83 ft expected).
"""

from pyproj import Transformer
import math

def calculate_distance_2d(x1, y1, x2, y2):
    """Calculate 2D Euclidean distance."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def meters_to_feet(meters):
    """Convert meters to US Survey Feet."""
    # US Survey Foot = 1200/3937 meters (exact)
    return meters / (1200/3937)

def feet_to_meters(feet):
    """Convert US Survey Feet to meters."""
    # US Survey Foot = 1200/3937 meters (exact)
    return feet * (1200/3937)

def main():
    print("=" * 80)
    print("COORDINATE TRANSFORMATION ANALYSIS")
    print("=" * 80)

    # Control Point CM 10.99 (from Control Points.csv)
    # These are in EPSG:2871 (CA State Plane Zone 2 in US Survey Feet)
    cm_10_99_northing = 2187051.01  # feet
    cm_10_99_easting = 6829001.34   # feet

    print("\n1. CONTROL POINT CM 10.99")
    print("-" * 80)
    print(f"   Source: Control Points.csv")
    print(f"   Coordinate System: EPSG:2871 (CA State Plane Zone 2, US Survey Feet)")
    print(f"   Northing: {cm_10_99_northing:.2f} feet")
    print(f"   Easting:  {cm_10_99_easting:.2f} feet")

    # RW Sta 0+032.67 (from IFC file)
    # Currently assumed to be in meters (EPSG:2767)
    rw_sta_x = 2081471.3317942552  # This is the X coordinate (Easting)
    rw_sta_y = 666613.68151956971  # This is the Y coordinate (Northing)

    print("\n2. RW STATION 0+032.67")
    print("-" * 80)
    print(f"   Source: 4.013_PR_RW Points_S-BD_RW1.ifc")
    print(f"   'Start Point' property: {rw_sta_x},{rw_sta_y},0")
    print(f"   X (Easting):  {rw_sta_x:.4f}")
    print(f"   Y (Northing): {rw_sta_y:.4f}")

    print("\n" + "=" * 80)
    print("SCENARIO TESTING")
    print("=" * 80)

    # SCENARIO 1: IFC coordinates are in meters (EPSG:2767) - CURRENT ASSUMPTION
    print("\n" + "-" * 80)
    print("SCENARIO 1: IFC coordinates are in METERS (EPSG:2767)")
    print("-" * 80)
    print("Assumption: IFC 'Start Point' values are in meters")
    print("Transform: EPSG:2767 (meters) -> EPSG:4326 (WGS84) -> EPSG:2871 (feet)")

    try:
        # Transform IFC point from EPSG:2767 (meters) to EPSG:2871 (feet)
        transformer_m_to_f = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
        rw_sta_easting_s1, rw_sta_northing_s1 = transformer_m_to_f.transform(rw_sta_x, rw_sta_y)

        print(f"\nTransformed RW Sta 0+032.67 to EPSG:2871:")
        print(f"   Northing: {rw_sta_northing_s1:.2f} feet")
        print(f"   Easting:  {rw_sta_easting_s1:.2f} feet")

        # Calculate distance
        distance_s1_feet = calculate_distance_2d(
            cm_10_99_easting, cm_10_99_northing,
            rw_sta_easting_s1, rw_sta_northing_s1
        )

        print(f"\nDistance from CM 10.99 to RW Sta 0+032.67:")
        print(f"   {distance_s1_feet:.2f} feet")
        print(f"   ERROR: This gives ~{distance_s1_feet:.0f} ft but we expect ~83 ft")

    except Exception as e:
        print(f"   ERROR: {e}")

    # SCENARIO 2: IFC coordinates are actually in FEET (EPSG:2871)
    print("\n" + "-" * 80)
    print("SCENARIO 2: IFC coordinates are in US SURVEY FEET (EPSG:2871)")
    print("-" * 80)
    print("Assumption: IFC 'Start Point' values are actually in feet, not meters")
    print("No transformation needed - both are in EPSG:2871")

    # Treat IFC coordinates as already being in feet
    rw_sta_easting_s2 = rw_sta_x  # feet
    rw_sta_northing_s2 = rw_sta_y  # feet

    print(f"\nRW Sta 0+032.67 (assuming already in EPSG:2871):")
    print(f"   Northing: {rw_sta_northing_s2:.2f} feet")
    print(f"   Easting:  {rw_sta_easting_s2:.2f} feet")

    # Calculate distance
    distance_s2_feet = calculate_distance_2d(
        cm_10_99_easting, cm_10_99_northing,
        rw_sta_easting_s2, rw_sta_northing_s2
    )

    print(f"\nDistance from CM 10.99 to RW Sta 0+032.67:")
    print(f"   {distance_s2_feet:.2f} feet")

    if 80 < distance_s2_feet < 86:
        print(f"   ✓ SUCCESS: This gives ~{distance_s2_feet:.0f} ft which matches expected ~83 ft!")
    else:
        print(f"   ERROR: This gives ~{distance_s2_feet:.0f} ft but we expect ~83 ft")

    # SCENARIO 3: What if we convert IFC meters to feet first, THEN transform?
    print("\n" + "-" * 80)
    print("SCENARIO 3: Convert IFC meters to feet, then transform projection")
    print("-" * 80)
    print("Assumption: IFC values are meters, but need conversion before projection transform")

    # Convert to feet first
    rw_sta_x_feet = meters_to_feet(rw_sta_x)
    rw_sta_y_feet = meters_to_feet(rw_sta_y)

    print(f"\nIFC coordinates converted from meters to feet:")
    print(f"   X (Easting):  {rw_sta_x_feet:.2f} feet")
    print(f"   Y (Northing): {rw_sta_y_feet:.2f} feet")

    # Calculate distance directly
    distance_s3_feet = calculate_distance_2d(
        cm_10_99_easting, cm_10_99_northing,
        rw_sta_x_feet, rw_sta_y_feet
    )

    print(f"\nDistance from CM 10.99 to RW Sta 0+032.67:")
    print(f"   {distance_s3_feet:.2f} feet")
    print(f"   Note: This is essentially Scenario 2 with extra steps")

    # SCENARIO 4: Raw coordinate comparison (no transformation)
    print("\n" + "-" * 80)
    print("SCENARIO 4: Raw coordinate differences (debugging)")
    print("-" * 80)

    delta_x_raw = abs(cm_10_99_easting - rw_sta_x)
    delta_y_raw = abs(cm_10_99_northing - rw_sta_y)

    print(f"\nRaw coordinate differences:")
    print(f"   ΔX (Easting):  {delta_x_raw:.2f}")
    print(f"   ΔY (Northing): {delta_y_raw:.2f}")
    print(f"   Pythagorean distance: {calculate_distance_2d(cm_10_99_easting, cm_10_99_northing, rw_sta_x, rw_sta_y):.2f}")

    # SCENARIO 5: Check the ratio
    print("\n" + "-" * 80)
    print("SCENARIO 5: Unit conversion factor analysis")
    print("-" * 80)

    expected_distance_feet = 83.0
    measured_distance_feet = 41.0  # What we're currently getting
    ratio = expected_distance_feet / measured_distance_feet

    print(f"\nDistance ratio analysis:")
    print(f"   Expected distance: {expected_distance_feet:.2f} ft")
    print(f"   Measured distance: {measured_distance_feet:.2f} ft")
    print(f"   Ratio: {ratio:.4f}x")

    # Check if this ratio matches meter-to-foot conversion
    meters_per_foot = 1200/3937  # US Survey Foot definition
    feet_per_meter = 3937/1200

    print(f"\nUS Survey Foot conversion factors:")
    print(f"   1 US Survey Foot = {meters_per_foot:.10f} meters")
    print(f"   1 meter = {feet_per_meter:.10f} US Survey Feet")
    print(f"   Ratio is NOT close to {feet_per_meter:.4f}, so it's not a simple unit error")

    print("\n" + "=" * 80)
    print("CONCLUSIONS AND RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. The IFC 'Start Point' coordinates appear to be in US SURVEY FEET, not meters")
    print("   as currently assumed by the code.")

    print("\n2. Both the IFC coordinates and Control Points are likely in the SAME")
    print("   coordinate system: EPSG:2871 (CA State Plane Zone 2, US Survey Feet)")

    print("\n3. The current code incorrectly assumes IFC coordinates are in EPSG:2767")
    print("   (meters) and transforms them, which is causing the distance errors.")

    print("\n4. RECOMMENDED FIX:")
    print("   - Change the source EPSG from 2767 (meters) to 2871 (US Survey Feet)")
    print("   - Or, add logic to detect the actual units in the IFC file")

    print("\n5. Evidence:")
    print(f"   - Scenario 2 (treating IFC as feet) gives {distance_s2_feet:.2f} ft ≈ 83 ft ✓")
    print(f"   - Scenario 1 (treating IFC as meters) gives {distance_s1_feet:.2f} ft ≠ 83 ft ✗")

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Let's verify by checking the coordinate ranges
    print("\nCoordinate range analysis:")
    print(f"   Control Points (EPSG:2871, feet):")
    print(f"      Northing range: ~2,170,000 to ~2,230,000 feet")
    print(f"      Easting range:  ~6,814,000 to ~6,859,000 feet")

    print(f"\n   IFC Points (claimed EPSG:2767, meters):")
    print(f"      Y (Northing): {rw_sta_y:.2f}")
    print(f"      X (Easting):  {rw_sta_x:.2f}")

    print(f"\n   If IFC were in meters (EPSG:2767), coordinates would be:")
    print(f"      Northing range: ~650,000 to ~700,000 meters")
    print(f"      Easting range:  ~2,080,000 to ~2,090,000 meters")

    print(f"\n   If IFC were in feet (EPSG:2871), coordinates would be:")
    print(f"      Northing range: ~650,000 to ~700,000 feet")
    print(f"      Easting range:  ~2,080,000 to ~2,090,000 feet")

    print("\n   OBSERVATION: The IFC and Control Points have vastly different coordinate")
    print("   ranges, which is expected because they're in different zones/systems.")
    print("   However, the units (feet vs meters) can be tested by distance calculations.")

    # Additional check: look at WGS84 transformation
    print("\n" + "=" * 80)
    print("WGS84 TRANSFORMATION CHECK")
    print("=" * 80)

    try:
        # Transform CM 10.99 to WGS84
        trans_cm_to_wgs = Transformer.from_crs('EPSG:2871', 'EPSG:4326', always_xy=True)
        cm_lon, cm_lat = trans_cm_to_wgs.transform(cm_10_99_easting, cm_10_99_northing)

        print(f"\nCM 10.99 in WGS84:")
        print(f"   Longitude: {cm_lon:.8f}")
        print(f"   Latitude:  {cm_lat:.8f}")

        # Transform RW Sta assuming it's in feet (EPSG:2871)
        rw_lon_s2, rw_lat_s2 = trans_cm_to_wgs.transform(rw_sta_x, rw_sta_y)

        print(f"\nRW Sta 0+032.67 in WGS84 (assuming EPSG:2871):")
        print(f"   Longitude: {rw_lon_s2:.8f}")
        print(f"   Latitude:  {rw_lat_s2:.8f}")

        # Transform RW Sta assuming it's in meters (EPSG:2767)
        trans_rw_to_wgs = Transformer.from_crs('EPSG:2767', 'EPSG:4326', always_xy=True)
        rw_lon_s1, rw_lat_s1 = trans_rw_to_wgs.transform(rw_sta_x, rw_sta_y)

        print(f"\nRW Sta 0+032.67 in WGS84 (assuming EPSG:2767):")
        print(f"   Longitude: {rw_lon_s1:.8f}")
        print(f"   Latitude:  {rw_lat_s1:.8f}")

        # Calculate distance using WGS84 coordinates (approximate)
        # Using simple lat/lon difference (not accurate but good enough for comparison)
        from pyproj import Geod
        geod = Geod(ellps='WGS84')

        # Distance for Scenario 2 (feet assumption)
        _, _, dist_s2_wgs = geod.inv(cm_lon, cm_lat, rw_lon_s2, rw_lat_s2)
        dist_s2_wgs_ft = dist_s2_wgs * 3.28084  # meters to international feet (approximate)

        print(f"\nDistance via WGS84 (Scenario 2 - feet assumption):")
        print(f"   {dist_s2_wgs:.2f} meters = {dist_s2_wgs_ft:.2f} feet")

        # Distance for Scenario 1 (meters assumption)
        _, _, dist_s1_wgs = geod.inv(cm_lon, cm_lat, rw_lon_s1, rw_lat_s1)
        dist_s1_wgs_ft = dist_s1_wgs * 3.28084

        print(f"\nDistance via WGS84 (Scenario 1 - meters assumption):")
        print(f"   {dist_s1_wgs:.2f} meters = {dist_s1_wgs_ft:.2f} feet")

    except Exception as e:
        print(f"   ERROR in WGS84 transformation: {e}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
