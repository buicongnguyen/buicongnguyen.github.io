"""Entry task: change dimensions, calculate by hand, and compare with this executable result."""
from readiness import box_inertia

MASS_KG = 12.0
DIMENSIONS_M = (2.0, 4.0, 6.0)
print(box_inertia(MASS_KG, *DIMENSIONS_M))
print("For fixed stiffness, critical damping scales with sqrt(mass).")
