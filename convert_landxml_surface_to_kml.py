#!/usr/bin/env python3
"""
Convert LandXML surface (TIN) definitions to KML meshes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
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

SURFACE_COLORS = [
    "80ff7043",
    "80ea4335",
    "80fbbc04",
    "804285f4",
    "8034a853",
    "809c27b0",
]


@dataclass
class SurfaceRecord:
    name: str
    points: Dict[int, Tuple[float, float, float]]
    faces: List[Tuple[int, int, int]]
    description: str = ""


def namespace_map(root: ET.Element) -> Dict[str, str]:
    ns = {"landxml": "http://www.landxml.org/schema/LandXML-1.2"}
    if root.tag.startswith("{"):
        uri = root.tag.split("}")[0].strip("{")
        ns["landxml"] = uri
    return ns


def parse_surface(surface_elem: ET.Element, ns: Dict[str, str]) -> SurfaceRecord | None:
    name = surface_elem.get("name", "Unnamed Surface")
    desc = surface_elem.get("desc", "")
    definition = surface_elem.find("landxml:Definition", ns)
    if definition is None:
        return None
    points_elem = definition.find("landxml:Pnts", ns)
    faces_elem = definition.find("landxml:Faces", ns)
    if points_elem is None or faces_elem is None:
        return None

    points: Dict[int, Tuple[float, float, float]] = {}
    for point_elem in points_elem.findall("landxml:P", ns):
        pid = point_elem.get("id")
        if not pid:
            continue
        coords = (point_elem.text or "").split()
        if len(coords) < 3:
            continue
        northing, easting, elevation = map(float, coords[:3])
        points[int(pid)] = (easting, northing, elevation)

    faces: List[Tuple[int, int, int]] = []
    for face_elem in faces_elem.findall("landxml:F", ns):
        parts = (face_elem.text or "").split()
        if len(parts) < 3:
            continue
        try:
            ids = tuple(int(p) for p in parts[:3])
        except ValueError:
            continue
        faces.append(ids)  # type: ignore[arg-type]

    if not points or not faces:
        return None
    return SurfaceRecord(name=name, description=desc, points=points, faces=faces)


def transformer_from_epsg(source_epsg: str | None, target_epsg: str) -> Transformer:
    if not source_epsg:
        raise ValueError("Source EPSG is required for surface conversion.")
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)


def build_surface_styles(surface_names: Iterable[str]) -> str:
    styles: List[str] = []
    for idx, _ in enumerate(surface_names):
        color = SURFACE_COLORS[idx % len(SURFACE_COLORS)]
        styles.append(
            f"""
    <Style id="surfaceStyle_{idx}">
      <LineStyle>
        <color>{color}</color>
        <width>1</width>
      </LineStyle>
      <PolyStyle>
        <color>{color}</color>
        <fill>1</fill>
        <outline>0</outline>
      </PolyStyle>
    </Style>
