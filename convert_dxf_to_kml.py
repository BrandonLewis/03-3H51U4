#!/usr/bin/env python3
"""
Convert DXF files containing retaining wall points to KML format.
Coordinates are in EPSG:2871 (NAD83(HARN) California Zone 2, US Survey Feet).
"""

import argparse
import json
import math
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

import ezdxf
from ezdxf.acis import dxf as acis_dxf
from ezdxf.acis.api import vertices_from_body
from ezdxf.acis.entities import NONE_REF
from ezdxf.math import BoundingBox, Vec3
from pyproj import Transformer

if TYPE_CHECKING:
    from ezdxf.document import Drawing

STYLE_CONFIG: Dict[str, Dict[str, float | str]] = {
    "align": {"color": "ff4285f4", "icon_scale": 0.75, "label_scale": 0.75, "line_width": 2.8},
    "obm": {"color": "ff34a853", "icon_scale": 0.75, "label_scale": 0.75, "line_width": 2.5},
    "ps": {"color": "ffea4335", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.3},
    "pc": {"color": "ffbb86fc", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.3},
    "df": {"color": "ff00bcd4", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.2},
    "c3d": {"color": "ff9e9e9e", "icon_scale": 0.65, "label_scale": 0.65, "line_width": 2.0},
    "mc": {"color": "fffbbc04", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.4},
    "rd": {"color": "ff795548", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.6},
    "esa": {"color": "ff7e57c2", "icon_scale": 0.7, "label_scale": 0.7, "line_width": 2.1},
    "gis": {"color": "ff009688", "icon_scale": 0.65, "label_scale": 0.65, "line_width": 2.0},
    "pp": {"color": "ff607d8b", "icon_scale": 0.65, "label_scale": 0.65, "line_width": 2.0},
    "default": {"color": "ff0000ff", "icon_scale": 0.6, "label_scale": 0.7, "line_width": 2.0},
}

LAYER_STYLE_PREFIXES = [
    ("align_", "align"),
    ("obm_", "obm"),
    ("ps_", "ps"),
    ("pc_", "pc"),
    ("df_", "df"),
    ("c3d_", "c3d"),
    ("mc_", "mc"),
    ("rd_", "rd"),
    ("esa_", "esa"),
    ("gis_", "gis"),
    ("pp_", "pp"),
]


def resolve_style_name(layer: str) -> str:
    lname = (layer or "").lower()
    for prefix, style_name in LAYER_STYLE_PREFIXES:
        if lname.startswith(prefix):
            return style_name
    return "default"


def point_style_id(style_name: str) -> str:
    return f"pt_{style_name}"


def line_style_id(style_name: str) -> str:
    return f"ln_{style_name}"


def style_config(style_name: str) -> Dict[str, float | str]:
    return STYLE_CONFIG.get(style_name, STYLE_CONFIG["default"])


def build_style_definitions(point_styles: Iterable[str], line_styles: Iterable[str]) -> str:
    parts: List[str] = []
    for style_name in sorted(set(point_styles)):
        config = style_config(style_name)
        color = config.get("color", STYLE_CONFIG["default"]["color"])
        icon_scale = config.get("icon_scale", STYLE_CONFIG["default"]["icon_scale"])
        label_scale = config.get("label_scale", STYLE_CONFIG["default"]["label_scale"])
        parts.append(f'''
    <Style id="{point_style_id(style_name)}">
        <IconStyle>
            <color>{color}</color>
            <scale>{float(icon_scale):.2f}</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
            </Icon>
        </IconStyle>
        <LabelStyle>
            <scale>{float(label_scale):.2f}</scale>
        </LabelStyle>
    </Style>
''')

    for style_name in sorted(set(line_styles)):
        config = style_config(style_name)
        color = config.get("color", STYLE_CONFIG["default"]["color"])
        line_width = config.get("line_width", STYLE_CONFIG["default"]["line_width"])
        parts.append(f'''
    <Style id="{line_style_id(style_name)}">
        <LineStyle>
            <color>{color}</color>
            <width>{float(line_width):.1f}</width>
        </LineStyle>
    </Style>
''')

    return "".join(parts)


def init_solid_stats() -> Dict[str, int]:
    return {
        "bodies": 0,
        "convex_hull": 0,
        "bbox": 0,
        "failed": 0,
    }

