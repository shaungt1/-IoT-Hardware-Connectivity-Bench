from __future__ import annotations

import importlib.metadata
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "dependency-inventory.json"
TOOL_SITE_PACKAGES = ROOT / ".tool-venv" / "Lib" / "site-packages"
REVIEW_LICENSE = re.compile(r"\b(?:A?GPL|SSPL|EUPL|UNKNOWN|UNDECLARED)\b", re.IGNORECASE)


def license_text_identifier(value: str) -> str | None:
    normalized = " ".join(value.split()).lower()
    if normalized.startswith("mit license ") and "permission is hereby granted" in normalized:
        return "MIT"
    if "apache license version 2.0" in normalized:
        return "Apache-2.0"
    if "redistribution and use in source and binary forms" in normalized:
        if "neither the name" in normalized:
            return "BSD-3-Clause"
        return "BSD-2-Clause"
    return None


def normalized_license(metadata: importlib.metadata.PackageMetadata) -> str:
    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        return expression
    license_value = (metadata.get("License") or "").strip()
    text_identifier = license_text_identifier(license_value)
    if text_identifier:
        return text_identifier
    if license_value and license_value.upper() != "UNKNOWN" and "\n" not in license_value:
        return license_value
    classifiers = metadata.get_all("Classifier") or []
    names = [item.rsplit(" :: ", 1)[-1] for item in classifiers if item.startswith("License ::")]
    return " OR ".join(sorted(set(names))) or "UNDECLARED"


def python_components(environment: str, paths: list[str] | None = None) -> list[dict[str, object]]:
    distributions = importlib.metadata.distributions(path=paths) if paths else importlib.metadata.distributions()
    components: list[dict[str, object]] = []
    for distribution in distributions:
        name = distribution.metadata.get("Name")
        if not name:
            continue
        license_value = normalized_license(distribution.metadata)
        components.append(
            {
                "ecosystem": "python",
                "environment": environment,
                "name": name,
                "version": distribution.version,
                "license": license_value,
                "review_required": bool(REVIEW_LICENSE.search(license_value)),
            }
        )
    return components


def npm_components() -> list[dict[str, object]]:
    lock = json.loads((ROOT / "react-app" / "package-lock.json").read_text(encoding="utf-8"))
    components: list[dict[str, object]] = []
    for package_path, package in lock.get("packages", {}).items():
        if not package_path or package.get("dev"):
            continue
        name = package.get("name") or package_path.rsplit("node_modules/", 1)[-1]
        license_value = str(package.get("license") or "UNDECLARED")
        components.append(
            {
                "ecosystem": "npm",
                "environment": "react-production",
                "name": name,
                "version": str(package.get("version") or "unknown"),
                "license": license_value,
                "review_required": bool(REVIEW_LICENSE.search(license_value)),
            }
        )
    return components


def main() -> None:
    if not TOOL_SITE_PACKAGES.is_dir():
        raise SystemExit(".tool-venv is missing; run setup before generating the dependency inventory")
    components = python_components("api")
    components.extend(python_components("hardware-tools", [str(TOOL_SITE_PACKAGES)]))
    components.extend(npm_components())
    components.sort(key=lambda item: (str(item["environment"]), str(item["name"]).lower(), str(item["version"])))
    review = [item for item in components if item["review_required"]]
    payload = {
        "schema": "iot-bench-dependency-inventory/1.0",
        "notice": "Metadata inventory only; legal review is required before redistribution.",
        "component_count": len(components),
        "review_required_count": len(review),
        "components": components,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"DEPENDENCY_INVENTORY_OK: {len(components)} components; {len(review)} require license review")
    for component in review:
        print(
            f"REVIEW: {component['environment']} {component['name']} {component['version']} "
            f"({component['license']})"
        )


if __name__ == "__main__":
    main()
