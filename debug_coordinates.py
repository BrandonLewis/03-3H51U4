#!/usr/bin/env python3
"""
Debug coordinate systems - check if we're comparing apples to apples.
"""

import math

# From Control Points.csv - CM 10.99
# These are in California State Plane Zone 2, but in what units?
CM_10_99_RAW = {
    'northing': 2187051.01,
    'easting': 6829001.34,
    'elevation': 2235.97
}

# From IFC - RW Station 0+000.00 Start Point
RW_STA_0_RAW = {
    'easting': 2081533.5399142911,
    'northing': 666940.64371720655,
    'elevation': 0
}

# From IFC - Site Origin at #25
SITE_ORIGIN = {
    'easting': 2081539.5615699999,
    'northing': 667013.22788000002,
    'elevation': 696.52140385999996
}

print("=" * 80)
print("COORDINATE SYSTEM DEBUG")
print("=" * 80)
print()

print("HYPOTHESIS 1: Control Points are in FEET (EPSG:2226)")
print("-" * 80)
print("If control points are in US Survey Feet and IFC is in meters:")
print()

# Convert control points from feet to meters
us_ft_to_m = 0.3048006096012192
cm_10_99_meters = {
    'northing': CM_10_99_RAW['northing'] * us_ft_to_m,
    'easting': CM_10_99_RAW['easting'] * us_ft_to_m,
    'elevation': CM_10_99_RAW['elevation'] * us_ft_to_m
}

print(f"CM 10.99 (original):")
print(f"  Northing: {CM_10_99_RAW['northing']:12.2f} ft")
print(f"  Easting:  {CM_10_99_RAW['easting']:12.2f} ft")
print()

print(f"CM 10.99 (converted to meters):")
print(f"  Northing: {cm_10_99_meters['northing']:12.2f} m")
print(f"  Easting:  {cm_10_99_meters['easting']:12.2f} m")
print()

print(f"RW Sta 0+000.00 (from IFC):")
print(f"  Northing: {RW_STA_0_RAW['northing']:12.2f} m")
print(f"  Easting:  {RW_STA_0_RAW['easting']:12.2f} m")
print()

dx1 = cm_10_99_meters['easting'] - RW_STA_0_RAW['easting']
dy1 = cm_10_99_meters['northing'] - RW_STA_0_RAW['northing']
dist1 = math.sqrt(dx1**2 + dy1**2)

print(f"Distance: {dist1:.2f} m = {dist1 / us_ft_to_m:.2f} ft")
print()

print()
print("HYPOTHESIS 2: Control Points are in METERS (EPSG:2767)")
print("-" * 80)
print("If BOTH control points and IFC are in meters:")
print()

print(f"CM 10.99 (as meters):")
print(f"  Northing: {CM_10_99_RAW['northing']:12.2f} m")
print(f"  Easting:  {CM_10_99_RAW['easting']:12.2f} m")
print()

print(f"RW Sta 0+000.00 (from IFC):")
print(f"  Northing: {RW_STA_0_RAW['northing']:12.2f} m")
print(f"  Easting:  {RW_STA_0_RAW['easting']:12.2f} m")
print()

dx2 = CM_10_99_RAW['easting'] - RW_STA_0_RAW['easting']
dy2 = CM_10_99_RAW['northing'] - RW_STA_0_RAW['northing']
dist2 = math.sqrt(dx2**2 + dy2**2)

print(f"Distance: {dist2:.2f} m = {dist2 / us_ft_to_m:.2f} ft")
print()

print()
print("HYPOTHESIS 3: Coordinates are SWAPPED (Northing/Easting confusion)")
print("-" * 80)
print("What if the IFC coordinates have Northing/Easting swapped?")
print()

# Swap IFC coordinates
RW_STA_0_SWAPPED = {
    'northing': RW_STA_0_RAW['easting'],  # Use easting as northing
    'easting': RW_STA_0_RAW['northing'],   # Use northing as easting
    'elevation': RW_STA_0_RAW['elevation']
}

print(f"CM 10.99 (in meters):")
print(f"  Northing: {cm_10_99_meters['northing']:12.2f} m")
print(f"  Easting:  {cm_10_99_meters['easting']:12.2f} m")
print()

print(f"RW Sta 0+000.00 (SWAPPED):")
print(f"  Northing: {RW_STA_0_SWAPPED['northing']:12.2f} m (was easting)")
print(f"  Easting:  {RW_STA_0_SWAPPED['easting']:12.2f} m (was northing)")
print()

dx3 = cm_10_99_meters['easting'] - RW_STA_0_SWAPPED['easting']
dy3 = cm_10_99_meters['northing'] - RW_STA_0_SWAPPED['northing']
dist3 = math.sqrt(dx3**2 + dy3**2)

print(f"Distance: {dist3:.2f} m = {dist3 / us_ft_to_m:.2f} ft")
print()

print()
print("HYPOTHESIS 4: IFC coordinates are in FEET, not meters")
print("-" * 80)
print("What if the IFC Start Point is actually in feet, not meters?")
print()

# Convert IFC from feet to meters
rw_sta_0_if_feet = {
    'northing': RW_STA_0_RAW['northing'] * us_ft_to_m,
    'easting': RW_STA_0_RAW['easting'] * us_ft_to_m,
    'elevation': RW_STA_0_RAW['elevation']
}

print(f"CM 10.99 (in meters):")
print(f"  Northing: {cm_10_99_meters['northing']:12.2f} m")
print(f"  Easting:  {cm_10_99_meters['easting']:12.2f} m")
print()

print(f"RW Sta 0+000.00 (IFC coords * 0.3048, assuming they were feet):")
print(f"  Northing: {rw_sta_0_if_feet['northing']:12.2f} m")
print(f"  Easting:  {rw_sta_0_if_feet['easting']:12.2f} m")
print()

dx4 = cm_10_99_meters['easting'] - rw_sta_0_if_feet['easting']
dy4 = cm_10_99_meters['northing'] - rw_sta_0_if_feet['northing']
dist4 = math.sqrt(dx4**2 + dy4**2)

print(f"Distance: {dist4:.2f} m = {dist4 / us_ft_to_m:.2f} ft")
print()

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print(f"Hypothesis 1 (CP in ft, IFC in m):              {dist1 / us_ft_to_m:10.2f} ft")
print(f"Hypothesis 2 (both in m):                       {dist2 / us_ft_to_m:10.2f} ft")
print(f"Hypothesis 3 (IFC coords swapped):              {dist3 / us_ft_to_m:10.2f} ft")
print(f"Hypothesis 4 (IFC in ft, should be m):          {dist4 / us_ft_to_m:10.2f} ft")
print()
print(f"User reports measuring: ~41 ft")
print(f"User expects: ~83 ft")
print()

# Check which is closest to either value
hypotheses = [
    ("H1 (CP in ft, IFC in m)", dist1 / us_ft_to_m),
    ("H2 (both in m)", dist2 / us_ft_to_m),
    ("H3 (IFC swapped)", dist3 / us_ft_to_m),
    ("H4 (IFC in ft)", dist4 / us_ft_to_m)
]

print("Closest to 41 ft:")
closest_41 = min(hypotheses, key=lambda x: abs(x[1] - 41))
print(f"  {closest_41[0]}: {closest_41[1]:.2f} ft (Δ = {abs(closest_41[1] - 41):.2f} ft)")
print()

print("Closest to 83 ft:")
closest_83 = min(hypotheses, key=lambda x: abs(x[1] - 83))
print(f"  {closest_83[0]}: {closest_83[1]:.2f} ft (Δ = {abs(closest_83[1] - 83):.2f} ft)")
print()
