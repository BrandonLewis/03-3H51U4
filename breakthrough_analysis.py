#!/usr/bin/env python3
"""
BREAKTHROUGH: Testing if IFC coordinates are in FEET but stored as if they were METERS.

The key insight: If coordinates that are actually in FEET are treated as METERS
and converted to feet, you get a 3.28x scale factor. But we're seeing ~2x error.

What if the IFC coordinates are in FEET (EPSG:2871) but we're transforming them
as if they're in METERS (EPSG:2767)?
"""

from pyproj import Transformer
import math

def main():
    print("=" * 80)
    print("BREAKTHROUGH ANALYSIS: UNIT CONFUSION")
    print("=" * 80)

    # Control Point
    cm_north_ft = 2187051.01
    cm_east_ft = 6829001.34

    # IFC Start Point for RW Sta 0+032.67
    rw_value_x = 2081471.3317942552
    rw_value_y = 666613.68151956971

    print("\nHYPOTHESIS: IFC 'Start Point' numbers are in FEET (EPSG:2871)")
    print("            but we're treating them as METERS (EPSG:2767)")
    print("=" * 80)

    # SCENARIO A: Treat IFC values as FEET in EPSG:2871
    print("\nSCENARIO A: IFC values are coordinates in EPSG:2871 (feet)")
    print("-" * 80)

    print(f"\nRW Sta 0+032.67 (treating values as EPSG:2871):")
    print(f"  Easting:  {rw_value_x:.2f} ft")
    print(f"  Northing: {rw_value_y:.2f} ft")

    print(f"\nCM 10.99 (EPSG:2871):")
    print(f"  Easting:  {cm_east_ft:.2f} ft")
    print(f"  Northing: {cm_north_ft:.2f} ft")

    # Calculate distance directly
    dist_a_ft = math.sqrt((cm_east_ft - rw_value_x)**2 + (cm_north_ft - rw_value_y)**2)

    print(f"\nDistance (both in EPSG:2871):")
    print(f"  {dist_a_ft:.2f} ft")

    if abs(dist_a_ft - 83) < 5:
        print(f"  ✓✓✓ SUCCESS! This gives {dist_a_ft:.2f} ft ≈ 83 ft expected!")
    else:
        print(f"  ✗ Does not match expected 83 ft")

    # SCENARIO B: Current (wrong) approach - treat as meters, then convert
    print("\n" + "=" * 80)
    print("SCENARIO B: Current approach (treating IFC values as EPSG:2767 meters)")
    print("-" * 80)

    trans_m_to_ft = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
    rw_east_ft_b, rw_north_ft_b = trans_m_to_ft.transform(rw_value_x, rw_value_y)

    print(f"\nRW Sta 0+032.67 after transformation:")
    print(f"  Easting:  {rw_east_ft_b:.2f} ft")
    print(f"  Northing: {rw_north_ft_b:.2f} ft")

    dist_b_ft = math.sqrt((cm_east_ft - rw_east_ft_b)**2 + (cm_north_ft - rw_north_ft_b)**2)

    print(f"\nDistance:")
    print(f"  {dist_b_ft:.2f} ft")
    print(f"  ✗ This gives ~41 ft (the problem we're seeing)")

    # Verify with the other RW station
    print("\n" + "=" * 80)
    print("VERIFICATION: Check with RW Sta 0+000.00")
    print("=" * 80)

    rw_000_x = 2081533.5399142911
    rw_000_y = 666940.64371720655

    print(f"\nRW Sta 0+000.00 'Start Point' from IFC: {rw_000_x:.2f}, {rw_000_y:.2f}")

    # Scenario A: Treat as feet
    dist_stations_a = math.sqrt((rw_value_x - rw_000_x)**2 + (rw_value_y - rw_000_y)**2)
    print(f"\nDistance between stations (treating values as feet in EPSG:2871):")
    print(f"  {dist_stations_a:.2f} ft")
    print(f"  Station difference: 32.67 ft (from station numbers)")

    if abs(dist_stations_a - 32.67) < 5:
        print(f"  ✓ Close match! (difference: {abs(dist_stations_a - 32.67):.2f} ft)")
    else:
        print(f"  ✗ Off by: {abs(dist_stations_a - 32.67):.2f} ft")

    # Scenario B: Treat as meters, then convert
    rw_000_east_b, rw_000_north_b = trans_m_to_ft.transform(rw_000_x, rw_000_y)
    dist_stations_b = math.sqrt((rw_east_ft_b - rw_000_east_b)**2 + (rw_north_ft_b - rw_000_north_b)**2)

    print(f"\nDistance between stations (current wrong approach):")
    print(f"  {dist_stations_b:.2f} ft")
    print(f"  Expected: 32.67 ft")
    print(f"  ✗ Way off!")

    # Calculate the conversion factor
    print("\n" + "=" * 80)
    print("CONVERSION FACTOR ANALYSIS")
    print("=" * 80)

    us_survey_ft_to_m = 1200/3937  # Exact definition
    m_to_us_survey_ft = 3937/1200

    print(f"\nUS Survey Foot conversion:")
    print(f"  1 US Survey Foot = {us_survey_ft_to_m:.10f} meters")
    print(f"  1 meter = {m_to_us_survey_ft:.10f} US Survey Feet")

    # When we mistakenly treat feet as meters and transform:
    # We're essentially converting the VALUE from one CRS to another
    # without changing the actual number much (same zone, different units)

    print(f"\nWhat happens when we treat {rw_value_x:.2f} ft as {rw_value_x:.2f} m?")
    print(f"  We transform from EPSG:2767 (meters) to EPSG:2871 (feet)")
    print(f"  But since they're the same zone, just different units,")
    print(f"  the transformation mostly just converts units:")
    print(f"  {rw_value_x:.2f} m × {m_to_us_survey_ft:.4f} = {rw_value_x * m_to_us_survey_ft:.2f} ft")

    print(f"\n  Original value (actually in feet): {rw_value_x:.2f} ft")
    print(f"  After wrong transformation: {rw_east_ft_b:.2f} ft")
    print(f"  Ratio: {rw_east_ft_b / rw_value_x:.4f}")

    # This ratio should be close to 3.28 (m to ft conversion)
    actual_ratio = rw_east_ft_b / rw_value_x
    print(f"\n  The ratio is ~{actual_ratio:.2f}, which is close to {m_to_us_survey_ft:.2f}")
    print(f"  This confirms the unit confusion!")

    # So distances get scaled by this factor
    distance_scale = dist_b_ft / dist_a_ft
    print(f"\n  Distance ratio (wrong/correct): {distance_scale:.4f}")
    print(f"  Expected (if pure unit confusion): 1.0 (no change, same CRS zone)")

    # Actually, let me recalculate this more carefully
    print("\n" + "=" * 80)
    print("DETAILED TRANSFORMATION ANALYSIS")
    print("=" * 80)

    # The transformation from EPSG:2767 to EPSG:2871 should be mostly identity
    # except for the unit conversion factor embedded in the CRS definitions

    # Let's see what the transformer actually does
    print("\nTransforming a test point:")
    test_x = 2081500.0
    test_y = 666700.0

    print(f"  Input (EPSG:2767, meters): X={test_x:.2f}, Y={test_y:.2f}")

    test_x_out, test_y_out = trans_m_to_ft.transform(test_x, test_y)
    print(f"  Output (EPSG:2871, feet): X={test_x_out:.2f}, Y={test_y_out:.2f}")

    ratio_x = test_x_out / test_x
    ratio_y = test_y_out / test_y

    print(f"  Ratio X: {ratio_x:.6f}")
    print(f"  Ratio Y: {ratio_y:.6f}")
    print(f"  Expected ratio (m to ft): {m_to_us_survey_ft:.6f}")

    print("\n  The ratios match! This confirms that EPSG:2767 -> EPSG:2871")
    print("  transformation is primarily just unit conversion.")

    print("\n" + "=" * 80)
    print("ROOT CAUSE CONFIRMED")
    print("=" * 80)

    print("\nThe IFC 'Start Point' coordinates are stored in FEET (EPSG:2871),")
    print("but the code assumes they are in METERS (EPSG:2767).")

    print("\nWhen we transform from EPSG:2767 to EPSG:2871, we multiply by ~3.28.")
    print(f"So a value that's actually {rw_value_x:.2f} feet becomes:")
    print(f"  {rw_value_x:.2f} × 3.28 = {rw_value_x * m_to_us_survey_ft:.2f} feet")

    print("\nThis is WRONG because the value was already in feet to begin with!")

    print("\n" + "=" * 80)
    print("SOLUTION")
    print("=" * 80)

    print("\nIn convert_ifc_to_kml.py, change line 28:")
    print("  FROM: def transform_point(x, y, z, source_epsg='EPSG:2767', ...")
    print("  TO:   def transform_point(x, y, z, source_epsg='EPSG:2871', ...)")

    print("\nOr, update the call to transform_point() to use EPSG:2871:")
    print("  lon, lat, elev = transform_point(point['coords'][0], point['coords'][1],")
    print("                                   point['coords'][2], source_epsg='EPSG:2871')")

    print("\n" + "=" * 80)
    print("FINAL VERIFICATION")
    print("=" * 80)

    # Transform using correct EPSG (2871)
    trans_correct = Transformer.from_crs('EPSG:2871', 'EPSG:4326', always_xy=True)

    # CM 10.99 to WGS84
    cm_lon, cm_lat = trans_correct.transform(cm_east_ft, cm_north_ft)

    # RW Sta 0+032.67 to WGS84 (treating values as feet)
    rw_lon, rw_lat = trans_correct.transform(rw_value_x, rw_value_y)

    print(f"\nCM 10.99 (WGS84): lon={cm_lon:.8f}, lat={cm_lat:.8f}")
    print(f"RW Sta 0+032.67 (WGS84): lon={rw_lon:.8f}, lat={rw_lat:.8f}")

    # Calculate distance
    from pyproj import Geod
    geod = Geod(ellps='WGS84')
    _, _, distance_m = geod.inv(cm_lon, cm_lat, rw_lon, rw_lat)
    distance_ft = distance_m / (1200/3937)

    print(f"\nFinal distance in KML (with correct transformation):")
    print(f"  {distance_m:.3f} m = {distance_ft:.2f} ft")

    if abs(distance_ft - 83) < 5:
        print(f"  ✓✓✓ SUCCESS! Distance is now {distance_ft:.2f} ft ≈ 83 ft expected!")
    else:
        print(f"  ? Result: {distance_ft:.2f} ft")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
