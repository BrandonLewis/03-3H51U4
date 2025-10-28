# IFC Site Origin Offset Investigation Report

## Executive Summary

**Question:** Is the IFC site origin offset being applied correctly?

**Answer:** YES, the current implementation is correct. The Start Point coordinates in the IFC file are already in world coordinates (EPSG:2767 meters) and should NOT have any additional offset applied.

**Finding:** The reported 2x discrepancy (41 ft vs 83 ft) **cannot be explained** by the site origin offset. The investigation reveals a much larger actual distance (~1083 ft) that doesn't match either the measured (41 ft) or expected (83 ft) values. This suggests the issue lies elsewhere.

---

## IFC File Structure Analysis

### Key Elements from `4.023_PR_RW Points_S-BD_RW2.ifc`:

1. **Site Origin** (at #25=IFCCARTESIANPOINT):
   ```
   Easting:  2,081,539.56 m
   Northing:   667,013.23 m
   Elevation:      696.52 m
   ```

2. **Element Placement** (at #53=IFCCARTESIANPOINT):
   ```
   Easting:  -2,081,539.56 m  (negative of site origin)
   Northing:   -667,013.23 m  (negative of site origin)
   Elevation:      -696.52 m  (negative of site origin)
   ```

3. **Site Placement Hierarchy**:
   ```
   #26 = IFCAXIS2PLACEMENT3D(#25, ...)  -> Uses site origin
   #27 = IFCLOCALPLACEMENT($, #26)       -> Site placement
   #54 = IFCAXIS2PLACEMENT3D(#53, ...)  -> Uses negative site origin
   #55 = IFCLOCALPLACEMENT(#27, #54)    -> Element placement references site placement
   ```

4. **Example Start Point** (RW Station 0+000.00):
   ```
   Easting:  2,081,533.54 m
   Northing:   666,940.64 m
   Elevation:        0.00 m
   ```

---

## Coordinate Transformation Scenarios Tested

### Scenario A: No Offset (CURRENT IMPLEMENTATION)
**Assumption:** Start Point values are already in world coordinates (EPSG:2767)

**Result:**
- RW Sta 0+029.26 coordinates: E=2,081,541.37 m, N=666,968.34 m
- Distance to CM 10.99: **1,074 ft**
- **This is the correct interpretation**

### Scenario B: Add Site Origin
**Assumption:** Start Point is in local coordinates, add site origin to get world coords

**Result:**
- Coordinates: E=4,163,080.93 m, N=1,333,981.57 m
- Distance to CM 10.99: **7,171,697 ft**
- **INCORRECT** - produces nonsensical coordinates

### Scenario C: Subtract Site Origin
**Assumption:** Start Point needs site origin subtracted

**Result:**
- Coordinates: E=1.81 m, N=-44.89 m
- Distance to CM 10.99: **7,170,622 ft**
- **INCORRECT** - produces coordinates near origin, far from expected location

### Scenario D: Add Element Placement
**Assumption:** Start Point is relative to element placement

**Result:**
- Coordinates: E=1.81 m, N=-44.89 m
- Distance to CM 10.99: **7,170,622 ft**
- **INCORRECT** - same as Scenario C

---

## Verification Against Actual KML Output

### Control Point: CM 10.99
- **Source (CSV in feet):** E=6,829,001.34 ft, N=2,187,051.01 ft
- **Converted to meters:** E=2,081,483.77 m, N=666,614.48 m
- **WGS84 in KML:** Lon=-121.05710442°, Lat=39.16382034°
- **Round-trip conversion:** ✓ Correct

### RW Station 0+000.00
- **Source (IFC in meters):** E=2,081,533.54 m, N=666,940.64 m
- **WGS84 in KML:** Lon=-121.05648936°, Lat=39.16675369°
- **Round-trip conversion:** ✓ Correct

### Measured Distance
- **From CM 10.99 to RW Sta 0+000.00:** 1,083 ft
- **From CM 10.99 to RW Sta 0+029.26:** 1,074 ft

---

## Why the Current Implementation is Correct

### 1. IFC Standard Behavior
The `USE_WORLD_COORDS = True` setting in ifcopenshell tells the geometry processor to handle coordinate transformations automatically. The property values (like Start Point) are **not** affected by this setting - they remain as stored in the file.

### 2. Coordinate Magnitude Analysis
The Start Point coordinates (~2,081,000 E, ~667,000 N) are in the correct range for California State Plane Zone 2 in meters. This confirms they are absolute world coordinates, not local offsets.

### 3. Element Placement Purpose
The element placement (#55) with the negative site origin is used for **geometric representations** (meshes, shapes), NOT for property values. The Start Point is a **property**, not geometry, so it's not affected by the placement hierarchy.

### 4. Consistency Check
If we apply the element placement to the Start Point:
```
Start Point:        (2,081,533.54, 666,940.64, 0)
+ Element Placement:(-2,081,539.56, -667,013.23, -696.52)
= Result:           (-6.02, -72.59, -696.52)
```

This gives coordinates near the local origin, which would then need the site origin added back:
```
Local coords:       (-6.02, -72.59, -696.52)
+ Site Origin:      (2,081,539.56, 667,013.23, 696.52)
= World coords:     (2,081,533.54, 666,940.64, 0)
```

We're back to the original Start Point values, proving they're already in world coordinates.

---

## The 41 ft vs 83 ft Discrepancy

### What We Know
- User reports measuring: **41 ft**
- User expects: **83 ft**
- Ratio: **2.0x difference**
- Our calculation: **1,074-1,083 ft**

### Why Site Origin Offset Is NOT the Cause

1. **None of the transformation scenarios produce 41 ft or 83 ft**
   - No offset: 1,074-1,083 ft
   - With offsets: 7+ million ft or similar

2. **The 2x factor doesn't appear in coordinate transformations**
   - Site origin offset would produce ~3.28x factor (ft/m conversion) if misapplied
   - Or would produce million-foot errors
   - Cannot produce exactly 2x error

3. **The measured distance is too large**
   - CM 10.99 is ~1,083 ft away from the first RW station
   - This is more than 10x larger than either reported value

### Possible Explanations (Outside IFC Offset Issue)

1. **Wrong Reference Points**
   - User may be measuring to/from different points than CM 10.99 and RW Sta 0+032.67
   - There may be other control points or RW points closer together

2. **Measurement Tool Issue**
   - Google Earth measurement tool may be using wrong elevation mode
   - Or measuring something other than horizontal distance

3. **Design vs As-Built**
   - The 83 ft may be from design plans
   - The 41 ft may be from incorrectly georeferenced data

4. **Different Coordinate System**
   - There may be another dataset in a different reference frame
   - The comparison may be mixing coordinate systems

---

## Recommendations

### 1. Verify Reference Points
- Confirm which specific CM point and RW station are being compared
- Check if there are closer points that might give 41-83 ft distances

### 2. Check Other Data Sources
- Review design plans to confirm expected 83 ft value
- Check if there are other RW IFC files with different coordinates

### 3. Google Earth Measurement
- Take screenshots of the measurement in Google Earth
- Verify which points are being selected
- Check measurement tool settings (clamped vs absolute elevation)

### 4. Alternative Distance Calculations
Compute distances between ALL CM points and ALL RW stations to find which pair gives ~41-83 ft

---

## Conclusion

**The IFC site origin offset IS being applied correctly.** The Start Point coordinates are already in world coordinates (EPSG:2767 meters) and should be used directly without any additional transformation. This is the current behavior of `convert_ifc_to_kml.py` and it is correct.

**The reported 41 ft vs 83 ft discrepancy cannot be explained by the site origin offset.** The actual calculated distance is ~1,083 ft, which suggests either:
- Different reference points are being compared
- There's a measurement tool issue
- The problem lies in a different dataset or coordinate system

**Applying any of the offset transformations would make the problem worse, not better.**

---

## Code Reference

Current implementation in `convert_ifc_to_kml.py` (lines 119-125):
```python
points.append({
    'name': name,
    'type': obj.is_a() if hasattr(obj, 'is_a') else 'Unknown',
    'coords': (coords[0], coords[1], coords[2]),  # Already in meters
    'station': station,
    'properties': props
})
```

This is correct - no offset is applied to the Start Point coordinates.
