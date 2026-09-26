"""Drill 2: URDF joint-graph validator. Implement validate_tree, then run the tests.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish
"""


def validate_tree(joints):
    """Return the single root link of a valid kinematic tree.

    `joints` is an iterable of (parent, child) link-name pairs. Raise ValueError when:
    - `joints` is not iterable, or an item is not a two-element pair;
    - a link name is empty or not a string, or a link is its own parent;
    - a child has more than one parent;
    - there is not exactly one root (a link that is never a child);
    - some link cannot be reached from the root (a detached cycle or second tree).

    Hints:
    - Build a child -> parent map while validating each pair.
    - A cycle that does not include the root still leaves exactly one root, so only a
      traversal from the root reveals it: compare the visited set with all links.
    """
    raise NotImplementedError("implement validate_tree")
