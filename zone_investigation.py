#!/usr/bin/env python3
"""
Investigate which coordinate zone the IFC coordinates are actually in.

Control Points: E~6,829,000 N~2,187,000 (EPSG:2871, CA Zone 2)
IFC Points:     X~2,081,000 Y~666,000    (Unknown zone/system)

These are clearly in DIFFERENT zones!
"""

from pyproj import Transformer, CRS
import math

def test_transformation(source_epsg, rw_x, rw_y, cm_east_ft, cm_north_ft):
    """Test if a given source EPSG produces the correct distance."""
    try:
        # Transform IFC point from source to EPSG:2871
        trans = Transformer.from_crs(f'EPSG:{source_epsg}', 'EPSG:2871', always_xy=True)
        rw_e, rw_n = trans.transform(rw_x, rw_y)

        # Calculate distance
        dist = math.sqrt((cm_east_ft - rw_e)**2 + (cm_north_ft - rw_n)**2)

        return rw_e, rw_n, dist
    except Exception as e:
        return None, None, None

def main():
    print("=" * 80)
    print("COORDINATE ZONE INVESTIGATION")
    print("=" * 80)

    # Control Point
    cm_north_ft = 2187051.01
    cm_east_ft = 6829001.34

    # IFC Point
    rw_x = 2081471.3317942552
    rw_y = 666613.68151956971

    print("\nCoordinate Ranges:")
    print(f"  Control Points (EPSG:2871, CA Zone 2):")
    print(f"    Easting:  ~6,829,000 ft")
    print(f"    Northing: ~2,187,000 ft")

    print(f"\n  IFC Points (Unknown system):")
    print(f"    X: ~2,081,000")
    print(f"    Y: ~666,000")

    print("\n  ❗ These ranges are COMPLETELY DIFFERENT!")
    print("     They cannot be in the same coordinate zone.")

    print("\n" + "=" * 80)
    print("TESTING CALIFORNIA STATE PLANE ZONES")
    print("=" * 80)

    # California State Plane zones
    ca_zones = {
        'EPSG:2225': 'NAD83 / California zone 1 (ftUS)',
        'EPSG:2226': 'NAD83 / California zone 2 (ftUS)',
        'EPSG:2227': 'NAD83 / California zone 3 (ftUS)',
        'EPSG:2228': 'NAD83 / California zone 4 (ftUS)',
        'EPSG:2229': 'NAD83 / California zone 5 (ftUS)',
        'EPSG:2230': 'NAD83 / California zone 6 (ftUS)',
        'EPSG:2766': 'NAD83(HARN) / California zone 1',
        'EPSG:2767': 'NAD83(HARN) / California zone 2',
        'EPSG:2768': 'NAD83(HARN) / California zone 3',
        'EPSG:2769': 'NAD83(HARN) / California zone 4',
        'EPSG:2770': 'NAD83(HARN) / California zone 5',
        'EPSG:2771': 'NAD83(HARN) / California zone 6',
        'EPSG:2870': 'NAD83(HARN) / California zone 1 (ftUS)',
        'EPSG:2871': 'NAD83(HARN) / California zone 2 (ftUS)',
        'EPSG:2872': 'NAD83(HARN) / California zone 3 (ftUS)',
        'EPSG:2873': 'NAD83(HARN) / California zone 4 (ftUS)',
        'EPSG:2874': 'NAD83(HARN) / California zone 5 (ftUS)',
        'EPSG:2875': 'NAD83(HARN) / California zone 6 (ftUS)',
    }

    results = []

    print("\nTesting each zone...")
    for epsg_code, name in ca_zones.items():
        rw_e, rw_n, dist = test_transformation(epsg_code, rw_x, rw_y, cm_east_ft, cm_north_ft)

        if rw_e is not None:
            results.append({
                'epsg': epsg_code,
                'name': name,
                'rw_e': rw_e,
                'rw_n': rw_n,
                'distance': dist
            })

            # Check if this gives us the expected distance
            if dist and 80 < dist < 86:
                print(f"  ✓ {epsg_code}: {name}")
                print(f"      Distance: {dist:.2f} ft ✓✓✓ MATCHES!")

    print("\n" + "=" * 80)
    print("RESULTS SORTED BY DISTANCE")
    print("=" * 80)

    # Sort by distance, closest to 83 ft first
    results.sort(key=lambda x: abs(x['distance'] - 83))

    print("\nTop 10 closest to 83 ft:")
    for i, result in enumerate(results[:10]):
        print(f"\n{i+1}. {result['epsg']}: {result['name']}")
        print(f"   Transformed to: E={result['rw_e']:.2f}, N={result['rw_n']:.2f}")
        print(f"   Distance: {result['distance']:.2f} ft")
        print(f"   Error: {abs(result['distance'] - 83):.2f} ft")

        if abs(result['distance'] - 83) < 5:
            print(f"   ✓✓✓ EXCELLENT MATCH!")

    print("\n" + "=" * 80)
    print("TESTING NEARBY COORDINATE SYSTEMS")
    print("=" * 80)

    # Maybe it's UTM?
    utm_zones = [
        ('EPSG:26910', 'NAD83 / UTM zone 10N'),
        ('EPSG:26911', 'NAD83 / UTM zone 11N'),
        ('EPSG:3310', 'NAD83 / California Albers'),
    ]

    print("\nTesting UTM and other systems...")
    for epsg_code, name in utm_zones:
        rw_e, rw_n, dist = test_transformation(epsg_code, rw_x, rw_y, cm_east_ft, cm_north_ft)

        if rw_e is not None and dist:
            print(f"\n{epsg_code}: {name}")
            print(f"  Distance: {dist:.2f} ft")
            if 80 < dist < 86:
                print(f"  ✓✓✓ MATCHES!")

    print("\n" + "=" * 80)
    print("COORDINATE RANGE CHECK")
    print("=" * 80)

    # Check which coordinate systems have ranges matching the IFC values
    print("\nWhich CRS has X~2,081,000 and Y~666,000?")

    # Test a point in each zone to see typical ranges
    test_lon = -121.057  # Near the project area
    test_lat = 39.164

    trans_wgs = {}
    for epsg_code, name in ca_zones.items():
        try:
            trans = Transformer.from_crs('EPSG:4326', f'EPSG:{epsg_code}', always_xy=True)
            x, y = trans.transform(test_lon, test_lat)
            trans_wgs[epsg_code] = (x, y, name)
        except:
            pass

    print(f"\nFor reference point (lon={test_lon}, lat={test_lat}):")
    for epsg_code, (x, y, name) in sorted(trans_wgs.items()):
        x_order = len(str(int(abs(x))))
        y_order = len(str(int(abs(y))))

        match_x = abs(int(x/1000)) == abs(int(rw_x/1000))
        match_y = abs(int(y/1000)) == abs(int(rw_y/1000))

        indicator = ""
        if match_x and match_y:
            indicator = " ✓✓✓ RANGE MATCHES IFC!"
        elif match_x or match_y:
            indicator = " ✓ Partial match"

        print(f"  {epsg_code}: X={x:12.2f}, Y={y:12.2f}{indicator}")

    print("\n" + "=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)

    # Find the best match
    if results and results[0]['distance'] and abs(results[0]['distance'] - 83) < 5:
        best = results[0]
        print(f"\n✓✓✓ SOLUTION FOUND!")
        print(f"\nThe IFC coordinates are in: {best['epsg']} ({best['name']})")
        print(f"NOT in EPSG:2767 as currently assumed!")

        print(f"\nWith this correction:")
        print(f"  Distance: {best['distance']:.2f} ft (expected ~83 ft)")
        print(f"  Error: only {abs(best['distance'] - 83):.2f} ft")

        print("\n" + "-" * 80)
        print("TO FIX THE CODE:")
        print("-" * 80)
        print(f"\nIn convert_ifc_to_kml.py, change:")
        print(f"  FROM: source_epsg='EPSG:2767'")
        print(f"  TO:   source_epsg='{best['epsg']}'")
    else:
        print("\n❌ No California State Plane zone produces the expected 83 ft distance.")
        print("\nThis suggests:")
        print("  1. The IFC coordinates are in a custom/local coordinate system")
        print("  2. There's an error in the surveyed coordinates")
        print("  3. The expected distance of 83 ft might be incorrect")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
