"""Audit URDF graph structure and common physical invariants using only stdlib."""

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def number(element: ET.Element | None, name: str) -> float | None:
    if element is None or element.get(name) is None:
        return None
    try:
        value = float(element.get(name, ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def positive_definite_inertia(inertia: ET.Element | None) -> bool:
    if inertia is None:
        return False
    values = {key: number(inertia, key) for key in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")}
    if any(value is None for value in values.values()):
        return False
    ixx, ixy, ixz = values["ixx"], values["ixy"], values["ixz"]
    iyy, iyz, izz = values["iyy"], values["iyz"], values["izz"]
    minor2 = ixx * iyy - ixy * ixy
    determinant = ixx * (iyy * izz - iyz * iyz) - ixy * (ixy * izz - iyz * ixz) + ixz * (ixy * iyz - iyy * ixz)
    return bool(ixx > 0.0 and minor2 > 0.0 and determinant > 0.0)


def audit_urdf(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if root.tag != "robot":
        return {"ok": False, "errors": ["root element must be <robot>"], "warnings": []}

    errors: list[str] = []
    warnings: list[str] = []
    link_names = [item.get("name", "") for item in root.findall("link")]
    links = set(link_names)
    joints = root.findall("joint")
    if "" in links:
        errors.append("every link must have a non-empty name")
        links.discard("")
    duplicates = sorted({name for name in link_names if name and link_names.count(name) > 1})
    if duplicates:
        errors.append(f"duplicate link names: {duplicates}")
    if not links:
        errors.append("robot contains no links")

    children: dict[str, list[str]] = {name: [] for name in links}
    child_links: set[str] = set()
    joint_names: set[str] = set()
    for joint in joints:
        name = joint.get("name", "")
        joint_type = joint.get("type", "")
        parent = (joint.find("parent").get("link", "") if joint.find("parent") is not None else "")
        child = (joint.find("child").get("link", "") if joint.find("child") is not None else "")
        if not name or name in joint_names:
            errors.append(f"joint name is empty or duplicated: {name!r}")
        joint_names.add(name)
        if parent not in links or child not in links:
            errors.append(f"joint {name!r} references missing parent/child link")
        elif child in child_links:
            errors.append(f"link {child!r} has more than one parent joint")
        else:
            children[parent].append(child)
            child_links.add(child)
        if joint_type in {"revolute", "prismatic"}:
            limit = joint.find("limit")
            lower, upper = number(limit, "lower"), number(limit, "upper")
            effort, velocity = number(limit, "effort"), number(limit, "velocity")
            if lower is None or upper is None or lower > upper:
                errors.append(f"joint {name!r} has invalid position limits")
            if effort is None or effort <= 0.0 or velocity is None or velocity <= 0.0:
                errors.append(f"joint {name!r} needs positive effort and velocity limits")
        mimic = joint.find("mimic")
        if mimic is not None and mimic.get("joint", "") not in {j.get("name", "") for j in joints}:
            errors.append(f"joint {name!r} mimics an unknown joint")

    roots = sorted(links - child_links)
    if len(roots) != 1:
        errors.append(f"expected one root link, found {len(roots)}: {roots}")
    visited: set[str] = set()
    active: set[str] = set()

    def visit(link: str) -> None:
        if link in active:
            errors.append(f"cycle detected at link {link!r}")
            return
        if link in visited:
            return
        active.add(link)
        for child in children.get(link, []):
            visit(child)
        active.remove(link)
        visited.add(link)

    for root_link in roots:
        visit(root_link)
    if links - visited:
        errors.append(f"unreachable links: {sorted(links - visited)}")

    for link in root.findall("link"):
        name = link.get("name", "")
        inertial = link.find("inertial")
        if inertial is None:
            warnings.append(f"link {name!r} has no inertial block")
        else:
            mass = number(inertial.find("mass"), "value")
            if mass is None or mass <= 0.0:
                errors.append(f"link {name!r} has non-positive or invalid mass")
            if not positive_definite_inertia(inertial.find("inertia")):
                errors.append(f"link {name!r} inertia matrix is not symmetric positive definite")
        if link.find("collision") is None:
            warnings.append(f"link {name!r} has no collision geometry")

    return {
        "ok": not errors,
        "robot": root.get("name", ""),
        "path": str(path),
        "counts": {"links": len(links), "joints": len(joints), "roots": len(roots)},
        "root_links": roots,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("urdf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = audit_urdf(args.urdf)
    except (OSError, ET.ParseError) as error:
        report = {"ok": False, "path": str(args.urdf), "errors": [str(error)], "warnings": []}
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
