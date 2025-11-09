#!/usr/bin/env python3
"""
Modern LandXML → KML converter.

Highlights
----------
* Processes every <Alignment> in a LandXML file (not just the first one).
* Supports lines, circular curves, and spirals with adaptive interpolation.
* Reads vertical profile data (<PVI>, <ParaCurve>, etc.) to build 3D paths.
* Honors the source EPSG/units metadata when present, with CLI overrides.
* Generates metadata-rich, multi-style KML along with optional JSON summaries.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING
import xml.etree.ElementTree as ET

from pyproj import Transformer


LINEAR_UNITS_TO_METERS = {
    "meter": 1.0,
    "metre": 1.0,
    "foot": 0.3048,
    "internationalfoot": 0.3048,
    "ussurveyfoot": 0.3048006096,
    "foot_us": 0.3048006096,
    "feet": 0.3048,
}

STYLE_COLORS = [
    "ff4285f4",
    "ff34a853",
    "ffea4335",
    "fffbbc04",
    "ff9c27b0",
    "ff00acc1",
    "ffff7043",
]


@dataclass
class AlignmentPoint:
    x: float
    y: float
    station: float
    z: Optional[float] = None


@dataclass
class AlignmentRecord:
    name: str
    description: str
    points: List[AlignmentPoint] = field(default_factory=list)
    source_file: str = ""
    has_vertical_profile: bool = False

    def total_length(self) -> float:
        if not self.points:
            return 0.0
        return self.points[-1].station - self.points[0].station


@dataclass
class ProfileEntry:
    station: float
    elevation: float
    length: Optional[float] = None
    kind: str = "PVI"


@dataclass
class VerticalCurve:
    station: float
    length: float
    grade_in: float
    grade_out: float
    pvc_sta: float
    pvt_sta: float
    pvc_elev: float
    pvt_elev: float


def namespace_map(root: ET.Element) -> Dict[str, str]:
    ns = {"landxml": "http://www.landxml.org/schema/LandXML-1.2"}
    if root.tag.startswith("{"):
        uri = root.tag.split("}")[0].strip("{")
        ns["landxml"] = uri
    return ns


def parse_point_text(elem: ET.Element) -> Tuple[float, float]:
    """LandXML stores points as Northing Easting (Y X)."""
    coords = elem.text.strip().split()
    if len(coords) < 2:
        raise ValueError("Invalid coordinate string")
    northing, easting = map(float, coords[:2])
    return easting, northing


def distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def interpolate_arc_points(
    center: Tuple[float, float],
    start: Tuple[float, float],
    end: Tuple[float, float],
    radius: float,
    delta_deg: float,
    rotation: str,
    chord_tolerance: float,
) -> List[Tuple[float, float]]:
    start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
    delta_rad = math.radians(delta_deg)
    if rotation == "cw":
        delta_rad = -delta_rad
    arc_length = abs(radius * delta_rad)
    chord_tol = max(chord_tolerance, 1.0)
    segments = max(2, int(math.ceil(arc_length / chord_tol)))
    points: List[Tuple[float, float]] = []
    for i in range(segments + 1):
        fraction = i / segments
        angle = start_angle + delta_rad * fraction
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    # enforce final endpoint to mitigate rounding error
    points[-1] = end
    return points


def interpolate_spiral_points(
    start: Tuple[float, float],
    end: Tuple[float, float],
    length: Optional[float],
    chord_tolerance: float,
) -> List[Tuple[float, float]]:
    chord_tol = max(chord_tolerance, 1.0)
    approx_length = length or distance_2d(start, end)
    segments = max(2, int(math.ceil(approx_length / chord_tol)))
    points = []
    for i in range(segments + 1):
        fraction = i / segments
        x = start[0] + (end[0] - start[0]) * fraction
        y = start[1] + (end[1] - start[1]) * fraction
        points.append((x, y))
    return points


def cumulative_station(points: List[Tuple[float, float]], sta_start: float) -> List[AlignmentPoint]:
    alignment_points: List[AlignmentPoint] = []
    total = sta_start
    prev: Optional[Tuple[float, float]] = None
    for idx, (x, y) in enumerate(points):
        if idx == 0:
            total = sta_start
        elif prev is not None:
            total += distance_2d(prev, (x, y))
        alignment_points.append(AlignmentPoint(x=x, y=y, station=total))
        prev = (x, y)
    return alignment_points


def decimate_duplicates(points: Iterable[Tuple[float, float]], tol: float = 1e-6) -> List[Tuple[float, float]]:
    unique: List[Tuple[float, float]] = []
    for pt in points:
        if not unique:
            unique.append(pt)
            continue
        dx = abs(unique[-1][0] - pt[0])
        dy = abs(unique[-1][1] - pt[1])
        if dx <= tol and dy <= tol:
            continue
        unique.append(pt)
    return unique


def collect_profile_points(profile_elem: ET.Element, ns: Dict[str, str]) -> List[ProfileEntry]:
    entries: List[ProfileEntry] = []
    prof_align = profile_elem.find("landxml:ProfAlign", ns)
    if prof_align is None:
        return entries
    for child in prof_align:
        tag = child.tag.split("}")[-1]
        if tag not in {"PVI", "ParaCurve", "HighPoint", "LowPoint"}:
            continue
        text = (child.text or "").strip()
        parts = text.split()
        if len(parts) < 2:
            continue
        try:
            station = float(parts[0])
            elevation = float(parts[1])
        except ValueError:
            continue
        length_attr = child.get("length")
        length_val = float(length_attr) if length_attr else None
        entries.append(ProfileEntry(station=station, elevation=elevation, length=length_val, kind=tag))
    entries.sort(key=lambda entry: entry.station)
    return entries


def load_profiles_from_file(xml_path: Path) -> Dict[str, List[ProfileEntry]]:
    root = ET.parse(xml_path).getroot()
    ns = namespace_map(root)
    profiles: Dict[str, List[ProfileEntry]] = {}
    for profile in root.findall(".//landxml:Profile", ns):
        profile_name = profile.get("name") or profile.get("alignRef")
        if not profile_name:
            continue
        entries = collect_profile_points(profile, ns)
        if entries:
            profiles.setdefault(profile_name, []).extend(entries)
    return profiles


def apply_profile(alignment_points: List[AlignmentPoint], profile_entries: List[ProfileEntry]):
    if not alignment_points or not profile_entries:
        return

    entries = sorted(profile_entries, key=lambda entry: entry.station)
    linear_breaks: List[Tuple[float, float]] = []
    curves: List[VerticalCurve] = []

    # Helper to add linear breakpoints without duplicates
    def add_linear_point(sta: float, elev: float):
        if not linear_breaks:
            linear_breaks.append((sta, elev))
            return
        last_sta, last_elev = linear_breaks[-1]
        if math.isclose(last_sta, sta, rel_tol=0, abs_tol=1e-6):
            linear_breaks[-1] = (sta, elev)
        else:
            linear_breaks.append((sta, elev))

    for idx, entry in enumerate(entries):
        prev_entry = entries[idx - 1] if idx > 0 else None
        next_entry = entries[idx + 1] if idx + 1 < len(entries) else None
        if entry.length and prev_entry and next_entry:
            delta_in = entry.station - prev_entry.station
            delta_out = next_entry.station - entry.station
            if delta_in <= 0 or delta_out <= 0:
                add_linear_point(entry.station, entry.elevation)
                continue
            grade_in = (entry.elevation - prev_entry.elevation) / delta_in
            grade_out = (next_entry.elevation - entry.elevation) / delta_out
            L = entry.length
            half = L / 2.0
            pvc_sta = entry.station - half
            pvt_sta = entry.station + half
            pvc_elev = entry.elevation - grade_in * half
            pvt_elev = entry.elevation + grade_out * half
            curves.append(
                VerticalCurve(
                    station=entry.station,
                    length=L,
                    grade_in=grade_in,
                    grade_out=grade_out,
                    pvc_sta=pvc_sta,
                    pvt_sta=pvt_sta,
                    pvc_elev=pvc_elev,
                    pvt_elev=pvt_elev,
                )
            )
            add_linear_point(pvc_sta, pvc_elev)
            add_linear_point(pvt_sta, pvt_elev)
        else:
            add_linear_point(entry.station, entry.elevation)

    if not linear_breaks:
        return

    linear_breaks.sort(key=lambda p: p[0])
    curves.sort(key=lambda c: c.pvc_sta)

    def find_linear_elev(sta: float) -> float:
        if sta <= linear_breaks[0][0]:
            return linear_breaks[0][1]
        if sta >= linear_breaks[-1][0]:
            return linear_breaks[-1][1]
        lo, hi = 0, len(linear_breaks) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if linear_breaks[mid][0] < sta:
                lo = mid + 1
            else:
                hi = mid - 1
        idx = max(1, lo)
        s0, e0 = linear_breaks[idx - 1]
        s1, e1 = linear_breaks[idx]
        if math.isclose(s0, s1):
            return e1
        fraction = (sta - s0) / (s1 - s0)
        return e0 + fraction * (e1 - e0)

    def find_curve_elev(sta: float) -> Optional[float]:
        if not curves:
            return None
        lo, hi = 0, len(curves) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            curve = curves[mid]
            if curve.pvt_sta < sta:
                lo = mid + 1
            elif curve.pvc_sta > sta:
                hi = mid - 1
            else:
                t = sta - curve.pvc_sta
                L = curve.length
                quadratic = ((curve.grade_out - curve.grade_in) / (2 * L)) * t * t
                return curve.pvc_elev + curve.grade_in * t + quadratic
        return None

    for point in alignment_points:
        curve_elev = find_curve_elev(point.station)
        if curve_elev is not None:
            point.z = curve_elev
        else:
            point.z = find_linear_elev(point.station)


def parse_alignments(
    xml_path: Path,
    chord_tolerance: float,
    ns: Dict[str, str],
    extra_profiles: Optional[Dict[str, List[ProfileEntry]]] = None,
) -> Tuple[List[AlignmentRecord], Dict[str, List[ProfileEntry]], Dict[str, str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    profiles: Dict[str, List[ProfileEntry]] = {}

    # Collect profile data keyed by profile name / alignRef
    for profile in root.findall(".//landxml:Profile", ns):
        profile_name = profile.get("name") or profile.get("alignRef")
        if not profile_name:
            continue
        pts = collect_profile_points(profile, ns)
        if pts:
            profiles.setdefault(profile_name, []).extend(pts)

    if extra_profiles:
        for key, entries in extra_profiles.items():
            profiles.setdefault(key, []).extend(entries)

    # gather metadata
    metadata: Dict[str, str] = {}
    units_elem = root.find(".//landxml:Units/landxml:Imperial", ns)
    if units_elem is not None:
        metadata["linear_unit"] = units_elem.get("linearUnit", "")
    coord_sys = root.find(".//landxml:CoordinateSystem", ns)
    if coord_sys is not None:
        metadata["epsg"] = coord_sys.get("epsgCode", "")

    alignments: List[AlignmentRecord] = []

    for alignment_elem in root.findall(".//landxml:Alignment", ns):
        name = alignment_elem.get("name", "Unnamed")
        description = alignment_elem.get("desc", "")
        sta_start = float(alignment_elem.get("staStart", "0") or 0.0)
        coord_geom = alignment_elem.find("landxml:CoordGeom", ns)
        if coord_geom is None:
            continue

        raw_points: List[Tuple[float, float]] = []

        for child in coord_geom:
            tag = child.tag.split("}")[-1]
            if tag == "Line":
                start_elem = child.find("landxml:Start", ns)
                end_elem = child.find("landxml:End", ns)
                if start_elem is None or end_elem is None:
                    continue
                start = parse_point_text(start_elem)
                end = parse_point_text(end_elem)
                if not raw_points:
                    raw_points.append(start)
                raw_points.append(end)
            elif tag == "Curve":
                start_elem = child.find("landxml:Start", ns)
                end_elem = child.find("landxml:End", ns)
                center_elem = child.find("landxml:Center", ns)
                radius = child.get("radius")
                delta = child.get("delta")
                rotation = child.get("rot", "ccw").lower()
                if (
                    start_elem is None
                    or end_elem is None
                    or center_elem is None
                    or radius is None
                    or delta is None
                ):
                    continue
                start = parse_point_text(start_elem)
                end = parse_point_text(end_elem)
                center = parse_point_text(center_elem)
                radius_val = float(radius)
                delta_val = float(delta)
                arc_points = interpolate_arc_points(
                    center=center,
                    start=start,
                    end=end,
                    radius=radius_val,
                    delta_deg=delta_val,
                    rotation=rotation,
                    chord_tolerance=chord_tolerance,
                )
                if raw_points:
                    arc_points = arc_points[1:]
                raw_points.extend(arc_points)
            elif tag == "Spiral":
                start_elem = child.find("landxml:Start", ns)
                end_elem = child.find("landxml:End", ns)
                length_attr = child.get("length")
                if start_elem is None or end_elem is None:
                    continue
                start = parse_point_text(start_elem)
                end = parse_point_text(end_elem)
                length_val = float(length_attr) if length_attr else None
                spiral_points = interpolate_spiral_points(
                    start, end, length_val, chord_tolerance
                )
                if raw_points:
                    spiral_points = spiral_points[1:]
                raw_points.extend(spiral_points)
            else:
                # unsupported geometry type; skip gracefully
                continue

        filtered_points = decimate_duplicates(raw_points)
        alignment_points = cumulative_station(filtered_points, sta_start=sta_start)
        profile_pts = profiles.get(name) or profiles.get(alignment_elem.get("profileRef", ""))
        has_profile = bool(profile_pts)
        if profile_pts:
            apply_profile(alignment_points, profile_pts)

        alignments.append(
            AlignmentRecord(
                name=name,
                description=description,
                points=alignment_points,
                source_file=str(xml_path),
                has_vertical_profile=has_profile,
            )
        )

    return alignments, profiles, metadata


def build_transformer(source_epsg: str, target_epsg: str) -> Transformer:
    if not source_epsg:
        raise ValueError("Source EPSG must be provided (metadata missing and no override supplied).")
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)


def create_alignment_styles(alignment_names: Sequence[str]) -> str:
    style_snippets: List[str] = []
    for idx, name in enumerate(alignment_names):
        color = STYLE_COLORS[idx % len(STYLE_COLORS)]
        style_snippets.append(
            f"""
    <Style id="lineStyle_{idx}">
      <LineStyle>
        <color>{color}</color>
        <width>3</width>
      </LineStyle>
      <LabelStyle>
        <scale>0.8</scale>
      </LabelStyle>
    </Style>
