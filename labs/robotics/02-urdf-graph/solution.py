def validate_tree(joints):
    parents = {}
    nodes = set()
    try:
        edges = list(joints)
    except TypeError as error:
        raise ValueError("joints must be an iterable of parent-child pairs") from error
    for edge in edges:
        if not isinstance(edge, (tuple, list)) or len(edge) != 2:
            raise ValueError("each joint must be a parent-child pair")
        parent, child = edge
        if not isinstance(parent, str) or not parent.strip() or not isinstance(child, str) or not child.strip():
            raise ValueError("link names must be non-empty strings")
        if parent == child:
            raise ValueError("a link cannot be its own parent")
        if child in parents:
            raise ValueError("child has multiple parents")
        parents[child] = parent
        nodes.update((parent, child))
    roots = nodes - set(parents)
    if len(roots) != 1:
        raise ValueError("expected exactly one root")
    root = next(iter(roots))
    visited = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node in visited:
            raise ValueError("cycle detected")
        visited.add(node)
        stack.extend(child for child, parent in parents.items() if parent == node)
    if visited != nodes:
        raise ValueError("graph is disconnected or cyclic")
    return root
