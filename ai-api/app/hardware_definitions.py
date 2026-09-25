from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import PurePosixPath
from typing import Any

import sexpdata


MAX_DEFINITION_BYTES = 4 * 1024 * 1024
MAX_BUNDLE_EXPANDED_BYTES = 12 * 1024 * 1024


class DefinitionError(ValueError):
    pass


def _text(element: ET.Element | None, name: str, default: str = "") -> str:
    if element is None:
        return default
    child = element.find(f"{{*}}{name}")
    return (child.text or default).strip() if child is not None else default


def _integer(value: str) -> int | None:
    try:
        return int(value.strip(), 0)
    except (TypeError, ValueError):
        return None


def import_cmsis_svd(content: str, source_name: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise DefinitionError(f"Invalid CMSIS-SVD XML: {error}") from error
    if root.tag.split("}")[-1] != "device":
        raise DefinitionError("CMSIS-SVD root element must be device")
    cpu = root.find("{*}cpu")
    peripherals = []
    for peripheral in root.findall(".//{*}peripherals/{*}peripheral")[:4096]:
        registers = []
        for register in peripheral.findall(".//{*}registers/{*}register")[:8192]:
            fields = []
            for field in register.findall(".//{*}fields/{*}field")[:512]:
                fields.append({
                    "name": _text(field, "name"),
                    "description": _text(field, "description"),
                    "bit_offset": _integer(_text(field, "bitOffset")),
                    "bit_width": _integer(_text(field, "bitWidth")),
                    "access": _text(field, "access") or None,
                })
            registers.append({
                "name": _text(register, "name"),
                "description": _text(register, "description"),
                "address_offset": _integer(_text(register, "addressOffset")),
                "size": _integer(_text(register, "size")),
                "access": _text(register, "access") or None,
                "reset_value": _integer(_text(register, "resetValue")),
                "fields": fields,
            })
        interrupts = [
            {"name": _text(item, "name"), "value": _integer(_text(item, "value"))}
            for item in peripheral.findall("{*}interrupt")
        ]
        peripherals.append({
            "name": _text(peripheral, "name"),
            "description": _text(peripheral, "description"),
            "base_address": _integer(_text(peripheral, "baseAddress")),
            "interrupts": interrupts,
            "registers": registers,
        })
    if not peripherals:
        raise DefinitionError("CMSIS-SVD contains no peripherals")
    return {
        "format": "cmsis-svd",
        "scope": "mcu_internal",
        "source_name": source_name,
        "source_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "device": _text(root, "name"),
        "vendor": _text(root, "vendor"),
        "description": _text(root, "description"),
        "cpu": {"name": _text(cpu, "name"), "revision": _text(cpu, "revision"), "endian": _text(cpu, "endian")},
        "peripherals": peripherals,
        "counts": {
            "peripherals": len(peripherals),
            "registers": sum(len(item["registers"]) for item in peripherals),
            "fields": sum(len(register["fields"]) for item in peripherals for register in item["registers"]),
            "interrupts": sum(len(item["interrupts"]) for item in peripherals),
        },
        "provenance": {"kind": "uploaded_definition", "confidence": "definition_exact"},
    }


_DTS_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_DTS_NODE = re.compile(r"(?:(?P<label>[A-Za-z_][\w-]*)\s*:\s*)?(?P<name>[A-Za-z_][\w,.-]*)(?:@(?P<unit>[0-9A-Fa-f]+))?\s*\{")
_DTS_PROPERTY = re.compile(r"^\s*(?P<name>[#A-Za-z_][\w,#.+-]*)\s*(?:=\s*(?P<value>.*?))?;\s*$", re.DOTALL)


def _property_value(value: str | None) -> Any:
    if value is None:
        return True
    strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', value)
    if strings:
        return strings[0] if len(strings) == 1 else strings
    cells = re.findall(r"(?:0x[0-9A-Fa-f]+|\b\d+\b|&[A-Za-z_][\w-]*)", value)
    if cells:
        parsed: list[Any] = []
        for cell in cells:
            parsed.append(_integer(cell) if not cell.startswith("&") else cell)
        return parsed[0] if len(parsed) == 1 else parsed
    return value.strip()


def _brace_pairs(source: str) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stack: list[int] = []
    quoted = False
    escaped = False
    for index, character in enumerate(source):
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            stack.append(index)
        elif character == "}":
            if not stack:
                raise DefinitionError("DeviceTree has an unmatched closing brace")
            pairs[stack.pop()] = index
    if stack:
        raise DefinitionError("DeviceTree has an unclosed node")
    return pairs


def _direct_properties(body: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    depth = 0
    quoted = False
    escaped = False
    segment_start = 0
    for index, character in enumerate(body):
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif character == ";" and depth == 0:
            segment = body[segment_start:index + 1]
            segment_start = index + 1
            match = _DTS_PROPERTY.fullmatch(segment)
            if match:
                properties[match.group("name")] = _property_value(match.group("value"))
    return properties


def import_zephyr_devicetree(content: str, source_name: str) -> dict[str, Any]:
    """Import preprocessed Zephyr DTS (normally build/zephyr/zephyr.dts), preserving references as evidence."""
    source = _DTS_COMMENT.sub("", content)
    brace_pairs = _brace_pairs(source)
    nodes: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    for match in _DTS_NODE.finditer(source):
        opening = match.end() - 1
        closing = brace_pairs.get(opening)
        if closing is None:
            raise DefinitionError(f"Unclosed DeviceTree node {match.group('name')}")
        while stack and match.start() > stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else "/"
        name = match.group("name")
        unit = match.group("unit")
        path = f"{parent.rstrip('/')}/{name}{f'@{unit}' if unit else ''}"
        body = source[match.end():closing]
        properties = _direct_properties(body)
        nodes.append({
            "path": path,
            "name": name,
            "unit_address": unit,
            "label": match.group("label"),
            "compatible": properties.get("compatible"),
            "status": properties.get("status", "okay"),
            "properties": properties,
        })
        stack.append((closing, path))
        if len(nodes) >= 8192:
            break
    meaningful = [node for node in nodes if node["name"] not in {"dts-v1", "plugin"}]
    if not meaningful:
        raise DefinitionError("Zephyr DeviceTree contains no parseable nodes")
    buses = [node for node in meaningful if any(token in node["name"].lower() for token in ("i2c", "spi", "uart", "serial"))]
    components = [node for node in meaningful if node.get("compatible")]
    return {
        "format": "zephyr-devicetree",
        "scope": "board_topology",
        "source_name": source_name,
        "source_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "nodes": meaningful,
        "components": components,
        "buses": buses,
        "counts": {"nodes": len(meaningful), "components": len(components), "buses": len(buses)},
        "provenance": {"kind": "uploaded_definition", "confidence": "definition_exact"},
        "limitations": ["Use Zephyr's preprocessed build/zephyr/zephyr.dts so includes and macros are already resolved."],
    }


def _sexp_name(value: Any) -> str:
    if isinstance(value, sexpdata.Symbol):
        return value.value()
    return str(value)


def _sexp_head(value: Any) -> str:
    return _sexp_name(value[0]) if isinstance(value, list) and value else ""


def _sexp_children(value: list[Any], name: str) -> list[list[Any]]:
    return [item for item in value[1:] if isinstance(item, list) and _sexp_head(item) == name]


def _sexp_scalar(value: list[Any], name: str, default: Any = None) -> Any:
    children = _sexp_children(value, name)
    return children[0][1] if children and len(children[0]) > 1 else default


def _sexp_point(value: list[Any]) -> list[float] | None:
    if _sexp_head(value) != "xy" or len(value) < 3:
        return None
    try:
        return [float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def import_kicad_schematic(content: str, source_name: str) -> dict[str, Any]:
    """Import KiCad's native S-expression schematic as design evidence."""
    try:
        root = sexpdata.loads(content)
    except Exception as error:
        raise DefinitionError(f"Invalid KiCad schematic: {error}") from error
    if not isinstance(root, list) or _sexp_head(root) != "kicad_sch":
        raise DefinitionError("KiCad schematic root must be kicad_sch")

    components: list[dict[str, Any]] = []
    for symbol in _sexp_children(root, "symbol")[:8192]:
        properties = {
            str(item[1]): str(item[2])
            for item in _sexp_children(symbol, "property")
            if len(item) >= 3
        }
        pins = [str(pin[1]) for pin in _sexp_children(symbol, "pin") if len(pin) > 1]
        components.append({
            "reference": properties.get("Reference", ""),
            "value": properties.get("Value", ""),
            "lib_id": str(_sexp_scalar(symbol, "lib_id", "")),
            "footprint": properties.get("Footprint", ""),
            "datasheet": properties.get("Datasheet", ""),
            "unit": _sexp_scalar(symbol, "unit"),
            "uuid": str(_sexp_scalar(symbol, "uuid", "")),
            "pins": pins,
        })

    wires: list[dict[str, Any]] = []
    for wire in _sexp_children(root, "wire")[:32768]:
        points: list[list[float]] = []
        pts = _sexp_children(wire, "pts")
        if pts:
            points = [point for item in pts[0][1:] if isinstance(item, list) and (point := _sexp_point(item))]
        wires.append({"uuid": str(_sexp_scalar(wire, "uuid", "")), "points": points})

    labels: list[dict[str, Any]] = []
    for kind in ("label", "global_label", "hierarchical_label"):
        for label in _sexp_children(root, kind)[:8192]:
            labels.append({
                "kind": kind,
                "name": str(label[1]) if len(label) > 1 else "",
                "uuid": str(_sexp_scalar(label, "uuid", "")),
            })

    junction_count = len(_sexp_children(root, "junction"))
    no_connect_count = len(_sexp_children(root, "no_connect"))
    if not components and not wires and not labels:
        raise DefinitionError("KiCad schematic contains no component, wire, or label evidence")
    return {
        "format": "kicad-schematic",
        "scope": "design_evidence",
        "source_name": source_name,
        "source_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "version": _sexp_scalar(root, "version"),
        "generator": str(_sexp_scalar(root, "generator", "")),
        "components": components,
        "wires": wires,
        "labels": labels,
        "counts": {
            "components": len(components),
            "pins": sum(len(item["pins"]) for item in components),
            "wires": len(wires),
            "labels": len(labels),
            "junctions": junction_count,
            "no_connects": no_connect_count,
        },
        "provenance": {"kind": "uploaded_design", "confidence": "definition_exact"},
        "limitations": [
            "A schematic describes intended design, not proof of components present on live hardware.",
            "Full hierarchy, net resolution, and electrical-rule checks remain the responsibility of KiCad.",
        ],
    }


def _xml_local(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in list(element) if child.tag.split("}")[-1] == name), None)


def import_fritzing_part(content: str, source_name: str) -> dict[str, Any]:
    """Import an unpacked Fritzing .fzp part definition without executing SVG or code."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise DefinitionError(f"Invalid Fritzing part XML: {error}") from error
    if root.tag.split("}")[-1] != "module":
        raise DefinitionError("Fritzing part root element must be module")

    properties: dict[str, str] = {}
    properties_node = _xml_local(root, "properties")
    if properties_node is not None:
        for item in list(properties_node):
            if item.tag.split("}")[-1] == "property" and item.get("name"):
                properties[item.get("name", "")] = (item.text or "").strip()

    connectors: list[dict[str, Any]] = []
    connectors_node = _xml_local(root, "connectors")
    if connectors_node is not None:
        for connector in list(connectors_node)[:8192]:
            if connector.tag.split("}")[-1] != "connector":
                continue
            connector_views = _xml_local(connector, "views")
            view_bindings: dict[str, dict[str, str]] = {}
            if connector_views is not None:
                for view in list(connector_views):
                    binding = next((child for child in list(view) if child.tag.split("}")[-1] == "p"), None)
                    if binding is not None:
                        view_bindings[view.tag.split("}")[-1]] = {
                            key: value for key, value in binding.attrib.items() if key in {"svgId", "terminalId", "layer"}
                        }
            connectors.append({
                "id": connector.get("id", ""),
                "name": connector.get("name", ""),
                "type": connector.get("type", "unknown"),
                "description": (_xml_local(connector, "description").text or "").strip() if _xml_local(connector, "description") is not None else "",
                "views": view_bindings,
            })

    views: dict[str, dict[str, str]] = {}
    views_node = _xml_local(root, "views")
    if views_node is not None:
        for view in list(views_node):
            layers = next((child for child in list(view) if child.tag.split("}")[-1] == "layers"), None)
            if layers is not None:
                views[view.tag.split("}")[-1]] = {"image": layers.get("image", "")}

    buses: list[dict[str, Any]] = []
    buses_node = _xml_local(root, "buses")
    if buses_node is not None:
        for bus in list(buses_node)[:4096]:
            members = []
            for node_member in list(bus):
                if node_member.tag.split("}")[-1] == "nodeMember" and node_member.get("connectorId"):
                    members.append(node_member.get("connectorId"))
            buses.append({"id": bus.get("id", ""), "members": members})

    if not connectors:
        raise DefinitionError("Fritzing part contains no connectors")
    return {
        "format": "fritzing-part",
        "scope": "component_definition",
        "source_name": source_name,
        "source_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "module_id": root.get("moduleId", ""),
        "title": (_xml_local(root, "title").text or "").strip() if _xml_local(root, "title") is not None else "",
        "label": (_xml_local(root, "label").text or "").strip() if _xml_local(root, "label") is not None else "",
        "version": (_xml_local(root, "version").text or "").strip() if _xml_local(root, "version") is not None else "",
        "author": (_xml_local(root, "author").text or "").strip() if _xml_local(root, "author") is not None else "",
        "taxonomy": (_xml_local(root, "taxonomy").text or "").strip() if _xml_local(root, "taxonomy") is not None else "",
        "properties": properties,
        "connectors": connectors,
        "views": views,
        "buses": buses,
        "counts": {"connectors": len(connectors), "views": len(views), "buses": len(buses)},
        "provenance": {"kind": "uploaded_part_definition", "confidence": "definition_exact"},
        "limitations": [
            "The .fzp file describes a catalog part and connector-to-SVG bindings; referenced SVG assets are not embedded in this import.",
            "A Fritzing part definition is design/catalog evidence, not proof that the part is physically connected.",
        ],
    }


def _sanitize_svg(content: bytes, asset_name: str) -> str:
    if len(content) > MAX_DEFINITION_BYTES:
        raise DefinitionError(f"Fritzing SVG asset is too large: {asset_name}")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise DefinitionError(f"Invalid Fritzing SVG asset {asset_name}: {error}") from error
    if root.tag.split("}")[-1] != "svg":
        raise DefinitionError(f"Fritzing visual asset is not SVG: {asset_name}")
    blocked = {"script", "foreignObject", "iframe", "object", "embed"}
    for parent in root.iter():
        for child in list(parent):
            if child.tag.split("}")[-1] in blocked:
                parent.remove(child)
        for attribute in list(parent.attrib):
            local = attribute.split("}")[-1].lower()
            value = parent.attrib[attribute].strip()
            if local.startswith("on") or (local in {"href", "src"} and value and not value.startswith("#")):
                del parent.attrib[attribute]
            elif "url(" in value.lower() and "url(#" not in value.lower():
                del parent.attrib[attribute]
        if parent.tag.split("}")[-1] == "style" and parent.text:
            parent.text = re.sub(r"@import\s+[^;]+;?", "", parent.text, flags=re.IGNORECASE)
            parent.text = re.sub(r"url\((?!\s*#)[^)]+\)", "", parent.text, flags=re.IGNORECASE)
    return ET.tostring(root, encoding="unicode")


def import_fritzing_bundle(content_base64: str, source_name: str) -> dict[str, Any]:
    try:
        payload = base64.b64decode(content_base64, validate=True)
    except binascii.Error as error:
        raise DefinitionError("Fritzing bundle content is not valid base64") from error
    if len(payload) > MAX_DEFINITION_BYTES:
        raise DefinitionError("Fritzing bundle exceeds the 4 MiB compressed limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as error:
        raise DefinitionError("Fritzing bundle is not a valid ZIP archive") from error
    with archive:
        members = archive.infolist()
        if len(members) > 128:
            raise DefinitionError("Fritzing bundle contains too many files")
        total = 0
        normalized: dict[str, zipfile.ZipInfo] = {}
        for member in members:
            path = PurePosixPath(member.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
                raise DefinitionError("Fritzing bundle contains an unsafe path")
            total += member.file_size
            if total > MAX_BUNDLE_EXPANDED_BYTES:
                raise DefinitionError("Fritzing bundle exceeds the 12 MiB expanded limit")
            if member.compress_size and member.file_size > member.compress_size * 200:
                raise DefinitionError("Fritzing bundle contains a suspicious compression ratio")
            if not member.is_dir():
                normalized[path.as_posix()] = member
        parts = [name for name in normalized if name.lower().endswith(".fzp")]
        if len(parts) != 1:
            raise DefinitionError("Fritzing bundle must contain exactly one .fzp part definition")
        try:
            part_content = archive.read(normalized[parts[0]]).decode("utf-8")
        except UnicodeDecodeError as error:
            raise DefinitionError("Fritzing part definition is not UTF-8") from error
        result = import_fritzing_part(part_content, source_name)
        visual_assets: list[dict[str, Any]] = []
        for view, metadata in result["views"].items():
            reference = metadata.get("image", "").replace("\\", "/")
            flattened = f"svg.{reference.replace('/', '.')}".lower()
            matches = [
                name for name in normalized
                if name.lower().endswith(reference.lower())
                or name.lower().endswith(flattened)
                or PurePosixPath(name).name.lower() == PurePosixPath(reference).name.lower()
            ]
            if not matches:
                continue
            asset = archive.read(normalized[matches[0]])
            visual_assets.append({
                "view": view,
                "source_path": matches[0],
                "media_type": "image/svg+xml",
                "sha256": hashlib.sha256(asset).hexdigest(),
                "size_bytes": len(asset),
                "svg": _sanitize_svg(asset, matches[0]),
            })
        result.update({
            "format": "fritzing-bundle",
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "visual_assets": visual_assets,
            "counts": {**result["counts"], "visual_assets": len(visual_assets)},
            "provenance": {"kind": "uploaded_part_bundle", "confidence": "definition_exact"},
            "limitations": ["SVG views are sanitized before storage; external resources and executable content are removed.", result["limitations"][1]],
        })
        return result


def import_hardware_definition(format_name: str, content: str, source_name: str) -> dict[str, Any]:
    if len(content.encode("utf-8")) > MAX_DEFINITION_BYTES:
        raise DefinitionError("Hardware definition exceeds the 4 MiB limit")
    normalized = format_name.strip().lower()
    if normalized in {"cmsis-svd", "svd"}:
        return import_cmsis_svd(content, source_name)
    if normalized in {"zephyr-devicetree", "devicetree", "dts"}:
        return import_zephyr_devicetree(content, source_name)
    if normalized in {"kicad-schematic", "kicad", "kicad-sch"}:
        return import_kicad_schematic(content, source_name)
    if normalized in {"fritzing-part", "fritzing", "fzp"}:
        return import_fritzing_part(content, source_name)
    if normalized in {"fritzing-bundle", "fzpz"}:
        return import_fritzing_bundle(content, source_name)
    raise DefinitionError("Supported definition formats are cmsis-svd, zephyr-devicetree, kicad-schematic, fritzing-part, and fritzing-bundle")
