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


URDF_JOINT_TYPES = {"revolute", "continuous", "prismatic", "fixed", "floating", "planar"}
# Relative slack for thin plates/rods, where I1 + I2 = I3 holds exactly and rounding can tip it.
TRIANGLE_TOLERANCE = 1e-3


def inertia_values(inertia: ET.Element | None) -> tuple[float, ...] | None:
    """Return (ixx, ixy, ixz, iyy, iyz, izz), or None when any entry is missing or invalid."""
    if inertia is None:
        return None
    values = tuple(number(inertia, key) for key in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz"))
    return None if any(value is None for value in values) else values


def positive_definite(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> bool:
    """Sylvester's criterion for the symmetric 3x3 matrix with these six entries."""
    minor2 = ixx * iyy - ixy * ixy
    determinant = ixx * (iyy * izz - iyz * iyz) - ixy * (ixy * izz - iyz * ixz) + ixz * (ixy * iyz - iyy * ixz)
    return bool(ixx > 0.0 and minor2 > 0.0 and determinant > 0.0)


def positive_definite_inertia(inertia: ET.Element | None) -> bool:
    values = inertia_values(inertia)
    return values is not None and positive_definite(*values)


def triangle_inequality_inertia(inertia: ET.Element | None, tolerance: float = TRIANGLE_TOLERANCE) -> bool:
    """Check I1 + I2 >= I3 for every permutation of the principal moments.

    Rotation-invariant form: every principal moment is at most trace/2, i.e. the
    matrix trace/2 * E - I is positive semidefinite, so off-diagonal tensors need
    no eigen-decomposition. The tolerance is relative to trace/2.
    """
    values = inertia_values(inertia)
    if values is None:
        return False
    ixx, ixy, ixz, iyy, iyz, izz = values
    shift = (ixx + iyy + izz) / 2.0 * (1.0 + tolerance)
    return positive_definite(shift - ixx, -ixy, -ixz, shift - iyy, -iyz, shift - izz)


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
        if joint_type not in URDF_JOINT_TYPES:
            errors.append(f"joint {name!r} has unknown type {joint_type!r}")
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
            elif not triangle_inequality_inertia(inertial.find("inertia")):
                errors.append(f"link {name!r} principal moments violate the triangle inequality I1 + I2 >= I3")
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
    if args.output:
        try:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as error:
            report = {"ok": False, "path": str(args.urdf), "errors": [f"cannot write --output: {error}"], "warnings": []}
            rendered = json.dumps(report, indent=2)
    print(rendered)
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