@dataclass
class DXFPoint:
    """Simple container for DXF points with metadata."""

    x: float
    y: float
    z: float
    layer: str
    source: str = "POINT"
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class DXFPolyline:
    """Polyline, line, arc, or derived geometry sampled into vertices."""

    coords: List[Tuple[float, float, float]]
    layer: str
    source: str
    metadata: Dict[str, str] = field(default_factory=dict)


def read_dxf_document(dxf_file: str) -> "Drawing":
    """Load and return the DXF document."""
    print(f"Reading DXF file: {dxf_file}")
    return ezdxf.readfile(dxf_file)


def lwpolyline_vertices(entity) -> List[Tuple[float, float, float]]:
    """Extract vertices from an LWPOLYLINE; ignores bulge arcs for now."""
    coords: List[Tuple[float, float, float]] = []
    elevation = entity.dxf.elevation if entity.dxf.hasattr("elevation") else 0.0
    for point in entity.get_points():
        x, y = point[0], point[1]
        z = point[2] if len(point) > 2 else elevation
        coords.append((x, y, z))
    # Ensure closed polylines finish at the first vertex
    if entity.closed and coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def polyline_vertices(entity) -> List[Tuple[float, float, float]]:
    """Extract vertices from a classic POLYLINE/3DPOLY."""
    coords: List[Tuple[float, float, float]] = []
    for vertex in entity.vertices:
        loc = vertex.dxf.location
        coords.append((loc.x, loc.y, loc.z))
    if entity.is_closed and coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def line_vertices(entity) -> List[Tuple[float, float, float]]:
    start = entity.dxf.start
    end = entity.dxf.end
    return [(start[0], start[1], start[2]), (end[0], end[1], end[2])]


def approximate_arc(entity, segments: int = 32) -> List[Tuple[float, float, float]]:
    """Approximate an ARC entity into a polyline."""
    center = entity.dxf.center
    radius = entity.dxf.radius
    start_angle = math.radians(entity.dxf.start_angle)
    end_angle = math.radians(entity.dxf.end_angle)
    if end_angle < start_angle:
        end_angle += 2 * math.pi
    step = (end_angle - start_angle) / max(1, segments)
    coords = []
    for idx in range(segments + 1):
        angle = start_angle + step * idx
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        coords.append((x, y, center[2]))
    return coords


def approximate_circle(entity, segments: int = 64) -> List[Tuple[float, float, float]]:
    """Approximate a circle for visualization."""
    center = entity.dxf.center
    radius = entity.dxf.radius
    coords = []
    for idx in range(segments + 1):
        angle = 2 * math.pi * idx / segments
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        coords.append((x, y, center[2]))
    return coords


def approximate_spline(entity, segments: int = 64) -> List[Tuple[float, float, float]]:
    """Sample a SPLINE entity into a list of vertices."""
    points = entity.approximate(segments)
    return [(pt[0], pt[1], pt[2]) for pt in points]


def convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Compute a 2D convex hull using the monotone chain algorithm."""
    unique = sorted(set(points))
    if len(unique) <= 1:
        return unique

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: List[Tuple[float, float]] = []
    for pt in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], pt) <= 0:
            lower.pop()
        lower.append(pt)

    upper: List[Tuple[float, float]] = []
    for pt in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], pt) <= 0:
            upper.pop()
        upper.append(pt)

    # Concatenate lower and upper without duplicating endpoints
    return lower[:-1] + upper[:-1]


def convert_vertices_to_hull(coords: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
    """Project 3D vertices to XY-plane and build a convex hull polyline."""
    if not coords:
        return []
    xy_points = [(x, y) for x, y, _ in coords]
    hull_2d = convex_hull(xy_points)
    if len(hull_2d) < 2:
        return []
    avg_z = sum(z for _, _, z in coords) / len(coords)
    hull_3d = [(x, y, avg_z) for x, y in hull_2d]
    if hull_3d[0] != hull_3d[-1]:
        hull_3d.append(hull_3d[0])
    return hull_3d


def get_entity_layer(entity) -> str:
    """Return the DXF layer or default to '0'."""
    try:
        layer = entity.dxf.layer
    except AttributeError:
        return "0"
    return layer or "0"


def extract_points_from_doc(doc: "Drawing") -> List[DXFPoint]:
    """Extract DXF POINT entities."""
    msp = doc.modelspace()
    points: List[DXFPoint] = []
    for entity in msp.query("POINT"):
        loc = entity.dxf.location
        metadata: Dict[str, str] = {}
        if entity.dxf.hasattr("thickness"):
            metadata["thickness"] = f"{entity.dxf.thickness}"
        points.append(
            DXFPoint(
                x=loc.x,
                y=loc.y,
                z=loc.z,
                layer=get_entity_layer(entity),
                source="POINT",
                metadata=metadata,
            )
        )
    return points


def extract_block_references(doc: "Drawing") -> List[DXFPoint]:
    """Extract INSERT entities as point markers."""
    msp = doc.modelspace()
    references: List[DXFPoint] = []
    for insert in msp.query("INSERT"):
        insert_point = insert.dxf.insert
        metadata: Dict[str, str] = {"block_name": insert.dxf.name}
        if insert.attribs:
            metadata["attributes"] = "; ".join(
                f"{attrib.dxf.tag}={attrib.dxf.text}" for attrib in insert.attribs
            )
        references.append(
            DXFPoint(
                x=insert_point.x,
                y=insert_point.y,
                z=getattr(insert_point, "z", 0.0),
                layer=get_entity_layer(insert),
                source="BLOCK_REFERENCE",
                metadata=metadata,
            )
        )
    return references


def _append_polyline(
    collector: List[DXFPolyline],
    coords: Iterable[Tuple[float, float, float]],
    layer: str,
    source: str,
    metadata: Optional[Dict[str, str]] = None,
):
    coord_list = list(coords)
    if len(coord_list) < 2:
        return
    collector.append(
        DXFPolyline(
            coords=coord_list,
            layer=layer,
            source=source,
            metadata=metadata or {},
        )
    )


def convert_virtual_entities(entity, parent_layer: str) -> List[DXFPolyline]:
    """Convert ACAD_PROXY virtual entities into polyline data."""
    polylines: List[DXFPolyline] = []
    try:
        virtual_entities = list(entity.virtual_entities())
    except Exception as exc:  # pragma: no cover - safety
        print(f"  Warning: failed decoding proxy entity ({exc})")
        return polylines

    for sub_entity in virtual_entities:
        layer = get_entity_layer(sub_entity) or parent_layer
        metadata = {
            "parent_entity": entity.dxftype(),
            "virtual_type": sub_entity.dxftype(),
        }
        coords: List[Tuple[float, float, float]] = []
        etype = sub_entity.dxftype()
        if etype == "LWPOLYLINE":
            coords = lwpolyline_vertices(sub_entity)
        elif etype == "POLYLINE":
            coords = polyline_vertices(sub_entity)
        elif etype == "LINE":
            coords = line_vertices(sub_entity)
        elif etype == "ARC":
            coords = approximate_arc(sub_entity)
        elif etype == "CIRCLE":
            coords = approximate_circle(sub_entity)
        elif etype == "SPLINE":
            coords = approximate_spline(sub_entity)
        elif etype == "POINT":
            loc = sub_entity.dxf.location
            coords = [(loc.x, loc.y, loc.z), (loc.x, loc.y, loc.z)]
            metadata["note"] = "proxy point duplicated for visibility"
        else:
            continue
        _append_polyline(polylines, coords, layer or parent_layer, "ACAD_PROXY_ENTITY", metadata)
    return polylines


def _is_none_ref(acis_obj) -> bool:
    if acis_obj is None:
        return True
    if acis_obj is NONE_REF:
        return True
    return bool(getattr(acis_obj, "is_none", False))


def collect_vertices_from_body(body) -> List[Tuple[float, float, float]]:
    """Return vertices from an ACIS body, falling back to a tolerant parser."""
    try:
        verts = vertices_from_body(body)
        return [(v.x, v.y, v.z) for v in verts]
    except Exception as exc:
        print(f"  Warning: standard ACIS vertex extraction failed ({exc}); attempting tolerant parse.")
        return tolerant_vertices_from_body(body)


def tolerant_vertices_from_body(body) -> List[Tuple[float, float, float]]:
    """Best-effort vertex extraction that skips incomplete coedges."""
    vertices: List[Tuple[float, float, float]] = []
    transform = getattr(body, "transform", None)
    matrix = None
    if transform is not None and not transform.is_none:
        matrix = transform.matrix
    lump = getattr(body, "lump", NONE_REF)
    while not _is_none_ref(lump):
        vertices.extend(tolerant_vertices_from_lump(lump, matrix))
        lump = lump.next_lump
    return vertices


def tolerant_vertices_from_lump(lump, matrix) -> List[Tuple[float, float, float]]:
    collected: List[Vec3] = []
    shell = getattr(lump, "shell", NONE_REF)
    if _is_none_ref(shell):
        return []
    face = getattr(shell, "face", NONE_REF)
    while not _is_none_ref(face):
        loop = getattr(face, "loop", NONE_REF)
        if _is_none_ref(loop):
            face = face.next_face
            continue
        first_coedge = getattr(loop, "coedge", NONE_REF)
        if _is_none_ref(first_coedge):
            face = face.next_face
            continue
        coedge = first_coedge
        guard = 0
        while True:
            if _is_none_ref(coedge) or guard > 4096:
                break
            edge = getattr(coedge, "edge", None)
            if edge is None or _is_none_ref(edge):
                break
            try:
                if coedge.sense:
                    point = edge.end_vertex.point.location
                else:
                    point = edge.start_vertex.point.location
            except AttributeError:
                break
            collected.append(point)
            guard += 1
            coedge = getattr(coedge, "next_coedge", NONE_REF)
            if coedge is first_coedge:
                break
        face = face.next_face

    if matrix is not None and collected:
        collected = list(matrix.transform_vertices(collected))

    return [(v.x, v.y, v.z) for v in collected]


def footprint_from_bbox(vertices: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
    """Create an axis-aligned footprint from a set of vertices."""
    if not vertices:
        return []
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if math.isclose(min_x, max_x) or math.isclose(min_y, max_y):
        return []
    avg_z = sum(zs) / len(zs)
    coords = [
        (min_x, min_y, avg_z),
        (max_x, min_y, avg_z),
        (max_x, max_y, avg_z),
        (min_x, max_y, avg_z),
    ]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def convert_solid_to_polylines(entity, solid_stats) -> List[DXFPolyline]:
    """Approximate 3DSOLID entities by deriving hulls or bounding footprints."""
    polylines: List[DXFPolyline] = []
    try:
        bodies = acis_dxf.load_dxf(entity)
    except Exception as exc:
        print(f"  Warning: unable to load ACIS data for {entity.dxftype()} ({exc})")
        solid_stats["failed"] += 1
        return polylines

    if not bodies:
        solid_stats["failed"] += 1
        return polylines

    for body_index, body in enumerate(bodies):
        solid_stats["bodies"] += 1
        vertices = collect_vertices_from_body(body)
        if not vertices:
            solid_stats["failed"] += 1
            continue
        hull_coords = convert_vertices_to_hull(vertices)
        representation = "convex_hull"
        coords = hull_coords
        if not coords:
            coords = footprint_from_bbox(vertices)
            representation = "bbox" if coords else None
        if not coords:
            solid_stats["failed"] += 1
            continue
        metadata = {
            "body_index": str(body_index),
            "representation": representation,
            "vertex_count": str(len(vertices)),
        }
        if representation == "bbox":
            metadata["note"] = "Hull unavailable; fallback to bounding box"
        _append_polyline(
            polylines,
            coords,
            layer=get_entity_layer(entity),
            source="3DSOLID",
            metadata=metadata,
        )
        solid_stats[representation] += 1
    return polylines


def extract_polylines_from_doc(doc: "Drawing") -> Tuple[List[DXFPolyline], Dict[str, int]]:
    """Collect polyline-like geometry, including proxies and solids."""
    msp = doc.modelspace()
    polylines: List[DXFPolyline] = []
    solid_stats = init_solid_stats()
    for entity in msp:
        etype = entity.dxftype()
        layer = get_entity_layer(entity)
        metadata = {"entity_type": etype}
        if etype == "LWPOLYLINE":
            _append_polyline(polylines, lwpolyline_vertices(entity), layer, "LWPOLYLINE", metadata)
        elif etype == "POLYLINE":
            _append_polyline(polylines, polyline_vertices(entity), layer, "POLYLINE", metadata)
        elif etype == "LINE":
            _append_polyline(polylines, line_vertices(entity), layer, "LINE", metadata)
        elif etype == "ARC":
            _append_polyline(polylines, approximate_arc(entity), layer, "ARC", metadata)
        elif etype == "CIRCLE":
            _append_polyline(polylines, approximate_circle(entity), layer, "CIRCLE", metadata)
        elif etype == "SPLINE":
            _append_polyline(polylines, approximate_spline(entity), layer, "SPLINE", metadata)
        elif etype == "ACAD_PROXY_ENTITY":
            polylines.extend(convert_virtual_entities(entity, layer))
        elif etype == "3DSOLID":
            polylines.extend(convert_solid_to_polylines(entity, solid_stats))
    return polylines, solid_stats

def get_transformer(source_epsg='EPSG:2871', target_epsg='EPSG:4326'):
    """
    Create a 2D coordinate transformer for horizontal coordinates.

    Note: EPSG:2871 is a 2D horizontal CRS without vertical datum specification.
    Elevation values are treated as orthometric heights (NAVD88 or similar) and
    only require unit conversion (US Survey Feet to meters), not datum transformation.

    Args:
        source_epsg: Source coordinate system (default: EPSG:2871)
        target_epsg: Target coordinate system (default: WGS84)

    Returns:
        Transformer object for 2D horizontal transformation
    """
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)

def transform_point(x, y, z, transformer):
    """
    Transform coordinates from EPSG:2871 (US Survey Feet) to WGS84.
    Transforms horizontal coordinates and converts elevation units.

    Args:
        x: Easting in US Survey Feet
        y: Northing in US Survey Feet
        z: Elevation in US Survey Feet (orthometric height, likely NAVD88)
        transformer: pyproj Transformer object for 2D horizontal transformation

    Returns:
        tuple: (longitude, latitude, elevation_meters)
            - longitude: WGS84 longitude in decimal degrees
            - latitude: WGS84 latitude in decimal degrees
            - elevation_meters: Elevation in meters (unit conversion only, same vertical datum)
    """
    # Transform horizontal coordinates (2D)
    lon, lat = transformer.transform(x, y)

    # Convert elevation from US Survey Feet to meters (unit conversion only)
    # 1 US Survey Foot = 0.3048006096 meters
    elev_meters = z * 0.3048006096

    return lon, lat, elev_meters

def calculate_cumulative_distances(points: List[DXFPoint]) -> List[Optional[float]]:
    """
    Calculate cumulative distance along POINT entities.

    Returns:
        list: Distance per point index (None for non-POINT sources)
    """
    if not points:
        return []
    filtered_indices: List[int] = []
    filtered_points: List[DXFPoint] = []
    for idx, point in enumerate(points):
        if point.source == "POINT":
            filtered_indices.append(idx)
            filtered_points.append(point)
    if not filtered_points:
        return [None] * len(points)

    distances = [0.0]
    for i in range(1, len(filtered_points)):
        p1 = filtered_points[i - 1]
        p2 = filtered_points[i]
        dist = math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
        distances.append(distances[-1] + dist)

    expanded: List[Optional[float]] = [None] * len(points)
    for idx, distance in zip(filtered_indices, distances):
        expanded[idx] = distance
    return expanded

def format_station(station_feet):
    """
    Format station value in standard civil engineering format.

    Args:
        station_feet: Station in feet (e.g., 10048.77)

    Returns:
        str: Formatted station (e.g., "100+48.77")
    """
    hundreds = int(station_feet // 100)
    feet = station_feet % 100
    return f"{hundreds}+{feet:05.2f}"

def extract_points_from_dxf(dxf_file: str) -> List[DXFPoint]:
    """Backwards compatible helper returning DXFPoint records."""
    doc = read_dxf_document(dxf_file)
    return extract_points_from_doc(doc)

def extract_polylines_from_dxf(dxf_file: str) -> List[DXFPolyline]:
    """Backwards compatible helper returning DXFPolyline records."""
    doc = read_dxf_document(dxf_file)
    polylines, _ = extract_polylines_from_doc(doc)
    return polylines

def create_kml(points: List[DXFPoint],
               polylines: List[DXFPolyline],
               block_references: Optional[List[DXFPoint]],
               output_file,
               file_description,
               start_station=None,
               end_station=None,
               include_stations=False,
               polyline_elevation=False,
               no_point_label=False):
    """
    Create KML file from points and polylines.

    Args:
        points: List of DXFPoint instances
        polylines: List of DXFPolyline instances
        block_references: INSERT entities represented as points
        output_file: Output KML file path
        file_description: Description for the KML file
        start_station: Starting station in feet (e.g., 10000 for 100+00.00)
        end_station: Ending station in feet (e.g., 11048.77 for 110+48.77)
        include_stations: If True, include station values in point names
        polyline_elevation: If True, render polylines at elevation (absolute altitude mode)
        no_point_label: If True, suppress point labels (empty name)
    """
    block_references = block_references or []

    point_style_names = {resolve_style_name(pt.layer) for pt in points}
    point_style_names.update(resolve_style_name(ref.layer) for ref in block_references)
    line_style_names = {resolve_style_name(poly.layer) for poly in polylines}

    # Create transformer once and reuse
    print(f"  Creating coordinate transformer...")
    transformer = get_transformer()

    # Calculate cumulative distances for station interpolation
    cumulative_distances: Optional[List[Optional[float]]] = None
    total_distance = None
    if points and start_station is not None and end_station is not None and include_stations:
        print(f"  Calculating cumulative distances...")
        cumulative_distances = calculate_cumulative_distances(points)
        valid_distances = [d for d in cumulative_distances if d is not None]
        total_distance = valid_distances[-1] if valid_distances else None
        expected_distance = end_station - start_station
        if total_distance is not None:
            print(f"  Total distance: {total_distance:.2f} feet")
        print(f"  Station range: {format_station(start_station)} to {format_station(end_station)}")
        print(f"  Expected distance: {expected_distance:.2f} feet")

        # Validate that measured distance matches station range
        if total_distance is not None:
            distance_diff = abs(total_distance - expected_distance)
            if distance_diff > 1.0:  # Tolerance of 1 foot
                print(f"  WARNING: Measured distance ({total_distance:.2f} ft) differs from station range ({expected_distance:.2f} ft) by {distance_diff:.2f} ft")
                print(f"           This may indicate incorrect station values or non-linear alignment")

    # Use list for efficient string building
    kml_parts = []

    kml_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>{os.path.basename(output_file)}</name>
    <description>{file_description}</description>
''')

    if point_style_names or line_style_names:
        kml_parts.append(build_style_definitions(point_style_names, line_style_names))

    # Add points folder
    if points:
        print(f"  Processing {len(points)} points...")
        kml_parts.append(f'''
    <Folder>
        <name>Retaining Wall Points</name>
        <description>{len(points)} retaining wall points</description>
        <open>1</open>
''')

        for i, point in enumerate(points):
            if i % 100 == 0 and i > 0:
                print(f"    Processed {i}/{len(points)} points...")

            lon, lat, elev = transform_point(point.x, point.y, point.z, transformer)

            # Calculate elevation in feet for display
            elev_ft = elev * 3.28084  # Convert meters to feet

            # Calculate point name
            if no_point_label:
                # Suppress point label with empty name
                point_name = ""
            elif include_stations:
                # Calculate station value
                if start_station is not None and end_station is not None and cumulative_distances:
                    distance_value = cumulative_distances[i] if cumulative_distances[i] is not None else i * 8.0
                    station_ft = start_station + distance_value
                    station_str = format_station(station_ft)
                else:
                    # Fallback to approximate station based on index
                    station_ft = i * 8.0  # Approximate 8-foot spacing
                    station_str = format_station(station_ft)
                point_name = f"RW Sta {station_str}"
            else:
                point_name = f"Point {i+1}"

            metadata_lines = [
                f"Layer: {point.layer}",
                f"Source: {point.source}",
                f"Elevation: {elev:.2f} m ({elev_ft:.2f} ft)",
                f"Original Coords (EPSG:2871): ({point.x:.2f}, {point.y:.2f}, {point.z:.2f}) ft",
                "Note: Elevation is orthometric height (likely NAVD88)",
            ]
            for key, value in point.metadata.items():
                metadata_lines.append(f"{key}: {value}")
            description = "\\n".join(metadata_lines)

            style_name = resolve_style_name(point.layer)
            kml_parts.append(f'''
        <Placemark>
            <name>{point_name}</name>
            <description>{description}</description>
            <styleUrl>#{point_style_id(style_name)}</styleUrl>
            <Point>
                <altitudeMode>clampToGround</altitudeMode>
                <coordinates>{lon:.10f},{lat:.10f},0</coordinates>
            </Point>
        </Placemark>
''')

        kml_parts.append('''    </Folder>
''')

    if block_references:
        print(f"  Processing {len(block_references)} block references...")
        kml_parts.append(f'''
    <Folder>
        <name>Block References</name>
        <description>{len(block_references)} INSERT entities</description>
        <open>0</open>
''')
        for i, ref in enumerate(block_references):
            lon, lat, elev = transform_point(ref.x, ref.y, ref.z, transformer)
            elev_ft = elev * 3.28084
            block_name = ref.metadata.get("block_name", f"Block {i+1}")
            description_lines = [
                f"Layer: {ref.layer}",
                f"Source: {ref.source}",
                f"Block: {block_name}",
                f"Elevation: {elev:.2f} m ({elev_ft:.2f} ft)",
            ]
            for key, value in ref.metadata.items():
                if key == "block_name":
                    continue
                description_lines.append(f"{key}: {value}")
            description = "\\n".join(description_lines)
            style_name = resolve_style_name(ref.layer)
            kml_parts.append(f'''
        <Placemark>
            <name>{block_name}</name>
            <description>{description}</description>
            <styleUrl>#{point_style_id(style_name)}</styleUrl>
            <Point>
                <altitudeMode>clampToGround</altitudeMode>
                <coordinates>{lon:.10f},{lat:.10f},0</coordinates>
            </Point>
        </Placemark>
''')
        kml_parts.append('''    </Folder>
''')

    # Add polylines folder
    if polylines:
        print(f"  Processing {len(polylines)} polylines...")
        kml_parts.append(f'''
    <Folder>
        <name>Polylines</name>
        <description>{len(polylines)} polyline entities</description>
        <open>1</open>
''')

        for i, poly in enumerate(polylines):
            if i % 10 == 0 and i > 0:
                print(f"    Processed {i}/{len(polylines)} polylines...")

            # Set altitude mode based on flag
            altitude_mode = 'absolute' if polyline_elevation else 'clampToGround'

            description_lines = [
                f"Layer: {poly.layer}",
                f"Source: {poly.source}",
                f"Vertices: {len(poly.coords)}",
            ]
            for key, value in poly.metadata.items():
                description_lines.append(f"{key}: {value}")
            description_text = "&#10;".join(description_lines)
            style_name = resolve_style_name(poly.layer)
            kml_parts.append(f'''
        <Placemark>
            <name>Polyline {i+1}</name>
            <description>{description_text}</description>
            <styleUrl>#{line_style_id(style_name)}</styleUrl>
            <LineString>
                <altitudeMode>{altitude_mode}</altitudeMode>
                <coordinates>
''')

            # Transform all coordinates at once for this polyline
            coord_strings = []
            for x, y, z in poly.coords:
                lon, lat, elev_meters = transform_point(x, y, z, transformer)
                if polyline_elevation:
                    # Include elevation in meters for absolute altitude mode (orthometric height)
                    coord_strings.append(f'{lon:.10f},{lat:.10f},{elev_meters:.2f}')
                else:
                    # Clamp to ground (elevation = 0)
                    coord_strings.append(f'{lon:.10f},{lat:.10f},0')

            kml_parts.append('\n'.join(f'                    {c}' for c in coord_strings))
            kml_parts.append('\n')

            kml_parts.append('''                </coordinates>
            </LineString>
        </Placemark>
''')

        kml_parts.append('''    </Folder>
''')

    kml_parts.append('''</Document>
</kml>
''')

    # Write to file
    print(f"  Writing KML file...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(kml_parts))

    print(f"Created KML file: {output_file}")
    print(f"  - {len(points)} points")
    print(f"  - {len(polylines)} polylines")

def convert_dxf_to_kml(dxf_file,
                       output_file=None,
                       start_station=None,
                       end_station=None,
                       include_stations=False,
                       polyline_elevation=False,
                       no_point_label=False,
                       return_summary=False):
    """
    Convert DXF file to KML format.

    Args:
        dxf_file: Path to input DXF file
        output_file: Path to output KML file (optional)
        start_station: Starting station in feet (e.g., 10000 for 100+00.00)
        end_station: Ending station in feet (e.g., 11048.77 for 110+48.77)
        include_stations: If True, include station values in point names
        polyline_elevation: If True, render polylines at elevation (absolute altitude mode)
        no_point_label: If True, suppress point labels (empty name)
    """
    if output_file is None:
        base_name = os.path.splitext(dxf_file)[0]
        output_file = f"{base_name}.kml"

    # Extract data from DXF
    doc = read_dxf_document(dxf_file)
    points = extract_points_from_doc(doc)
    block_references = extract_block_references(doc)
    polylines, solid_stats = extract_polylines_from_doc(doc)
    print(f"  Extracted {len(points)} points, {len(block_references)} block references, {len(polylines)} polyline-like entities.")
    if solid_stats["bodies"]:
        print(
            f"    Solid breakdown -> hull: {solid_stats['convex_hull']}, bbox fallback: {solid_stats['bbox']}, failed: {solid_stats['failed']}"
        )

    # Create description
    file_name = os.path.basename(dxf_file)
    description = f"Converted from {file_name} - EPSG:2871 (NAD83(HARN) CA Zone 2, US Survey Feet) to WGS84"
    if start_station is not None and end_station is not None and include_stations:
        description += f"\nStation range: {format_station(start_station)} to {format_station(end_station)}"

    # Create KML
    create_kml(points, polylines, block_references, output_file, description, start_station, end_station,
               include_stations, polyline_elevation, no_point_label)

    summary = {
        "points": len(points),
        "block_references": len(block_references),
        "polylines": len(polylines),
        "polyline_sources": dict(Counter(poly.source for poly in polylines)),
        "solid_conversion": solid_stats,
    }

    if return_summary:
        return output_file, summary
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert DXF files containing retaining wall points to KML format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  %(prog)s input.dxf

  # Convert with custom output name
  %(prog)s input.dxf -o output.kml

  # Convert with station information
  %(prog)s input.dxf --start-station 30000 --end-station 30872 --include-stations

  # Convert with elevated polylines
  %(prog)s input.dxf --polyline-elevation

  # Convert without point labels
  %(prog)s input.dxf --no-point-label

  # Convert all DXF files in DATA directory
  %(prog)s DATA/*.dxf

  # Full example with all options
  %(prog)s input.dxf -o output.kml --start-station 30000 --end-station 30872 \\
           --include-stations --polyline-elevation --no-point-label

Station Format:
  Stations should be specified in feet (e.g., 30000 for station 300+00.00)
  The script calculates stations based on actual measured distances.
        """
    )

    parser.add_argument(
        'input_files',
        nargs='*',
        help='DXF file(s) to convert. If no files specified, processes all .dxf files in DATA directory.'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output KML file path (only valid when converting a single file)'
    )

    parser.add_argument(
        '--start-station',
        type=float,
        help='Starting station in feet (e.g., 30000 for station 300+00.00)'
    )

    parser.add_argument(
        '--end-station',
        type=float,
        help='Ending station in feet (e.g., 30872 for station 308+72.00). Used for validation.'
    )

    parser.add_argument(
        '--include-stations',
        action='store_true',
        help='Include station values in point names (requires --start-station)'
    )

    parser.add_argument(
        '--polyline-elevation',
        action='store_true',
        help='Render polylines at elevation (absolute altitude mode) instead of clamping to ground'
    )

    parser.add_argument(
        '--no-point-label',
        action='store_true',
        help='Suppress point labels (points will have empty names)'
    )

    parser.add_argument(
        '--summary-json',
        help='Write per-file extraction summary to JSON for automation workflows'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.include_stations and args.start_station is None:
        parser.error("--include-stations requires --start-station to be specified")

    if args.output and len(args.input_files) > 1:
        parser.error("--output can only be used when converting a single file")

    # Determine which files to process
    if args.input_files:
        dxf_files = args.input_files
    else:
        # Process all DXF files in DATA directory
        import glob
        dxf_files = glob.glob("DATA/*.dxf")
        if not dxf_files:
            # Try alternate path
            dxf_files = glob.glob("/home/user/03-3H51U4/DATA/*.dxf")

        if not dxf_files:
            print("No DXF files found in DATA directory")
            print("\nUsage: python convert_dxf_to_kml.py <input.dxf> [options]")
            print("Run with --help for more information")
            sys.exit(1)

        print(f"Found {len(dxf_files)} DXF files to convert\n")

    summary_report = {}
    need_summary = bool(args.summary_json)

    # Process each file
    for i, dxf_file in enumerate(sorted(dxf_files)):
        if len(dxf_files) > 1:
            print(f"\n{'='*80}")
            print(f"[{i+1}/{len(dxf_files)}] Processing: {dxf_file}")

        if not os.path.exists(dxf_file):
            print(f"Error: File not found: {dxf_file}")
            continue

        try:
            # Determine output file
            output_file = args.output if args.output else None

            # Convert the file
            conversion_result = convert_dxf_to_kml(
                dxf_file=dxf_file,
                output_file=output_file,
                start_station=args.start_station,
                end_station=args.end_station,
                include_stations=args.include_stations,
                polyline_elevation=args.polyline_elevation,
                no_point_label=args.no_point_label,
                return_summary=need_summary,
            )

            if need_summary:
                result, summary = conversion_result
                summary_report[dxf_file] = summary
            else:
                result = conversion_result

            if len(dxf_files) == 1:
                print(f"\nSuccess! Output file: {result}")

        except Exception as e:
            print(f"Error processing {dxf_file}: {e}")
            import traceback
            traceback.print_exc()

    if args.summary_json:
        with open(args.summary_json, 'w', encoding='utf-8') as summary_file:
            json.dump(summary_report, summary_file, indent=2)
        print(f"\nWrote conversion summary to {args.summary_json}")

    if len(dxf_files) > 1:
        print(f"\n{'='*80}")
        print("All conversions complete!")
