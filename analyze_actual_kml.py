#!/usr/bin/env python3
"""
Analyze the actual coordinates from the KML files to understand the discrepancy.
"""

from pyproj import Transformer
import math

# WGS84 coordinates from the actual KML files
CM_10_99_WGS84 = {
    'lon': -121.05710441630382,
    'lat': 39.16382034053008
}

RW_STA_0_WGS84 = {
    'lon': -121.0564893644726,
    'lat': 39.16675368710917
}

# State Plane coordinates from the source data
CM_10_99_STATE_PLANE_FEET = {
    'easting': 6829001.340,
    'northing': 2187051.010,
    'elevation': 2235.970
}

RW_STA_0_STATE_PLANE_METERS = {
    'easting': 2081533.54,
    'northing': 666940.64,
    'elevation': 0.0
}

print("=" * 80)
print("ANALYZING ACTUAL KML COORDINATES")
print("=" * 80)
print()

# Convert WGS84 back to State Plane to see what's happening
transformer_wgs84_to_2226 = Transformer.from_crs('EPSG:4326', 'EPSG:2226', always_xy=True)
transformer_wgs84_to_2767 = Transformer.from_crs('EPSG:4326', 'EPSG:2767', always_xy=True)

# Convert CM 10.99 from WGS84 back to State Plane
cm_2226 = transformer_wgs84_to_2226.transform(CM_10_99_WGS84['lon'], CM_10_99_WGS84['lat'])
cm_2767 = transformer_wgs84_to_2767.transform(CM_10_99_WGS84['lon'], CM_10_99_WGS84['lat'])

print("CM 10.99 COORDINATES")
print("-" * 80)
print(f"Source (from CSV in feet):        E={CM_10_99_STATE_PLANE_FEET['easting']:12.2f}, N={CM_10_99_STATE_PLANE_FEET['northing']:12.2f}")
print(f"WGS84 (from KML):                 Lon={CM_10_99_WGS84['lon']:.8f}, Lat={CM_10_99_WGS84['lat']:.8f}")
print(f"Back to EPSG:2226 (ft):           E={cm_2226[0]:12.2f}, N={cm_2226[1]:12.2f}")
print(f"Back to EPSG:2767 (m):            E={cm_2767[0]:12.2f}, N={cm_2767[1]:12.2f}")
print()

# Convert RW Sta 0 from WGS84 back to State Plane
rw_2226 = transformer_wgs84_to_2226.transform(RW_STA_0_WGS84['lon'], RW_STA_0_WGS84['lat'])
rw_2767 = transformer_wgs84_to_2767.transform(RW_STA_0_WGS84['lon'], RW_STA_0_WGS84['lat'])

print("RW Sta 0+000.00 COORDINATES")
print("-" * 80)
print(f"Source (from IFC in meters):      E={RW_STA_0_STATE_PLANE_METERS['easting']:12.2f}, N={RW_STA_0_STATE_PLANE_METERS['northing']:12.2f}")
print(f"WGS84 (from KML):                 Lon={RW_STA_0_WGS84['lon']:.8f}, Lat={RW_STA_0_WGS84['lat']:.8f}")
print(f"Back to EPSG:2226 (ft):           E={rw_2226[0]:12.2f}, N={rw_2226[1]:12.2f}")
print(f"Back to EPSG:2767 (m):            E={rw_2767[0]:12.2f}, N={rw_2767[1]:12.2f}")
print()

# Now calculate distances in State Plane (meters)
us_ft_to_m = 0.3048006096012192

# CM in meters
cm_meters = (cm_2767[0], cm_2767[1])

# RW in meters
rw_meters = (rw_2767[0], rw_2767[1])

dx = rw_meters[0] - cm_meters[0]
dy = rw_meters[1] - cm_meters[1]
dist_m = math.sqrt(dx**2 + dy**2)
dist_ft = dist_m / us_ft_to_m

print("DISTANCE CALCULATION (using WGS84 -> EPSG:2767 conversion)")
print("-" * 80)
print(f"CM 10.99:        E={cm_meters[0]:12.2f} m, N={cm_meters[1]:12.2f} m")
print(f"RW Sta 0+000.00: E={rw_meters[0]:12.2f} m, N={rw_meters[1]:12.2f} m")
print(f"ΔE: {dx:10.2f} m")
print(f"ΔN: {dy:10.2f} m")
print(f"Distance: {dist_m:.2f} m = {dist_ft:.2f} ft")
print()

