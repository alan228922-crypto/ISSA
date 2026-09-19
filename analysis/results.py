from math import hypot, isfinite


def maximum_displacement_summary(result):
    """Return the existing authoritative level-one displacement disclosure."""
    entries = result.get("node_displacements") if isinstance(result, dict) else None
    if not isinstance(entries, list) or not entries:
        return None
    values = []
    for entry in entries:
        if not isinstance(entry, dict):
            return None
        node_id = entry.get("analysis_node_id")
        ux = entry.get("ux_mm")
        uy = entry.get("uy_mm")
        if (
            not isinstance(node_id, str)
            or not isinstance(ux, (int, float))
            or isinstance(ux, bool)
            or not isinstance(uy, (int, float))
            or isinstance(uy, bool)
            or not isfinite(ux)
            or not isfinite(uy)
        ):
            return None
        values.append((node_id, hypot(ux, uy)))
    maximum = max(value for _, value in values)
    tolerance = max(1e-9, 1e-9 * maximum)
    return {
        "maximum_displacement": {
            "maximum_displacement_mm": maximum,
            "candidate_analysis_node_ids": sorted(
                node_id for node_id, value in values if maximum - value <= tolerance
            ),
        }
    }
