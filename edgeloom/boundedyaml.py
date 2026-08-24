"""Bounds on documents parsed from untrusted sources.

`yaml.safe_load` resolves aliases into shared references rather than copies, so
parsing a document with nested anchors is cheap and looks harmless. The cost
appears later, in whatever walks the result: `json.dumps` flattens the shared
graph and writes every path, and `jsonschema` visits every logical leaf. A
sub-kilobyte driver file reaches hundreds of megabytes that way.

The check here measures the size a consumer would *see* — aliases expanded —
without expanding anything. Counting is memoised per object identity, so a node
reachable by a million paths is visited once and its subtotal reused. That makes
the check proportional to the distinct nodes in the document, not to the
expansion it describes.

Reported as #44 and #45 by the audit that followed the `deviceProfileName`
report in `SECURITY.md`.
"""

from __future__ import annotations

from typing import Any

# A real profile or fingerprints file is a few hundred nodes. Six figures leaves
# a wide margin for legitimate growth while stopping expansion long before it
# costs real memory: the measured failures started around 10^6 logical leaves.
DEFAULT_NODE_BUDGET = 200_000

# json.loads and yaml.safe_load both recurse, and a deeply nested document
# raises RecursionError from inside the parser before this module sees it.
# Callers translate that into a diagnostic; this cap catches what parses.
DEFAULT_DEPTH_BUDGET = 100


class DocumentTooLargeError(ValueError):
    """A parsed document would expand past what a consumer can be asked to walk."""


def expanded_node_count(document: Any, *, depth_budget: int = DEFAULT_DEPTH_BUDGET) -> int:
    """Nodes a consumer sees once aliases are expanded, counted without expanding.

    Raises `DocumentTooLargeError` on a self-referential document, which YAML
    permits and which no consumer here can walk.
    """
    memo: dict[int, int] = {}
    in_progress: set[int] = set()

    def count(node: Any, depth: int) -> int:
        if depth > depth_budget:
            raise DocumentTooLargeError(
                f"document nests deeper than {depth_budget} levels",
            )
        key = id(node)
        if key in memo:
            return memo[key]
        if key in in_progress:
            raise DocumentTooLargeError("document contains a recursive alias")

        if isinstance(node, dict):
            in_progress.add(key)
            total = 1 + sum(count(k, depth + 1) + count(v, depth + 1) for k, v in node.items())
            in_progress.discard(key)
        elif isinstance(node, (list, tuple)):
            in_progress.add(key)
            total = 1 + sum(count(item, depth + 1) for item in node)
            in_progress.discard(key)
        else:
            total = 1

        memo[key] = total
        return total

    return count(document, 0)


def check_bounds(
    document: Any,
    *,
    node_budget: int = DEFAULT_NODE_BUDGET,
    depth_budget: int = DEFAULT_DEPTH_BUDGET,
) -> Any:
    """Return `document` unchanged, or raise if walking it would be unreasonable."""
    size = expanded_node_count(document, depth_budget=depth_budget)
    if size > node_budget:
        raise DocumentTooLargeError(
            f"document expands to {size:,} nodes, over the {node_budget:,} limit; "
            f"this is what nested YAML aliases do to a small file",
        )
    return document
