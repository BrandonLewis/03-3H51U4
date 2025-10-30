# DXF to KML Converter - Command Line Usage

## Overview
The `convert_dxf_to_kml.py` script now supports comprehensive command-line arguments for controlling station calculations, elevation handling, and output formatting.

## Basic Usage

### Convert a Single File
```bash
python convert_dxf_to_kml.py input.dxf
```
Output: `input.kml` (same directory as input)

### Convert with Custom Output Name
```bash
python convert_dxf_to_kml.py input.dxf -o custom_output.kml
```

### Convert Multiple Files
```bash
python convert_dxf_to_kml.py DATA/*.dxf
```

### Process All DXF Files in DATA Directory
```bash
python convert_dxf_to_kml.py
```

## Station Options

### Include Station Values in Point Names
```bash
python convert_dxf_to_kml.py input.dxf --start-station 30000 --include-stations
```
- Stations are calculated based on **actual measured distances** along the alignment
- Start station is required when using `--include-stations`
- Stations are displayed in standard civil engineering format (e.g., "300+00.00")

### With Station Validation
```bash
python convert_dxf_to_kml.py input.dxf \
    --start-station 30000 \
    --end-station 30488 \
    --include-stations
```
- The script validates that the measured distance matches the station range
- **Warning issued** if difference exceeds 1 foot
- Helps identify data quality issues

Example output when stations match:
```
  Total distance: 488.00 feet
  Station range: 300+00.00 to 304+88.00
  Expected distance: 488.00 feet
```

Example output when stations don't match:
```
  Total distance: 488.00 feet
  Station range: 300+00.00 to 308+72.00
  Expected distance: 872.00 feet
  WARNING: Measured distance (488.00 ft) differs from station range (872.00 ft) by 384.00 ft
           This may indicate incorrect station values or non-linear alignment
```

## Elevation Options

### Render Polylines at Elevation
```bash
python convert_dxf_to_kml.py input.dxf --polyline-elevation
```
- Polylines will be rendered at their actual elevations (absolute altitude mode)
- Elevations are properly transformed from EPSG:2871 (US Survey Feet) to WGS84 (meters)
- Without this flag, polylines are clamped to ground (default)

## Combined Example

Full example with all options:
```bash
python convert_dxf_to_kml.py \
    "DATA/4.023_PR_RW Points_S-BD_RW2.dxf" \
    -o "output/retaining_wall_stations.kml" \
    --start-station 30000 \
    --end-station 30488 \
    --include-stations \
    --polyline-elevation
```

## Command-Line Options Reference

| Option | Type | Description |
|--------|------|-------------|
| `input_files` | Positional | DXF file(s) to convert. If omitted, processes all .dxf files in DATA directory |
| `-o`, `--output` | String | Output KML file path (only valid for single file conversion) |
| `--start-station` | Float | Starting station in feet (e.g., 30000 for station 300+00.00) |
| `--end-station` | Float | Ending station in feet (used for validation) |
| `--include-stations` | Flag | Include station values in point names (requires `--start-station`) |
| `--polyline-elevation` | Flag | Render polylines at elevation instead of clamping to ground |

## How Stations Work

### Station Calculation Formula
```
station = start_station + cumulative_distance_from_first_point
```

The script:
1. Calculates cumulative 2D horizontal distances between sequential points
2. Adds cumulative distance to the start station
3. Formats as standard civil engineering stations (e.g., "300+48.77")

### Why This is Correct
- Stations represent actual measured distances along the alignment
- No interpolation or scaling is performed
- Stations directly correspond to physical distances on the ground

### Station Format
- Input: Feet (e.g., 30000)
- Display: Civil engineering format (e.g., "300+00.00")
- Formula: `hundreds + "+" + feet`
  - Example: 30048.77 → "300+48.77"

## Elevation Information

### 3D Coordinate Transformation
All coordinates (X, Y, Z) are now properly transformed:
- **Source:** EPSG:2871 (NAD83 HARN California Zone 2, US Survey Feet)
- **Target:** EPSG:4326 (WGS84)
- **Elevation output:** WGS84 ellipsoidal height in meters

### KML Output Format
Point descriptions now show:
```xml
<description>
    Layer: 0
    Elevation (WGS84): 2280.17 m (7480.88 ft)
    Original Coords (EPSG:2871): (6829116.30, 2188133.95, 2280.72) ft
</description>
```

- Clear distinction between WGS84 and original EPSG:2871 values
- Elevation shown in both meters and feet for convenience
- Original coordinates preserved for reference

## Error Handling

### Missing Required Arguments
```bash
$ python convert_dxf_to_kml.py input.dxf --include-stations
error: --include-stations requires --start-station to be specified
```

### Invalid File Paths
```bash
$ python convert_dxf_to_kml.py nonexistent.dxf
Error: File not found: nonexistent.dxf
```

### Output Restriction
```bash
$ python convert_dxf_to_kml.py file1.dxf file2.dxf -o output.kml
error: --output can only be used when converting a single file
```

## Getting Help

Display full help information:
```bash
python convert_dxf_to_kml.py --help
```

## Notes

1. **Station Range Validation**: When both `--start-station` and `--end-station` are provided, the script validates that the measured distance along the points matches the expected station range (within 1 foot tolerance).

2. **End Station Usage**: The `--end-station` parameter is used only for validation. Station values are calculated from the start station and measured distances, not interpolated between start and end.

3. **Elevation Accuracy**: Elevations are properly transformed using 3D coordinate transformation, ensuring accuracy for both display and 3D visualization in Google Earth.

4. **Batch Processing**: When processing multiple files, each file gets a progress indicator showing `[n/total]` to track conversion progress.

5. **Default Behavior**: Without any arguments, the script processes all `.dxf` files in the `DATA/` directory with default settings (no stations, polylines clamped to ground).
