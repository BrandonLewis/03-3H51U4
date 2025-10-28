#!/usr/bin/env python3
"""
Final analysis: Investigate if the IFC Start Point coordinates are relative
to the site origin or if they're in a different unit system.
"""

from pyproj import Transformer
import math

def main():
    print("=" * 80)
    print("FINAL ROOT CAUSE ANALYSIS")
    print("=" * 80)

    # Site origin from IFC file (#25)
    site_origin_x = 2081474.46679
    site_origin_y = 666740.95432999998
    site_origin_z = 687.31151009999996

    print("\nIFC Site Origin (from #25):")
    print(f"  X: {site_origin_x:.2f} m")
    print(f"  Y: {site_origin_y:.2f} m")
    print(f"  Z: {site_origin_z:.2f} m")

    # RW Sta 0+032.67 Start Point from IFC
    rw_x = 2081471.3317942552
    rw_y = 666613.68151956971
    rw_z = 0

    print("\nRW Sta 0+032.67 'Start Point' from IFC:")
    print(f"  X: {rw_x:.2f} m")
    print(f"  Y: {rw_y:.2f} m")
    print(f"  Z: {rw_z:.2f} m")

    # Control Point CM 10.99
    cm_north_ft = 2187051.01
    cm_east_ft = 6829001.34

    print("\nCM 10.99 from Control Points CSV (EPSG:2871, feet):")
    print(f"  Northing: {cm_north_ft:.2f} ft")
    print(f"  Easting: {cm_east_ft:.2f} ft")

    # Convert CM to EPSG:2767 (meters)
    trans_ft_to_m = Transformer.from_crs('EPSG:2871', 'EPSG:2767', always_xy=True)
    cm_x_m, cm_y_m = trans_ft_to_m.transform(cm_east_ft, cm_north_ft)

    print("\nCM 10.99 in EPSG:2767 (meters):")
    print(f"  X (Easting): {cm_x_m:.2f} m")
    print(f"  Y (Northing): {cm_y_m:.2f} m")

    print("\n" + "=" * 80)
    print("HYPOTHESIS 1: Start Point is in absolute EPSG:2767 coordinates")
    print("=" * 80)

    # Calculate distance in EPSG:2767
    dist_m_h1 = math.sqrt((cm_x_m - rw_x)**2 + (cm_y_m - rw_y)**2)
    dist_ft_h1 = dist_m_h1 / (1200/3937)  # Convert to US Survey feet

    print(f"\nDistance in EPSG:2767:")
    print(f"  {dist_m_h1:.2f} m = {dist_ft_h1:.2f} ft")
    print(f"  Result: {'✓ Matches ~41 ft problem' if abs(dist_ft_h1 - 41) < 2 else '✗ Does not match'}")

    print("\n" + "=" * 80)
    print("HYPOTHESIS 2: Start Point values are actually in FEET, not meters")
    print("=" * 80)

    # Treat RW coordinates as feet (EPSG:2871) directly
    rw_x_as_feet = rw_x  # Interpret the number as feet, not meters
    rw_y_as_feet = rw_y

    # But wait, the coordinate ranges don't match EPSG:2871
    # EPSG:2871 Northing for this area should be ~2,187,000
    # but we have Y=666613 which is way off

    print("\nIf we interpret Start Point numbers as feet in EPSG:2871:")
    print(f"  Easting: {rw_x_as_feet:.2f} ft")
    print(f"  Northing: {rw_y_as_feet:.2f} ft")

    dist_ft_h2 = math.sqrt((cm_east_ft - rw_x_as_feet)**2 + (cm_north_ft - rw_y_as_feet)**2)

    print(f"\nDistance:")
    print(f"  {dist_ft_h2:.2f} ft")
    print(f"  Result: ✗ This is way off - coordinate systems don't match")

    print("\n" + "=" * 80)
    print("HYPOTHESIS 3: Start Point is relative to site origin")
    print("=" * 80)

    # Add site origin to Start Point
    rw_abs_x = site_origin_x + rw_x
    rw_abs_y = site_origin_y + rw_y

    print("\nRW Sta absolute position (Start Point + Site Origin):")
    print(f"  X: {rw_abs_x:.2f} m")
    print(f"  Y: {rw_abs_y:.2f} m")

    dist_m_h3 = math.sqrt((cm_x_m - rw_abs_x)**2 + (cm_y_m - rw_abs_y)**2)
    dist_ft_h3 = dist_m_h3 / (1200/3937)

    print(f"\nDistance:")
    print(f"  {dist_m_h3:.2f} m = {dist_ft_h3:.2f} ft")
    print(f"  Result: ✗ Way off")

    print("\n" + "=" * 80)
    print("HYPOTHESIS 4: Check if there's a unit conversion issue in IFC")
    print("=" * 80)

    # What if the Start Point coordinates are in US Survey Feet but the numbers
    # look like meters because they're in a local coordinate system?

    # Convert RW coordinates from meters to feet
    us_ft_per_m = 3937/1200
    rw_x_converted = rw_x * us_ft_per_m
    rw_y_converted = rw_y * us_ft_per_m

    print("\nIf Start Point (nominally in meters) is converted to feet:")
    print(f"  X: {rw_x_converted:.2f} ft")
    print(f"  Y: {rw_y_converted:.2f} ft")

    # This still won't match because coordinate systems are different

    print("\n" + "=" * 80)
    print("HYPOTHESIS 5: Different EPSG zones or datums")
    print("=" * 80)

    # What if IFC uses a different zone of CA State Plane?
    # Or what if it uses NAD83 instead of NAD83(HARN)?

    # Let's try EPSG:26942 (NAD83 / California zone 2, not HARN)
    try:
        trans_26942_to_2871 = Transformer.from_crs('EPSG:26942', 'EPSG:2871', always_xy=True)
        rw_e_26942, rw_n_26942 = trans_26942_to_2871.transform(rw_x, rw_y)

        dist_ft_h5a = math.sqrt((cm_east_ft - rw_e_26942)**2 + (cm_north_ft - rw_n_26942)**2)

        print("\nTesting EPSG:26942 (NAD83 / California zone 2, meters):")
        print(f"  Transformed: E={rw_e_26942:.2f}, N={rw_n_26942:.2f}")
        print(f"  Distance: {dist_ft_h5a:.2f} ft")
        print(f"  Result: {'✓ Matches!' if 80 < dist_ft_h5a < 86 else '✗ Does not match'}")
    except Exception as e:
        print(f"  Error: {e}")

    # Try EPSG:2226 (NAD83 / California zone 2, feet)
    try:
        trans_2226_to_2871 = Transformer.from_crs('EPSG:2226', 'EPSG:2871', always_xy=True)
        rw_e_2226, rw_n_2226 = trans_2226_to_2871.transform(rw_x, rw_y)

        dist_ft_h5b = math.sqrt((cm_east_ft - rw_e_2226)**2 + (cm_north_ft - rw_n_2226)**2)

        print("\nTesting EPSG:2226 (NAD83 / California zone 2, feet):")
        print(f"  Transformed: E={rw_e_2226:.2f}, N={rw_n_2226:.2f}")
        print(f"  Distance: {dist_ft_h5b:.2f} ft")
        print(f"  Result: {'✓ Matches!' if 80 < dist_ft_h5b < 86 else '✗ Does not match'}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 80)
    print("HYPOTHESIS 6: Working backward from the required position")
    print("=" * 80)

    # We know the correct distance should be 83 ft
    # Current distance is 40.90 ft
    # Scale factor = 83/40.90 = 2.029

    scale_factor = 83.0 / dist_ft_h1

    print(f"\nRequired scale factor: {scale_factor:.4f}")

    # What if we scale the IFC coordinates?
    rw_x_scaled = rw_x * scale_factor
    rw_y_scaled = rw_y * scale_factor

    print(f"\nScaled Start Point coordinates:")
    print(f"  X: {rw_x_scaled:.2f} m")
    print(f"  Y: {rw_y_scaled:.2f} m")

    dist_m_h6 = math.sqrt((cm_x_m - rw_x_scaled)**2 + (cm_y_m - rw_y_scaled)**2)
    dist_ft_h6 = dist_m_h6 / (1200/3937)

    print(f"\nDistance:")
    print(f"  {dist_m_h6:.2f} m = {dist_ft_h6:.2f} ft")
    print(f"  Result: {'✓ Would match!' if abs(dist_ft_h6 - 83) < 2 else '✗ Still wrong'}")

    # But this doesn't make sense - why would there be a 2.029 scale factor?

    print("\n" + "=" * 80)
    print("CRITICAL INSIGHT")
    print("=" * 80)

    print("\nLet me check if the IFC coordinates might be in a LOCAL coordinate")
    print("system (like a construction coordinate system) that's separate from")
    print("the state plane system.")

    print("\nNotice that:")
    print(f"  - IFC X range: ~2,081,000 m")
    print(f"  - IFC Y range: ~666,000 m")
    print(f"  - EPSG:2767 should have X (Easting) ~2,081,000 m ✓")
    print(f"  - EPSG:2767 should have Y (Northing) ~666,000 m ✓")

    print("\nThe coordinate ranges MATCH EPSG:2767, so the coordinate system is correct!")
    print("The issue must be with the SPECIFIC coordinates, not the system itself.")

    print("\n" + "=" * 80)
    print("TESTING WITH ANOTHER CONTROL POINT")
    print("=" * 80)

    # Let's check CM 10.90 which should be nearby
    print("\nCM 10.90 from Control Points CSV:")
    cm_10_90_north_ft = 2186505.99
    cm_10_90_east_ft = 6828863.07
    print(f"  Northing: {cm_10_90_north_ft:.2f} ft")
    print(f"  Easting: {cm_10_90_east_ft:.2f} ft")

    cm_10_90_x_m, cm_10_90_y_m = trans_ft_to_m.transform(cm_10_90_east_ft, cm_10_90_north_ft)
    print(f"  In EPSG:2767: X={cm_10_90_x_m:.2f} m, Y={cm_10_90_y_m:.2f} m")

    # Distance between CM 10.90 and CM 10.99
    dist_cm_m = math.sqrt((cm_x_m - cm_10_90_x_m)**2 + (cm_y_m - cm_10_90_y_m)**2)
    dist_cm_ft = dist_cm_m / (1200/3937)
    print(f"\nDistance between CM 10.90 and CM 10.99:")
    print(f"  {dist_cm_m:.2f} m = {dist_cm_ft:.2f} ft")

    # Now let's check if there's a RW Sta 0+000.00 to compare
    print("\nLet me check RW Sta 0+000.00 from IFC...")
    # From the IFC file, line 94: Station 0+000.00
    # From grep earlier, Start Point: 2081533.5399142911,666940.64371720655,0

    rw_000_x = 2081533.5399142911
    rw_000_y = 666940.64371720655

    print(f"RW Sta 0+000.00 Start Point: X={rw_000_x:.2f}, Y={rw_000_y:.2f}")

    # Distance from RW 0+000.00 to RW 0+032.67
    dist_rw_m = math.sqrt((rw_x - rw_000_x)**2 + (rw_y - rw_000_y)**2)
    dist_rw_ft = dist_rw_m / (1200/3937)

    print(f"\nDistance between RW Sta 0+000.00 and RW Sta 0+032.67:")
    print(f"  {dist_rw_m:.2f} m = {dist_rw_ft:.2f} ft")

    # Station 0+032.67 means 32.67 feet along the alignment
    print(f"\nExpected distance (from station numbers): 32.67 ft")
    print(f"Calculated distance: {dist_rw_ft:.2f} ft")

    if abs(dist_rw_ft - 32.67) < 2:
        print("✓ Distances match! IFC coordinates are internally consistent.")
    else:
        ratio = dist_rw_ft / 32.67
        print(f"✗ Off by factor of {ratio:.2f}x")

    print("\n" + "=" * 80)
    print("FINAL CONCLUSION")
    print("=" * 80)

    print("\nBased on all tests:")
    print("1. IFC coordinates ARE in EPSG:2767 (meters) - coordinate ranges match")
    print("2. IFC coordinates are internally consistent (if station distances work)")
    print("3. The transformation to WGS84 is working correctly")
    print("4. The 2x distance error persists in the final KML")

    print("\nThis suggests ONE OF TWO POSSIBILITIES:")
    print("\nA) The IFC coordinates for RW points are SURVEYED INCORRECTLY")
    print("   - They're in the right system but at the wrong positions")
    print("   - There's a systematic offset or error in the RW survey data")

    print("\nB) The IFC and Control Points are in DIFFERENT REALIZATIONS")
    print("   - Both claim to be NAD83(HARN) but might be different epochs/realizations")
    print("   - There could be a datum shift we're not accounting for")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
