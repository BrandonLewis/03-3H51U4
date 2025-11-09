#!/usr/bin/env python3
"""
Convert IFC models to KML with configurable CRS, altitude handling, and summary output.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import ifcopenshell
import ifcopenshell.geom
from pyproj import Transformer

DEFAULT_SOURCE_EPSG = "EPSG:2767"  # CA State Plane Zone II (meters)
DEFAULT_TARGET_EPSG = "EPSG:4326"


def setup_ifc_settings() -> ifcopenshell.geom.settings:
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    settings.set(settings.WELD_VERTICES, False)
    return settings


def build_transformer(source_epsg: str, target_epsg: str) -> Transformer:
    if not source_epsg:
        raise ValueError("Source EPSG must be specified.")
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)


def gather_properties(ifc) -> Dict[int, Dict[str, str]]:
    prop_map: Dict[int, Dict[str, str]] = defaultdict(dict)
    for rel in ifc.by_type("IfcRelDefinesByProperties"):
        pset = rel.RelatingPropertyDefinition
        props = getattr(pset, "HasProperties", []) if pset else []
        for obj in rel.RelatedObjects:
            entry = prop_map[obj.id()]
            for prop in props:
                name = getattr(prop, "Name", "")
                nominal = getattr(prop, "NominalValue", None)
                if not name or nominal is None:
                    continue
                value = nominal.wrappedValue if hasattr(nominal, "wrappedValue") else str(nominal)
                entry[name] = value
    return prop_map


def extract_property_points(
    ifc,
    prop_map: Dict[int, Dict[str, str]],
    map_conv: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    result = []
    names = {"Start Point", "StartPoint"}
    for rel in ifc.by_type("IfcRelDefinesByProperties"):
        pset = rel.RelatingPropertyDefinition
        props = getattr(pset, "HasProperties", [])
        coords = None
        for prop in props:
            if getattr(prop, "Name", "") in names:
                nominal = getattr(prop, "NominalValue", None)
                if nominal is None:
                    continue
                value = nominal.wrappedValue if hasattr(nominal, "wrappedValue") else str(nominal)
                try:
                    coords = [float(x.strip()) for x in value.split(",")]
                except ValueError:
                    coords = None
                break
        if coords is None or len(coords) < 3:
            continue
        for obj in rel.RelatedObjects:
            props = prop_map.get(obj.id(), {})
            station = props.get("Station", "")
            feature_name = props.get("Feature Name", "")
            if station:
                name = f"Sta {station}"
            elif feature_name:
                name = feature_name
            else:
                name = getattr(obj, "Name", obj.is_a())
            coord_tuple = tuple(coords[:3])
            if map_conv:
                coord_tuple = apply_map_conversion(coord_tuple, map_conv)
            result.append(
                {
                    "name": name,
                    "type": obj.is_a(),
                    "coords": coord_tuple,
                    "station": station,
                    "properties": props,
                }
            )
    return result


def get_map_conversion(ifc) -> Tuple[Optional[Dict[str, float]], Dict[str, str]]:
    for ctx in ifc.by_type("IfcGeometricRepresentationContext"):
        operations = getattr(ctx, "HasCoordinateOperation", None) or []
        for op in operations:
            if not op.is_a("IfcMapConversion"):
                continue
            target = getattr(op, "TargetCRS", None)
            info = {
                "target_crs_name": getattr(target, "Name", "") if target else "",
                "target_crs_description": getattr(target, "Description", "") if target else "",
            }
            params = {
                "eastings": getattr(op, "Eastings", 0.0) or 0.0,
                "northings": getattr(op, "Northings", 0.0) or 0.0,
                "orthogonal_height": getattr(op, "OrthogonalHeight", 0.0) or 0.0,
                "xaxis_abscissa": getattr(op, "XAxisAbscissa", 1.0) or 1.0,
                "xaxis_ordinate": getattr(op, "XAxisOrdinate", 0.0) or 0.0,
                "scale": getattr(op, "Scale", 1.0) or 1.0,
            }
            return params, info
    return None, {}


def apply_map_conversion(coord: Tuple[float, float, float], params: Dict[str, float]) -> Tuple[float, float, float]:
    x, y, z = coord
    east = params["eastings"]
    north = params["northings"]
    height = params["orthogonal_height"]
    scale = params["scale"]
    x_axis = params["xaxis_abscissa"]
    y_axis = params["xaxis_ordinate"]
    norm = math.hypot(x_axis, y_axis)
    if norm < 1e-9:
        cos_val, sin_val = 1.0, 0.0
    else:
        cos_val = x_axis / norm
        sin_val = y_axis / norm
    map_x = east + scale * (cos_val * x - sin_val * y)
    map_y = north + scale * (sin_val * x + cos_val * y)
    map_z = height + z
    return map_x, map_y, map_z


def extract_geometry(
    ifc_path: Path,
    transformer: Transformer,
    altitude_mode: str,
    clamp_elevations: bool,
    filter_types: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, float], Dict[str, List[Dict]], Dict[str, str]]:
    ifc = ifcopenshell.open(str(ifc_path))
    settings = setup_ifc_settings()
    prop_map = gather_properties(ifc)
    map_conv_params, map_info = get_map_conversion(ifc)

    geometry = {"lines": [], "points": [], "polygons": []}

    property_points = extract_property_points(ifc, prop_map, map_conv_params)
    if property_points:
        geometry["points"].extend(property_points)

    filter_set = {ft.lower() for ft in filter_types} if filter_types else None

    products = ifc.by_type("IfcProduct")
    for product in products:
        type_name = product.is_a()
        if filter_set and type_name.lower() not in filter_set:
            continue
        if not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception:
            continue
        geom = shape.geometry
        verts = geom.verts
        faces = geom.faces
        edges = geom.edges
        vertices = [(verts[i], verts[i + 1], verts[i + 2]) for i in range(0, len(verts), 3)]
        if map_conv_params:
            vertices = [apply_map_conversion(v, map_conv_params) for v in vertices]

        if edges:
            for i in range(0, len(edges), 2):
                if i + 1 >= len(edges):
                    break
                v1_idx, v2_idx = edges[i], edges[i + 1]
                if v1_idx >= len(vertices) or v2_idx >= len(vertices):
                    continue
                geometry["lines"].append(
                    {
                        "name": getattr(product, "Name", type_name),
                        "type": type_name,
                        "points": [vertices[v1_idx], vertices[v2_idx]],
                    }
                )

        if faces and len(faces) >= 3:
            for i in range(0, len(faces), 3):
                if i + 2 >= len(faces):
                    break
                idxs = [faces[i], faces[i + 1], faces[i + 2]]
                if any(idx >= len(vertices) for idx in idxs):
                    continue
                triangle = [vertices[idx] for idx in idxs]
                geometry["polygons"].append(
                    {
                        "name": getattr(product, "Name", type_name),
                        "type": type_name,
                        "points": triangle,
                    }
                )

        if not edges and not faces and vertices:
            for v in vertices:
                geometry["points"].append(
                    {"name": getattr(product, "Name", type_name), "type": type_name, "coords": v}
                )

    counts = {k: len(v) for k, v in geometry.items()}
    project = ifc.by_type("IfcProject")
    project_name = project[0].Name if project else ifc_path.stem
    counts["project_name"] = project_name
    counts["map_conversion_applied"] = bool(map_conv_params)
    if map_info:
        counts["map_conversion"] = map_info
    return counts, geometry, map_info


def transform_coords(
    coords: Tuple[float, float, float],
    transformer: Transformer,
    clamp: bool,
) -> Tuple[float, float, float]:
    lon, lat = transformer.transform(coords[0], coords[1])
    altitude = 0.0 if clamp else coords[2]
    return lon, lat, altitude


def create_kml(
    geometry: Dict[str, List[Dict]],
    output_path: Path,
    transformer: Transformer,
    altitude_mode: str,
    clamp_elevations: bool,
) -> None:
    has_altitudes = not clamp_elevations
    doc_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        f"    <name>{output_path.stem}</name>",
        "    <Style id=\"lineStyle\"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle></Style>",
        "    <Style id=\"pointStyle\"><IconStyle><color>ff0000ff</color><scale>0.8</scale>"
        "<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>"
        "</IconStyle><LabelStyle><scale>0.6</scale></LabelStyle></Style>",
        "    <Style id=\"polyStyle\"><LineStyle><color>8000ffff</color></LineStyle>"
        "<PolyStyle><color>4000ffff</color></PolyStyle></Style>",
    ]

    def grouped_folders(entries: List[Dict], folder_name: str, builder):
        if not entries:
            return
        doc_lines.append(f"    <Folder><name>{folder_name}</name>")
        grouped = defaultdict(list)
        for entry in entries:
            grouped[entry["type"]].append(entry)
        for type_name, bucket in grouped.items():
            doc_lines.append(f"      <Folder><name>{type_name}</name>")
            for item in bucket:
                builder(item, doc_lines)
            doc_lines.append("      </Folder>")
        doc_lines.append("    </Folder>")

    def build_line(line, lines_out):
        coords = []
        for point in line["points"]:
            lon, lat, alt = transform_coords(point, transformer, clamp_elevations)
            coords.append(f"{lon:.8f},{lat:.8f},{alt:.2f}")
        lines_out.extend(
            [
                "        <Placemark>",
                f"          <name>{line['name']}</name>",
                "          <styleUrl>#lineStyle</styleUrl>",
                "          <LineString>",
                "            <tessellate>1</tessellate>",
                f"            <altitudeMode>{altitude_mode if has_altitudes else 'clampToGround'}</altitudeMode>",
                "            <coordinates>",
                "              " + " ".join(coords),
                "            </coordinates>",
                "          </LineString>",
                "        </Placemark>",
            ]
        )

    def build_point(point, lines_out):
        lon, lat, alt = transform_coords(point["coords"], transformer, clamp_elevations)
        props = point.get("properties", {})
        desc_lines = [f"Type: {point['type']}"]
        for key, value in props.items():
            desc_lines.append(f"{key}: {value}")
        lines_out.extend(
            [
                "        <Placemark>",
                f"          <name>{point['name']}</name>",
                f"          <description><![CDATA[{'<br/>'.join(desc_lines)}]]></description>",
                "          <styleUrl>#pointStyle</styleUrl>",
                "          <Point>",
                f"            <altitudeMode>{altitude_mode if has_altitudes else 'clampToGround'}</altitudeMode>",
                f"            <coordinates>{lon:.8f},{lat:.8f},{alt:.2f}</coordinates>",
                "          </Point>",
                "        </Placemark>",
            ]
        )

    def build_polygon(poly, lines_out):
        coords_lines = []
        transformed = [transform_coords(p, transformer, clamp_elevations) for p in poly["points"]]
        transformed.append(transformed[0])
        for lon, lat, alt in transformed:
            coords_lines.append(f"{lon:.8f},{lat:.8f},{alt:.2f}")
        lines_out.extend(
            [
                "        <Placemark>",
                f"          <name>{poly['name']}</name>",
                "          <styleUrl>#polyStyle</styleUrl>",
                "          <Polygon>",
                f"            <altitudeMode>{altitude_mode if has_altitudes else 'clampToGround'}</altitudeMode>",
                "            <outerBoundaryIs>",
                "              <LinearRing>",
                "                <coordinates>",
                "                  " + " ".join(coords_lines),
                "                </coordinates>",
                "              </LinearRing>",
                "            </outerBoundaryIs>",
                "          </Polygon>",
                "        </Placemark>",
            ]
        )

    grouped_folders(geometry["lines"], "Lines", build_line)
    grouped_folders(geometry["points"], "Points", build_point)
    grouped_folders(geometry["polygons"], "Polygons", build_polygon)

    doc_lines.append("  </Document></kml>")
    output_path.write_text("\n".join(doc_lines), encoding="utf-8")
    print(f"Created KML file: {output_path}")


def process_ifc_file(
    ifc_file: Path,
    output_dir: Path,
    transformer: Transformer,
    altitude_mode: str,
    clamp_elevations: bool,
    filter_types: Optional[Sequence[str]],
) -> Dict[str, object]:
    summary, geometry, map_info = extract_geometry(
        ifc_file,
        transformer=transformer,
        altitude_mode=altitude_mode,
        clamp_elevations=clamp_elevations,
        filter_types=filter_types,
    )
    output_path = output_dir / f"{ifc_file.stem}.kml"
    create_kml(
        geometry,
        output_path=output_path,
        transformer=transformer,
        altitude_mode=altitude_mode,
        clamp_elevations=clamp_elevations,
    )
    summary["output"] = str(output_path)
    summary["ifc_file"] = str(ifc_file)
    if map_info:
        summary.setdefault("map_conversion", map_info)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert IFC files to KML.")
    parser.add_argument("inputs", nargs="*", help="IFC files to convert. Defaults to all *.ifc in DATA/.")
    parser.add_argument("--data-dir", default="DATA", help="Directory scanned when no inputs are provided.")
    parser.add_argument("--output-dir", default=None, help="Directory for generated KML files.")
    parser.add_argument("--source-epsg", default=DEFAULT_SOURCE_EPSG, help="Source EPSG code (default: EPSG:2767).")
    parser.add_argument("--target-epsg", default=DEFAULT_TARGET_EPSG, help="Target EPSG (default: EPSG:4326).")
    parser.add_argument(
        "--altitude-mode",
        choices=["absolute", "relativeToGround", "clampToGround"],
        default="absolute",
        help="Altitude mode for KML geometries.",
    )
    parser.add_argument("--clamp-elevations", action="store_true", help="Clamp all geometries to ground (z=0).")
    parser.add_argument(
        "--filter-types",
        nargs="+",
        help="Limit export to specific IFC entity types (e.g., IfcWall, IfcSlab).",
    )
    parser.add_argument("--summary-json", help="Write conversion summary to this JSON file.")
    return parser.parse_args()


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    ifc_files = [Path(p) for p in args.inputs] if args.inputs else sorted(data_dir.glob("*.ifc"))
    if not ifc_files:
        print("No IFC files found.")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else None
    transformer = build_transformer(args.source_epsg, args.target_epsg)

    summaries = []
    for ifc_file in ifc_files:
        if not ifc_file.exists():
            print(f"Skipping missing file: {ifc_file}")
            continue
        target_dir = output_dir or ifc_file.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            summary = process_ifc_file(
                ifc_file=ifc_file,
                output_dir=target_dir,
                transformer=transformer,
                altitude_mode=args.altitude_mode,
                clamp_elevations=args.clamp_elevations,
                filter_types=args.filter_types,
            )
            summaries.append(summary)
        except Exception as exc:  # pragma: no cover
            print(f"ERROR processing {ifc_file}: {exc}")

    if args.summary_json and summaries:
        Path(args.summary_json).write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        print(f"Wrote summary to {args.summary_json}")


if __name__ == "__main__":
    main()
