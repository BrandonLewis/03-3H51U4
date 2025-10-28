#!/usr/bin/env python3
"""
Detailed analysis of the 2x distance error.

The problem: Distance is ~41 ft but should be ~83 ft (exactly 2x).
This suggests a scale factor or projection issue.
"""

from pyproj import Transformer, CRS
import math

def calculate_distance_2d(x1, y1, x2, y2):
    """Calculate 2D Euclidean distance."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def main():
    print("=" * 80)
    print("DETAILED 2X ERROR ANALYSIS")
    print("=" * 80)

    # Control Point CM 10.99
    cm_north_ft = 2187051.01  # EPSG:2871 (feet)
    cm_east_ft = 6829001.34   # EPSG:2871 (feet)

    # RW Sta 0+032.67
    rw_x = 2081471.3317942552  # From IFC file
    rw_y = 666613.68151956971  # From IFC file

    print("\nRAW COORDINATES:")
    print(f"  CM 10.99:         N={cm_north_ft:.2f}, E={cm_east_ft:.2f} (EPSG:2871, feet)")
    print(f"  RW Sta 0+032.67:  X={rw_x:.4f}, Y={rw_y:.4f} (units unknown)")

    # Test 1: Transform IFC from EPSG:2767 (meters) to EPSG:2871 (feet)
    print("\n" + "-" * 80)
    print("TEST 1: Current approach (EPSG:2767 meters -> EPSG:2871 feet)")
    print("-" * 80)

    trans_2767_to_2871 = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
    rw_east_ft, rw_north_ft = trans_2767_to_2871.transform(rw_x, rw_y)

    print(f"  Transformed: N={rw_north_ft:.2f}, E={rw_east_ft:.2f}")

    dist_test1 = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_east_ft, rw_north_ft)
    print(f"  Distance: {dist_test1:.2f} ft")
    print(f"  Result: {'✓ MATCHES ~41 ft problem' if abs(dist_test1 - 41) < 2 else '✗ Does not match'}")

    # Test 2: What if we need to scale by 2?
    print("\n" + "-" * 80)
    print("TEST 2: What if the distance calculation needs a 2x scale factor?")
    print("-" * 80)

    dist_test2 = dist_test1 * 2
    print(f"  Distance × 2: {dist_test2:.2f} ft")
    print(f"  Result: {'✓ MATCHES ~83 ft expected' if abs(dist_test2 - 83) < 2 else '✗ Does not match'}")

    # Test 3: Check CRS definitions
    print("\n" + "-" * 80)
    print("TEST 3: Examine CRS definitions")
    print("-" * 80)

    crs_2767 = CRS.from_epsg(2767)
    crs_2871 = CRS.from_epsg(2871)

    print(f"\nEPSG:2767:")
    print(f"  Name: {crs_2767.name}")
    print(f"  Units: {crs_2767.axis_info[0].unit_name}")
    print(f"  Axis 1: {crs_2767.axis_info[0].name} ({crs_2767.axis_info[0].direction})")
    print(f"  Axis 2: {crs_2767.axis_info[1].name} ({crs_2767.axis_info[1].direction})")

    print(f"\nEPSG:2871:")
    print(f"  Name: {crs_2871.name}")
    print(f"  Units: {crs_2871.axis_info[0].unit_name}")
    print(f"  Axis 1: {crs_2871.axis_info[0].name} ({crs_2871.axis_info[0].direction})")
    print(f"  Axis 2: {crs_2871.axis_info[1].name} ({crs_2871.axis_info[1].direction})")

    # Test 4: Manual conversion check
    print("\n" + "-" * 80)
    print("TEST 4: Manual unit conversion verification")
    print("-" * 80)

    us_survey_ft_to_m = 1200/3937  # Exact definition
    m_to_us_survey_ft = 3937/1200

    print(f"  1 US Survey Foot = {us_survey_ft_to_m:.10f} meters")
    print(f"  1 meter = {m_to_us_survey_ft:.10f} US Survey Feet")

    # If RW coords are in meters, convert to feet manually
    rw_x_manual_ft = rw_x * m_to_us_survey_ft
    rw_y_manual_ft = rw_y * m_to_us_survey_ft

    print(f"\n  IFC coords if they were meters converted to feet:")
    print(f"    X: {rw_x_manual_ft:.2f} ft")
    print(f"    Y: {rw_y_manual_ft:.2f} ft")

    # Test 5: Check if there's a projection parameter issue
    print("\n" + "-" * 80)
    print("TEST 5: Compare different transformation methods")
    print("-" * 80)

    # Method A: Direct EPSG:2767 -> EPSG:2871
    trans_a = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
    rw_e_a, rw_n_a = trans_a.transform(rw_x, rw_y)
    dist_a = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_e_a, rw_n_a)

    print(f"\n  Method A: Direct 2767->2871")
    print(f"    Result: N={rw_n_a:.2f}, E={rw_e_a:.2f}")
    print(f"    Distance: {dist_a:.2f} ft")

    # Method B: Via WGS84 (2767 -> 4326 -> 2871)
    trans_b1 = Transformer.from_crs('EPSG:2767', 'EPSG:4326', always_xy=True)
    trans_b2 = Transformer.from_crs('EPSG:4326', 'EPSG:2871', always_xy=True)
    lon, lat = trans_b1.transform(rw_x, rw_y)
    rw_e_b, rw_n_b = trans_b2.transform(lon, lat)
    dist_b = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_e_b, rw_n_b)

    print(f"\n  Method B: Via WGS84 (2767->4326->2871)")
    print(f"    WGS84: lon={lon:.8f}, lat={lat:.8f}")
    print(f"    Result: N={rw_n_b:.2f}, E={rw_e_b:.2f}")
    print(f"    Distance: {dist_b:.2f} ft")

    print(f"\n  Difference between methods: {abs(dist_a - dist_b):.6f} ft")

    # Test 6: Check if coordinates need to be swapped
    print("\n" + "-" * 80)
    print("TEST 6: What if X/Y are swapped in IFC file?")
    print("-" * 80)

    # Try swapping X and Y
    trans_swap = Transformer.from_crs('EPSG:2767', 'EPSG:2871', always_xy=True)
    rw_e_swap, rw_n_swap = trans_swap.transform(rw_y, rw_x)  # Swapped!
    dist_swap = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_e_swap, rw_n_swap)

    print(f"  With X/Y swapped:")
    print(f"    Input: X={rw_y:.2f}, Y={rw_x:.2f}")
    print(f"    Result: N={rw_n_swap:.2f}, E={rw_e_swap:.2f}")
    print(f"    Distance: {dist_swap:.2f} ft")
    print(f"    Result: {'✓ Could be relevant' if abs(dist_swap - 83) < 20 else '✗ Still does not match'}")

    # Test 7: What if the scale factor is in the projection definition?
    print("\n" + "-" * 80)
    print("TEST 7: Check projection scale factors")
    print("-" * 80)

    # Get projection strings
    print(f"\nEPSG:2767 WKT:")
    wkt_2767 = crs_2767.to_wkt(pretty=True)
    # Look for scale factor
    for line in wkt_2767.split('\n'):
        if 'scale' in line.lower() or 'factor' in line.lower():
            print(f"  {line.strip()}")

    print(f"\nEPSG:2871 WKT:")
    wkt_2871 = crs_2871.to_wkt(pretty=True)
    for line in wkt_2871.split('\n'):
        if 'scale' in line.lower() or 'factor' in line.lower():
            print(f"  {line.strip()}")

    # Test 8: Compute what the IFC coordinates SHOULD be for 83 ft
    print("\n" + "-" * 80)
    print("TEST 8: Back-calculate what IFC coords should be for 83 ft distance")
    print("-" * 80)

    # If we want distance of 83 ft and current approach gives 41 ft,
    # we need to move the RW point further away
    # Current: N=2187048.39, E=6828960.53
    # Target: CM 10.99 at N=2187051.01, E=6829001.34

    # Vector from CM to RW (current)
    delta_n = rw_north_ft - cm_north_ft
    delta_e = rw_east_ft - cm_east_ft

    # Magnitude (current distance)
    mag_current = math.sqrt(delta_n**2 + delta_e**2)

    # For 83 ft, we need 2x the distance
    scale_needed = 83.0 / dist_test1

    # New deltas
    delta_n_new = delta_n * scale_needed
    delta_e_new = delta_e * scale_needed

    # New RW position (in EPSG:2871)
    rw_north_target = cm_north_ft + delta_n_new
    rw_east_target = cm_east_ft + delta_e_new

    print(f"  Current RW position (EPSG:2871): N={rw_north_ft:.2f}, E={rw_east_ft:.2f}")
    print(f"  Current distance: {dist_test1:.2f} ft")
    print(f"  Target distance: 83.00 ft")
    print(f"  Scale factor needed: {scale_needed:.4f}x")
    print(f"  Target RW position (EPSG:2871): N={rw_north_target:.2f}, E={rw_east_target:.2f}")

    # Now transform this target position back to EPSG:2767
    trans_back = Transformer.from_crs('EPSG:2871', 'EPSG:2767', always_xy=True)
    rw_x_target, rw_y_target = trans_back.transform(rw_east_target, rw_north_target)

    print(f"\n  Target coords in EPSG:2767 (if that's the source): X={rw_x_target:.4f}, Y={rw_y_target:.4f}")
    print(f"  Actual IFC coords:                                 X={rw_x:.4f}, Y={rw_y:.4f}")
    print(f"  Difference: ΔX={abs(rw_x_target - rw_x):.4f}, ΔY={abs(rw_y_target - rw_y):.4f}")

    # Test 9: Check if it's a simple scaling issue in the coordinates
    print("\n" + "-" * 80)
    print("TEST 9: What if IFC coordinates have a 2x scale applied?")
    print("-" * 80)

    # Try scaling IFC coords by 2
    rw_x_scaled = rw_x * 2
    rw_y_scaled = rw_y * 2

    rw_e_scaled, rw_n_scaled = trans_2767_to_2871.transform(rw_x_scaled, rw_y_scaled)
    dist_scaled = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_e_scaled, rw_n_scaled)

    print(f"  IFC coords × 2:")
    print(f"    Input: X={rw_x_scaled:.2f}, Y={rw_y_scaled:.2f}")
    print(f"    Transformed: N={rw_n_scaled:.2f}, E={rw_e_scaled:.2f}")
    print(f"    Distance: {dist_scaled:.2f} ft")

    # Try scaling by 0.5
    rw_x_half = rw_x * 0.5
    rw_y_half = rw_y * 0.5

    rw_e_half, rw_n_half = trans_2767_to_2871.transform(rw_x_half, rw_y_half)
    dist_half = calculate_distance_2d(cm_east_ft, cm_north_ft, rw_e_half, rw_n_half)

    print(f"\n  IFC coords × 0.5:")
    print(f"    Input: X={rw_x_half:.2f}, Y={rw_y_half:.2f}")
    print(f"    Transformed: N={rw_n_half:.2f}, E={rw_e_half:.2f}")
    print(f"    Distance: {dist_half:.2f} ft")

    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)

    print("\n1. The current transformation gives ~41 ft, which is exactly half of ~83 ft")
    print("\n2. This 2x error is NOT explained by:")
    print("   - Simple unit conversion (m to ft factor is 3.28, not 2.0)")
    print("   - X/Y coordinate swap")
    print("   - Different transformation paths")

    print("\n3. Possible causes:")
    print("   a) IFC coordinates might have a scale factor of 0.5 applied")
    print("   b) The distance calculation itself might need adjustment")
    print("   c) The coordinate reference system interpretation might be wrong")
    print("   d) There might be an origin/datum difference we're missing")

    print("\n4. Next steps:")
    print("   - Check if IFC file has a global scale factor applied")
    print("   - Verify the actual surveyed distance between these points")
    print("   - Check if there are other pairs of points to test with")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
