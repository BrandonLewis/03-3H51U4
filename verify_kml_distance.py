#!/usr/bin/env python3
"""
Verify the distance between CM 10.99 and RW Sta 0+032.67 in the KML files.
"""

from pyproj import Geod

def main():
    print("=" * 80)
    print("KML FILE DISTANCE VERIFICATION")
    print("=" * 80)

    # Coordinates from the KML files
    cm_lon = -121.05710441630382
    cm_lat = 39.16382034053008

    rw_lon = -121.05724844861956
    rw_lat = 39.163814301755465

    print("\nCoordinates from KML files (WGS84):")
    print(f"  CM 10.99:         lon={cm_lon:.10f}, lat={cm_lat:.10f}")
    print(f"  RW Sta 0+032.67:  lon={rw_lon:.10f}, lat={rw_lat:.10f}")

    # Calculate distance using WGS84 ellipsoid
    geod = Geod(ellps='WGS84')
    azimuth1, azimuth2, distance_meters = geod.inv(cm_lon, cm_lat, rw_lon, rw_lat)

    # Convert to feet
    distance_ft = distance_meters * 3.28084  # International feet
    distance_us_ft = distance_meters / (1200/3937)  # US Survey feet

    print("\n" + "-" * 80)
    print("DISTANCE CALCULATION")
    print("-" * 80)
    print(f"  Distance: {distance_meters:.3f} meters")
    print(f"  Distance: {distance_ft:.2f} feet (international)")
    print(f"  Distance: {distance_us_ft:.2f} feet (US Survey)")

    print("\n" + "-" * 80)
    print("ANALYSIS")
    print("-" * 80)

    if 40 < distance_us_ft < 43:
        print(f"  ✓ Result: {distance_us_ft:.2f} ft matches the problem (~41 ft)")
        print("  ✗ Expected: ~83 ft")
        print("  ✗ Error: Distance is approximately 2x too small")
    elif 80 < distance_us_ft < 86:
        print(f"  ✓ Result: {distance_us_ft:.2f} ft matches expected (~83 ft)")
    else:
        print(f"  ? Result: {distance_us_ft:.2f} ft")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    print("\nThe distance in the KML files is ~{:.2f} ft, which confirms the problem.".format(distance_us_ft))
    print("\nSince both points are correctly transformed to WGS84 and the distance")
    print("is still wrong, this means the SOURCE coordinates for the IFC points")
    print("are incorrect or misinterpreted.")

    print("\nThe IFC coordinates (2081471.33 E, 666613.68 N) in EPSG:2767 (meters)")
    print("are being correctly transformed to WGS84, but they don't represent")
    print("the actual location of RW Sta 0+032.67.")

    print("\n" + "=" * 80)
    print("ROOT CAUSE HYPOTHESIS")
    print("=" * 80)

    print("\nThe IFC file coordinates might be:")
    print("  1. In a different coordinate system than EPSG:2767")
    print("  2. In EPSG:2767 but with an incorrect origin/offset")
    print("  3. Scaled incorrectly (e.g., stored as half the actual values)")
    print("  4. In feet (EPSG:2871) but stored in the wrong coordinate space")

    print("\nLet me test if the IFC coordinates are in a LOCAL coordinate system")
    print("that needs to be offset to match the project coordinate system...")

    # What if the IFC coords need an offset?
    # Let's work backwards from the correct position

    # We know:
    # - CM 10.99 is at (6829001.34 E, 2187051.01 N) in EPSG:2871 (feet)
    # - Distance should be 83 ft
    # - IFC has X=2081471.33, Y=666613.68

    # Transform CM to EPSG:2767 to see the coordinate space
    from pyproj import Transformer

    trans_ft_to_m = Transformer.from_crs('EPSG:2871', 'EPSG:2767', always_xy=True)
    cm_x_m, cm_y_m = trans_ft_to_m.transform(6829001.34, 2187051.01)

    print("\n" + "-" * 80)
    print("COORDINATE SPACE ANALYSIS")
    print("-" * 80)

    print(f"\nCM 10.99 in EPSG:2767 (meters):")
    print(f"  X (Easting):  {cm_x_m:.2f} m")
    print(f"  Y (Northing): {cm_y_m:.2f} m")

    print(f"\nRW Sta 0+032.67 from IFC (claimed EPSG:2767):")
    print(f"  X (Easting):  2081471.33 m")
    print(f"  Y (Northing): 666613.68 m")

    print(f"\nOffset between them:")
    print(f"  ΔX: {cm_x_m - 2081471.33:.2f} m")
    print(f"  ΔY: {cm_y_m - 666613.68:.2f} m")

    # Calculate what the offset would need to be for 83 ft distance
    # Current distance is 40.90 ft in EPSG:2871
    # We need to find where RW should be for 83 ft

    trans_m_to_ft = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
    rw_x_ft, rw_y_ft = trans_m_to_ft.transform(2081471.33, 666613.68)

    print(f"\n" + "-" * 80)
    print("TRANSFORMED POSITIONS IN EPSG:2871 (feet)")
    print("-" * 80)

    print(f"\nCM 10.99:")
    print(f"  Easting:  {6829001.34:.2f} ft")
    print(f"  Northing: {2187051.01:.2f} ft")

    print(f"\nRW Sta 0+032.67 (current):")
    print(f"  Easting:  {rw_x_ft:.2f} ft")
    print(f"  Northing: {rw_y_ft:.2f} ft")

    import math
    current_dist = math.sqrt((6829001.34 - rw_x_ft)**2 + (2187051.01 - rw_y_ft)**2)
    print(f"\nCurrent distance: {current_dist:.2f} ft")

    # Calculate required position for 83 ft
    # Vector from CM to RW
    dx = rw_x_ft - 6829001.34
    dy = rw_y_ft - 2187051.01

    # Normalize and scale to 83 ft
    scale = 83.0 / current_dist
    dx_new = dx * scale
    dy_new = dy * scale

    rw_x_target_ft = 6829001.34 + dx_new
    rw_y_target_ft = 2187051.01 + dy_new

    print(f"\nRequired RW position for 83 ft distance (EPSG:2871):")
    print(f"  Easting:  {rw_x_target_ft:.2f} ft")
    print(f"  Northing: {rw_y_target_ft:.2f} ft")

    # Transform back to EPSG:2767
    rw_x_target_m, rw_y_target_m = trans_ft_to_m.transform(rw_x_target_ft, rw_y_target_ft)

    print(f"\nRequired RW position for 83 ft distance (EPSG:2767):")
    print(f"  X (Easting):  {rw_x_target_m:.2f} m")
    print(f"  Y (Northing): {rw_y_target_m:.2f} m")

    print(f"\nCurrent IFC coordinates:")
    print(f"  X (Easting):  2081471.33 m")
    print(f"  Y (Northing): 666613.68 m")

    print(f"\nRequired offset to IFC coordinates:")
    print(f"  ΔX: {rw_x_target_m - 2081471.33:.2f} m")
    print(f"  ΔY: {rw_y_target_m - 666613.68:.2f} m")

    # Check if this offset is consistent
    offset_x = rw_x_target_m - 2081471.33
    offset_y = rw_y_target_m - 666613.68

    print(f"\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    print("\nBased on this analysis, the IFC coordinates need an offset of:")
    print(f"  ΔX = {offset_x:.2f} m")
    print(f"  ΔY = {offset_y:.2f} m")

    print("\nThis small offset (~13m in X, ~1m in Y) suggests that:")
    print("  1. The coordinate system is correct (EPSG:2767)")
    print("  2. There's a local origin offset in the IFC file")
    print("  3. OR the surveyed coordinates for RW Sta 0+032.67 are incorrect in the IFC")

    print("\nTo fix this, you should:")
    print("  1. Check if there's a project base point or origin defined in the IFC")
    print("  2. Verify the surveyed coordinates for RW Sta 0+032.67")
    print("  3. Check if multiple stations show the same systematic offset")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