# Now let's check - what if we compare the original coordinates directly?
print("=" * 80)
print("PROBLEM DIAGNOSIS")
print("=" * 80)
print()

# Convert CM from feet to meters
cm_orig_to_meters = {
    'easting': CM_10_99_STATE_PLANE_FEET['easting'] * us_ft_to_m,
    'northing': CM_10_99_STATE_PLANE_FEET['northing'] * us_ft_to_m
}

dx_orig = RW_STA_0_STATE_PLANE_METERS['easting'] - cm_orig_to_meters['easting']
dy_orig = RW_STA_0_STATE_PLANE_METERS['northing'] - cm_orig_to_meters['northing']
dist_orig_m = math.sqrt(dx_orig**2 + dy_orig**2)
dist_orig_ft = dist_orig_m / us_ft_to_m

print("Direct comparison of source coordinates (CM converted ft->m):")
print(f"CM 10.99:        E={cm_orig_to_meters['easting']:12.2f} m, N={cm_orig_to_meters['northing']:12.2f} m")
print(f"RW Sta 0+000.00: E={RW_STA_0_STATE_PLANE_METERS['easting']:12.2f} m, N={RW_STA_0_STATE_PLANE_METERS['northing']:12.2f} m")
print(f"Distance: {dist_orig_m:.2f} m = {dist_orig_ft:.2f} ft")
print()

# Key insight: Check if control points were converted with wrong CRS
print("HYPOTHESIS: Control Points KML used wrong source CRS")
print("-" * 80)
print()

# What if the Control Points KML was created assuming the feet coordinates
# were already in meters (EPSG:2767)?
transformer_2767_to_4326 = Transformer.from_crs('EPSG:2767', 'EPSG:4326', always_xy=True)

# Treat the feet values as if they were meters
cm_wrong_wgs84 = transformer_2767_to_4326.transform(
    CM_10_99_STATE_PLANE_FEET['easting'],
    CM_10_99_STATE_PLANE_FEET['northing']
)

print("If Control Points CSV (in feet) was incorrectly treated as meters:")
print(f"  Input:  E={CM_10_99_STATE_PLANE_FEET['easting']:.2f} ft, N={CM_10_99_STATE_PLANE_FEET['northing']:.2f} ft")
print(f"  Treated as: E={CM_10_99_STATE_PLANE_FEET['easting']:.2f} m, N={CM_10_99_STATE_PLANE_FEET['northing']:.2f} m")
print(f"  Result WGS84: Lon={cm_wrong_wgs84[0]:.8f}, Lat={cm_wrong_wgs84[1]:.8f}")
print(f"  Actual WGS84: Lon={CM_10_99_WGS84['lon']:.8f}, Lat={CM_10_99_WGS84['lat']:.8f}")
print()

if abs(cm_wrong_wgs84[0] - CM_10_99_WGS84['lon']) < 0.0001:
    print("MATCH! The Control Points KML incorrectly treated feet as meters!")
    print()
    print("This means:")
    print("  1. The Control Points are being placed at the wrong location")
    print("  2. The scaling factor is ~3.28 (ft/m), causing the ~2-3x error")
    print("  3. We need to fix the Control Points KML creation process")
else:
    print("No match - different issue")
print()

# Calculate the actual distance if both were correctly converted
print("=" * 80)
print("CORRECT DISTANCE CALCULATION")
print("=" * 80)
print()

# Correct coordinates for both
transformer_2226_to_2767 = Transformer.from_crs('EPSG:2226', 'EPSG:2767', always_xy=True)

cm_correct = transformer_2226_to_2767.transform(
    CM_10_99_STATE_PLANE_FEET['easting'],
    CM_10_99_STATE_PLANE_FEET['northing']
)

print("Correctly converted coordinates:")
print(f"CM 10.99 (from EPSG:2226 ft):     E={cm_correct[0]:12.2f} m, N={cm_correct[1]:12.2f} m")
print(f"RW Sta 0+000.00 (from IFC):       E={RW_STA_0_STATE_PLANE_METERS['easting']:12.2f} m, N={RW_STA_0_STATE_PLANE_METERS['northing']:12.2f} m")

dx_correct = RW_STA_0_STATE_PLANE_METERS['easting'] - cm_correct[0]
dy_correct = RW_STA_0_STATE_PLANE_METERS['northing'] - cm_correct[1]
dist_correct_m = math.sqrt(dx_correct**2 + dy_correct**2)
dist_correct_ft = dist_correct_m / us_ft_to_m

print(f"Distance: {dist_correct_m:.2f} m = {dist_correct_ft:.2f} ft")
print()