"""
        )
    return "".join(styles)


def create_surface_kml(
    surfaces: List[SurfaceRecord],
    transformer: Transformer,
    linear_factor: float,
    altitude_mode: str,
    clamp: bool,
    output_path: Path,
) -> None:
    def is_degenerate_triangle(verts: List[Tuple[float, float, float]]) -> bool:
        rounded = {(round(x, 6), round(y, 6)) for (x, y, _) in verts}
        if len(rounded) < 3:
            return True
        (x1, y1, _), (x2, y2, _), (x3, y3, _) = verts
        area2 = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        return area2 < 1e-2

    has_altitudes = not clamp
    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        f"    <name>{output_path.name}</name>",
        build_surface_styles(surface.name for surface in surfaces),
    ]

    for idx, surface in enumerate(surfaces):
        kml_parts.append("    <Folder>")
        kml_parts.append(f"      <name>{surface.name}</name>")
        kml_parts.append("      <Placemark>")
        kml_parts.append(f"        <name>{surface.name}</name>")
        kml_parts.append("        <description><![CDATA[Surface with "
                         f"{len(surface.points)} points / {len(surface.faces)} faces"
                         "]]></description>")
        kml_parts.append(f"        <styleUrl>#surfaceStyle_{idx}</styleUrl>")
        kml_parts.append("      </Placemark>")

        skipped = 0
        for face in surface.faces:
            verts = []
            missing = False
            for pid in face:
                if pid not in surface.points:
                    missing = True
                    break
                verts.append(surface.points[pid])
            if missing or len(verts) != 3:
                continue
            if is_degenerate_triangle(verts):
                skipped += 1
                continue
            coords_lines = []
            transformed_xy = []
            for (x, y, z) in verts:
                lon, lat = transformer.transform(x, y)
                altitude = 0.0 if clamp else z * linear_factor
                transformed_xy.append((lon, lat, altitude))
            unique_lonlat = {(round(lon, 8), round(lat, 8)) for lon, lat, _ in transformed_xy}
            if len(unique_lonlat) < 3:
                skipped += 1
                continue
            transformed_xy.append(transformed_xy[0])
            for lon, lat, altitude in transformed_xy:
                coords_lines.append(f"{lon:.8f},{lat:.8f},{altitude:.2f}")

            kml_parts.append("      <Placemark>")
            kml_parts.append("        <Polygon>")
            kml_parts.append(f"          <altitudeMode>{altitude_mode if has_altitudes else 'clampToGround'}</altitudeMode>")
            kml_parts.append("          <outerBoundaryIs>")
            kml_parts.append("            <LinearRing>")
            kml_parts.append("              <coordinates>")
            for coord in coords_lines:
                kml_parts.append(f"                {coord}")
            kml_parts.append("              </coordinates>")
            kml_parts.append("            </LinearRing>")
            kml_parts.append("          </outerBoundaryIs>")
            kml_parts.append("        </Polygon>")
            kml_parts.append("      </Placemark>")

        kml_parts.append("    </Folder>")
        if skipped:
            print(f"  Skipped {skipped} degenerate triangles in surface '{surface.name}'.")

    kml_parts.append("  </Document>")
    kml_parts.append("</kml>")
    output_path.write_text("\n".join(kml_parts), encoding="utf-8")
    print(f"Created KML file: {output_path}")


def summarize_surfaces(xml_file: Path, surfaces: List[SurfaceRecord], metadata: Dict[str, str]) -> Dict[str, object]:
    summary = {
        "xml_file": str(xml_file),
        "surface_count": len(surfaces),
        "metadata": metadata,
        "surfaces": [],
    }
    for surface in surfaces:
        elevs = [pt[2] for pt in surface.points.values()]
        summary["surfaces"].append(
            {
                "name": surface.name,
                "description": surface.description,
                "point_count": len(surface.points),
                "face_count": len(surface.faces),
                "elevation_min": min(elevs) if elevs else None,
                "elevation_max": max(elevs) if elevs else None,
            }
        )
    return summary


def process_landxml_surface_file(
    xml_file: Path,
    output_dir: Path,
    target_epsg: str,
    clamp: bool,
    altitude_mode: str,
) -> Dict[str, object]:
    root = ET.parse(xml_file).getroot()
    ns = namespace_map(root)

    surfaces: List[SurfaceRecord] = []
    for surface_elem in root.findall(".//landxml:Surface", ns):
        record = parse_surface(surface_elem, ns)
        if record:
            surfaces.append(record)

    if not surfaces:
        raise ValueError("No surfaces with TIN data found.")

    units_elem = root.find(".//landxml:Units/landxml:Imperial", ns)
    linear_unit = units_elem.get("linearUnit", "USSurveyFoot") if units_elem is not None else "USSurveyFoot"
    coord_sys = root.find(".//landxml:CoordinateSystem", ns)
    epsg_code = coord_sys.get("epsgCode", "") if coord_sys is not None else ""
    source_epsg = f"EPSG:{epsg_code}" if epsg_code else None
    transformer = transformer_from_epsg(source_epsg, target_epsg)
    linear_factor = LINEAR_UNITS_TO_METERS.get(linear_unit.lower(), 0.3048006096)

    output_file = output_dir / (xml_file.stem + "_surface.kml")
    create_surface_kml(
        surfaces=surfaces,
        transformer=transformer,
        linear_factor=linear_factor,
        altitude_mode=altitude_mode,
        clamp=clamp,
        output_path=output_file,
    )

    metadata = {"epsg": epsg_code, "linear_unit": linear_unit}
    return summarize_surfaces(xml_file, surfaces, metadata)


def main():
    parser = argparse.ArgumentParser(description="Convert LandXML surface (TIN) definitions to KML.")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="LandXML files to process. Defaults to all *.xml in DATA/ if omitted.",
    )
    parser.add_argument(
        "--data-dir",
        default="DATA",
        help="Directory scanned when no input paths are provided (default: DATA).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated KML files (default: alongside input file).",
    )
    parser.add_argument(
        "--target-epsg",
        default="EPSG:4326",
        help="EPSG code for KML output coordinates (default: EPSG:4326).",
    )
    parser.add_argument(
        "--altitude-mode",
        choices=["absolute", "relativeToGround", "clampToGround"],
        default="absolute",
        help="Altitude mode for polygons (default: absolute).",
    )
    parser.add_argument(
        "--clamp-elevations",
        action="store_true",
        help="Clamp all surface polygons to ground (ignore TIN elevations).",
    )
    parser.add_argument(
        "--summary-json",
        help="Write a JSON array summarizing each processed file.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    input_files = [Path(p) for p in args.inputs] if args.inputs else sorted(data_dir.glob("*.xml"))
    if not input_files:
        print("No LandXML files found.")
        return

    output_dir = Path(args.output_dir) if args.output_dir else None
    summaries = []
    for xml_file in input_files:
        if not xml_file.exists():
            print(f"Skipping missing file: {xml_file}")
            continue
        target_dir = output_dir or xml_file.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            summary = process_landxml_surface_file(
                xml_file=xml_file,
                output_dir=target_dir,
                target_epsg=args.target_epsg,
                clamp=args.clamp_elevations,
                altitude_mode=args.altitude_mode,
            )
            summaries.append(summary)
        except Exception as exc:
            print(f"ERROR processing {xml_file}: {exc}")

    if args.summary_json and summaries:
        Path(args.summary_json).write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        print(f"Wrote summary to {args.summary_json}")


if __name__ == "__main__":
    main()