"""
        )
    return "".join(style_snippets)


def create_kml_document(
    alignments: List[AlignmentRecord],
    transformer: Transformer,
    linear_unit: str,
    altitude_mode: str,
    clamp_elevations: bool,
    output_path: Path,
) -> None:
    linear_factor = LINEAR_UNITS_TO_METERS.get(linear_unit.lower(), 0.3048006096)
    style_block = create_alignment_styles([a.name for a in alignments])
    has_altitudes = not clamp_elevations and any(any(pt.z is not None for pt in al.points) for al in alignments)

    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        f"    <name>{output_path.name}</name>",
        style_block,
    ]

    for idx, alignment in enumerate(alignments):
        kml_parts.append("    <Folder>")
        kml_parts.append(f"      <name>{alignment.name}</name>")
        kml_parts.append("      <Placemark>")
        kml_parts.append(f"        <name>{alignment.name}</name>")
        desc_lines = [
            f"Source: {Path(alignment.source_file).name}",
            f"Description: {alignment.description or 'N/A'}",
            f"Profile: {'Yes' if alignment.has_vertical_profile else 'No'}",
            f"Points: {len(alignment.points)}",
            f"Length (ft): {alignment.total_length():.2f}",
        ]
        kml_parts.append("        <description><![CDATA[" + "<br/>".join(desc_lines) + "]]></description>")
        kml_parts.append(f"        <styleUrl>#lineStyle_{idx}</styleUrl>")
        kml_parts.append("        <LineString>")
        kml_parts.append("          <tessellate>1</tessellate>")
        kml_parts.append(f"          <altitudeMode>{altitude_mode if has_altitudes else 'clampToGround'}</altitudeMode>")
        kml_parts.append("          <coordinates>")
        for point in alignment.points:
            lon, lat = transformer.transform(point.x, point.y)
            if point.z is not None and has_altitudes:
                altitude = point.z * linear_factor
            else:
                altitude = 0.0
            kml_parts.append(f"            {lon:.8f},{lat:.8f},{altitude:.2f}")
        kml_parts.append("          </coordinates>")
        kml_parts.append("        </LineString>")
        kml_parts.append("      </Placemark>")
        kml_parts.append("    </Folder>")

    kml_parts.append("  </Document>")
    kml_parts.append("</kml>")

    output_path.write_text("\n".join(kml_parts), encoding="utf-8")
    print(f"Created KML file: {output_path}")


def summarize_alignments(
    xml_file: Path,
    alignments: List[AlignmentRecord],
    profiles: Dict[str, List[ProfileEntry]],
    metadata: Dict[str, str],
) -> Dict[str, object]:
    summary = {
        "xml_file": str(xml_file),
        "alignment_count": len(alignments),
        "metadata": metadata,
        "alignments": [],
    }
    for alignment in alignments:
        summary["alignments"].append(
            {
                "name": alignment.name,
                "description": alignment.description,
                "point_count": len(alignment.points),
                "has_profile": alignment.has_vertical_profile,
                "length": alignment.total_length(),
            }
        )
    summary["profile_keys"] = list(profiles.keys())
    return summary


def process_landxml_file(
    xml_file: Path,
    output_dir: Path,
    source_epsg_override: Optional[str],
    target_epsg: str,
    chord_tolerance: float,
    altitude_mode: str,
    clamp_elevations: bool,
    external_profiles: Optional[Dict[str, List[ProfileEntry]]] = None,
) -> Dict[str, object]:
    print(f"\nProcessing: {xml_file}")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ns = namespace_map(root)

    alignments, profiles, metadata = parse_alignments(
        xml_path=xml_file,
        chord_tolerance=chord_tolerance,
        ns=ns,
        extra_profiles=external_profiles,
    )

    if not alignments:
        raise ValueError(f"No alignments found in {xml_file}")

    detected_epsg = metadata.get("epsg")
    source_epsg = source_epsg_override or (f"EPSG:{detected_epsg}" if detected_epsg else None)
    transformer = build_transformer(source_epsg, target_epsg)
    linear_unit = metadata.get("linear_unit", "USSurveyFoot")
    output_file = output_dir / (xml_file.stem + ".kml")

    create_kml_document(
        alignments=alignments,
        transformer=transformer,
        linear_unit=linear_unit,
        altitude_mode=altitude_mode,
        clamp_elevations=clamp_elevations,
        output_path=output_file,
    )

    return summarize_alignments(xml_file, alignments, profiles, metadata)


def main():
    parser = argparse.ArgumentParser(
        description="Convert LandXML alignment files (with optional profile data) to KML.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="LandXML files to process. Defaults to all *.xml in DATA/ if not provided.",
    )
    parser.add_argument(
        "--data-dir",
        default="DATA",
        help="Directory to search when no explicit inputs are provided (default: DATA).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated KML files (defaults to same dir as each input).",
    )
    parser.add_argument(
        "--source-epsg",
        help="Override source EPSG code (e.g., EPSG:2871). If omitted, uses metadata from LandXML.",
    )
    parser.add_argument(
        "--target-epsg",
        default="EPSG:4326",
        help="Target EPSG for KML output (default: EPSG:4326/WGS84).",
    )
    parser.add_argument(
        "--arc-chord-tolerance",
        type=float,
        default=25.0,
        help="Maximum chord length (in source units) used when interpolating curves/spirals.",
    )
    parser.add_argument(
        "--altitude-mode",
        choices=["absolute", "relativeToGround", "clampToGround"],
        default="absolute",
        help="Altitude mode used when profiles are available (default: absolute).",
    )
    parser.add_argument(
        "--clamp-elevations",
        action="store_true",
        help="Force all alignments to clamp to ground (ignore profile elevations for visualization).",
    )
    parser.add_argument(
        "--summary-json",
        help="Write a JSON summary of the conversion results to this path.",
    )
    parser.add_argument(
        "--profile-library",
        action="append",
        help="Additional LandXML file(s) that contain Profile definitions to merge by alignment name.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    input_files = [Path(p) for p in args.inputs] if args.inputs else sorted(data_dir.glob("*.xml"))
    if not input_files:
        print("No LandXML files found.")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else None
    external_profiles: Dict[str, List[ProfileEntry]] = {}
    if args.profile_library:
        for library_path in args.profile_library:
            lib_path = Path(library_path)
            if not lib_path.exists():
                print(f"Warning: profile library not found: {library_path}")
                continue
            lib_profiles = load_profiles_from_file(lib_path)
            for key, entries in lib_profiles.items():
                external_profiles.setdefault(key, []).extend(entries)
    summaries = []
    for xml_file in input_files:
        if not xml_file.exists():
            print(f"Skipping missing file: {xml_file}")
            continue
        target_dir = output_dir or xml_file.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            summary = process_landxml_file(
                xml_file=xml_file,
                output_dir=target_dir,
                source_epsg_override=args.source_epsg,
                target_epsg=args.target_epsg,
                chord_tolerance=args.arc_chord_tolerance,
                altitude_mode=args.altitude_mode,
                clamp_elevations=args.clamp_elevations,
                external_profiles=external_profiles,
            )
            summaries.append(summary)
        except Exception as exc:  # pragma: no cover - user feedback
            print(f"ERROR processing {xml_file}: {exc}")

    if args.summary_json and summaries:
        Path(args.summary_json).write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        print(f"\nWrote summary to {args.summary_json}")


if __name__ == "__main__":
    main()
