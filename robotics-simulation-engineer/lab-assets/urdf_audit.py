"""Audit URDF graph structure and common physical invariants using only stdlib."""

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from report_io import emit

URDF_JOINT_TYPES = {"revolute", "continuous", "prismatic", "fixed", "floating", "planar"}
# Relative error above which declared inertia is flagged against its collision primitive.
GEOMETRY_TOLERANCE = 0.25
# Published URDF inertias are usually rounded to 4-5 significant digits, which can push a
# flat plate (I3 == I1 + I2 exactly) just past the triangle boundary; allow 0.1%.
TRIANGLE_TOLERANCE = 1e-3


def number(element: ET.Element | None, name: str) -> float | None:
    if element is None or element.get(name) is None:
        return None
    try:
        value = float(element.get(name, ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def vector(element: ET.Element | None, name: str, size: int = 3) -> list[float] | None:
    """Parse a whitespace-separated attribute; a missing element or attribute means zeros."""
    if element is None or element.get(name) is None:
        return [0.0] * size
    try:
        values = [float(item) for item in element.get(name, "").split()]
    except ValueError:
        return None
    return values if len(values) == size and all(math.isfinite(value) for value in values) else None


def symmetric_eigenvalues(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> list[float]:
    """Eigenvalues of a symmetric 3x3 matrix, ascending, by cyclic Jacobi rotations.

    The closed-form trigonometric solution loses about half the digits when two moments
    are equal, which is exactly the boundary case (a flat plate) the triangle check needs.
    """
    a = [[ixx, ixy, ixz], [ixy, iyy, iyz], [ixz, iyz, izz]]
    scale = max(abs(value) for row in a for value in row) or 1.0
    for _ in range(50):
        off = abs(a[0][1]) + abs(a[0][2]) + abs(a[1][2])
        if off <= 1e-15 * scale:
            break
        for p, q in ((0, 1), (0, 2), (1, 2)):
            if a[p][q] == 0.0:
                continue
            theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
            t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
            c = 1.0 / math.sqrt(t * t + 1.0)
            s = t * c
            for k in range(3):  # A <- A J, then A <- J^T A
                a[k][p], a[k][q] = c * a[k][p] - s * a[k][q], s * a[k][p] + c * a[k][q]
            for k in range(3):
                a[p][k], a[q][k] = c * a[p][k] - s * a[q][k], s * a[p][k] + c * a[q][k]
    return sorted([a[0][0], a[1][1], a[2][2]])


def inertia_values(inertia: ET.Element | None) -> dict[str, float] | None:
    if inertia is None:
        return None
    values = {key: number(inertia, key) for key in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")}
    return None if any(value is None for value in values.values()) else values  # type: ignore[return-value]


def inertia_problem(values: dict[str, float] | None) -> str | None:
    """Return why an inertia tensor is not physically realizable, or None when it is.

    Positive-definite is necessary but not sufficient: a rigid body's principal moments
    must also satisfy the triangle inequality (each moment <= the sum of the other two).
    """
    if values is None:
        return "inertia is missing or has non-numeric components"
    moments = symmetric_eigenvalues(
        values["ixx"], values["ixy"], values["ixz"], values["iyy"], values["iyz"], values["izz"]
    )
    if moments[0] <= 0.0:
        return f"inertia is not positive definite (principal moments {moments})"
    if moments[2] > (moments[0] + moments[1]) * (1.0 + TRIANGLE_TOLERANCE):
        return f"principal moments {moments} violate the triangle inequality"
    return None


def primitive_inertia(geometry: ET.Element | None, mass: float) -> tuple[str, list[float]] | None:
    """Diagonal inertia of a uniform-density primitive about its own center, in its own axes."""
    if geometry is None:
        return None
    box = geometry.find("box")
    if box is not None:
        size = vector(box, "size")
        if size is None or min(size) <= 0.0:
            return None
        x, y, z = size
        return "box", [mass * (y * y + z * z) / 12.0, mass * (x * x + z * z) / 12.0, mass * (x * x + y * y) / 12.0]
    cylinder = geometry.find("cylinder")
    if cylinder is not None:
        radius, length = number(cylinder, "radius"), number(cylinder, "length")
        if not radius or not length or radius <= 0.0 or length <= 0.0:
            return None
        side = mass * (3.0 * radius * radius + length * length) / 12.0
        return "cylinder", [side, side, mass * radius * radius / 2.0]
    sphere = geometry.find("sphere")
    if sphere is not None:
        radius = number(sphere, "radius")
        if not radius or radius <= 0.0:
            return None
        moment = 2.0 * mass * radius * radius / 5.0
        return "sphere", [moment, moment, moment]
    return None


def geometry_warning(name: str, link: ET.Element, mass: float, values: dict[str, float]) -> str | None:
    """Compare declared inertia with the single collision primitive when frames make that valid."""
    collisions = link.findall("collision")
    if len(collisions) != 1:
        return None
    inertial_origin = link.find("inertial/origin")
    collision_origin = collisions[0].find("origin")
    frames = [vector(inertial_origin, "xyz"), vector(inertial_origin, "rpy"),
              vector(collision_origin, "xyz"), vector(collision_origin, "rpy")]
    if any(item is None for item in frames):
        return None
    inertial_xyz, inertial_rpy, collision_xyz, collision_rpy = frames
    # Only compare when both frames share the link axes and the COM sits at the shape center.
    if any(abs(value) > 1e-9 for value in (*inertial_rpy, *collision_rpy)):
        return None
    if any(abs(a - b) > 1e-9 for a, b in zip(inertial_xyz, collision_xyz)):
        return None
    if any(abs(values[key]) > 1e-12 for key in ("ixy", "ixz", "iyz")):
        return None
    expected = primitive_inertia(collisions[0].find("geometry"), mass)
    if expected is None:
        return None
    shape, reference = expected
    declared = [values["ixx"], values["iyy"], values["izz"]]
    errors = [abs(d - r) / r for d, r in zip(declared, reference)]
    if max(errors) <= GEOMETRY_TOLERANCE:
        return None
    axis = "xyz"[errors.index(max(errors))]
    rounded = [float(f"{value:.6g}") for value in reference]
    return (
        f"link {name!r} i{axis}{axis} differs by {max(errors):.0%} from a uniform {shape} of the same mass "
        f"(expected ixx, iyy, izz ~ {rounded}); confirm CAD mass properties or fix the axis"
    )


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
    all_joint_names = {joint.get("name", "") for joint in joints}
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
        if joint_type in {"revolute", "prismatic", "continuous"}:
            axis = vector(joint.find("axis"), "xyz") if joint.find("axis") is not None else [1.0, 0.0, 0.0]
            if axis is None or math.hypot(*axis) < 1e-9:
                errors.append(f"joint {name!r} has an invalid or zero-length axis")
        mimic = joint.find("mimic")
        if mimic is not None and mimic.get("joint", "") not in all_joint_names:
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
            values = inertia_values(inertial.find("inertia"))
            problem = inertia_problem(values)
            if problem:
                errors.append(f"link {name!r} {problem}")
            elif mass is not None and mass > 0.0 and values is not None:
                warning = geometry_warning(name, link, mass, values)
                if warning:
                    warnings.append(warning)
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
    report, _ = emit(report, args.output)
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
