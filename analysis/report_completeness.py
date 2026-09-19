"""Deterministic technical readiness checks for an authoritative report package."""


_REQUIRED_BLOCKS = (
    "analysis_provenance",
    "model",
    "materials_sections",
    "supports_loads",
    "results",
    "limitations",
)


def _issue(code, *, field=None, object_ref=None):
    issue = {"code": code}
    if field is not None:
        issue["field"] = field
    if object_ref is not None:
        issue["object_ref"] = object_ref
    return issue


def _block(issues):
    return {"status": "MISSING" if issues else "READY", "issues": issues}


def _required_value(mapping, field, code):
    if not isinstance(mapping, dict) or mapping.get(field) is None:
        return _issue(code, field=field)
    return None


def _required_list(mapping, field, code):
    if not isinstance(mapping, dict) or not isinstance(mapping.get(field), list) or not mapping[field]:
        return _issue(code, field=field)
    return None


def _required_mapping(mapping, field, code):
    if not isinstance(mapping, dict) or not isinstance(mapping.get(field), dict) or not mapping[field]:
        return _issue(code, field=field)
    return None


def _material_issues(block):
    issues = []
    materials = block.get("materials") if isinstance(block, dict) else None
    sections = block.get("sections") if isinstance(block, dict) else None
    if not isinstance(materials, list) or not materials:
        issues.append(_issue("MISSING_MATERIAL_EVIDENCE", field="materials"))
    else:
        for material in materials:
            if not isinstance(material, dict) or material.get("E_MPa") is None or material.get("density_g_per_mm3") is None:
                issues.append(_issue("MISSING_MATERIAL_PROPERTY", field="materials"))
                break
    if not isinstance(sections, list) or not sections:
        issues.append(_issue("MISSING_SECTION_EVIDENCE", field="sections"))
    else:
        for section in sections:
            if not isinstance(section, dict) or section.get("A_mm2") is None:
                issues.append(_issue("MISSING_SECTION_PROPERTY", field="sections"))
                break
    return issues


def _analysis_provenance(package):
    metadata = package.get("metadata") if isinstance(package, dict) else None
    provenance = package.get("provenance") if isinstance(package, dict) else None
    issues = []
    for field, code in (
        ("analysis_run_id", "MISSING_ANALYSIS_RUN"),
        ("model_revision_id", "MISSING_MODEL_REVISION"),
        ("solver_version", "MISSING_SOLVER_VERSION"),
        ("model_hash", "MISSING_MODEL_HASH"),
    ):
        issue = _required_value(metadata, field, code)
        if issue:
            issues.append(issue)
    issue = _required_value(provenance, "input_hash", "MISSING_INPUT_HASH")
    if issue:
        issues.append(issue)
    issue = _required_value(provenance, "is_stale", "MISSING_STALE_STATUS")
    if issue:
        issues.append(issue)
    return _block(issues)


def _model(package):
    model = package.get("geometry_connectivity") if isinstance(package, dict) else None
    issues = []
    for field, code in (
        ("nodes", "MISSING_GEOMETRY_EVIDENCE"),
        ("physical_members", "MISSING_GEOMETRY_EVIDENCE"),
        ("connections", "MISSING_CONNECTION_EVIDENCE"),
        ("analysis_member_mapping", "MISSING_ANALYSIS_MAPPING"),
    ):
        issue = _required_mapping(model, field, code) if field == "analysis_member_mapping" else _required_list(model, field, code)
        if issue:
            issues.append(issue)
    return _block(issues)


def _supports_loads(package):
    supports_loads = package.get("supports_loads") if isinstance(package, dict) else None
    issues = []
    for field, code in (
        ("supports", "MISSING_SUPPORT_EVIDENCE"),
        ("loads", "MISSING_LOAD_EVIDENCE"),
    ):
        issue = _required_list(supports_loads, field, code)
        if issue:
            issues.append(issue)
    return _block(issues)


def _results(package):
    node_results = package.get("node_results") if isinstance(package, dict) else None
    member_results = package.get("member_results") if isinstance(package, dict) else None
    summary = package.get("results_summary") if isinstance(package, dict) else None
    issues = []
    if not isinstance(node_results, dict) or node_results.get("status") != "READY":
        issues.append(_issue("MISSING_NODE_RESULTS", field="node_results"))
    elif not isinstance(node_results.get("items"), list) or not node_results["items"]:
        issues.append(_issue("MISSING_NODE_RESULTS", field="node_results.items"))
    if not isinstance(node_results, dict) or not isinstance(node_results.get("support_reactions"), list) or not node_results["support_reactions"]:
        issues.append(_issue("MISSING_REACTION_RESULTS", field="node_results.support_reactions"))
    if not isinstance(member_results, dict) or member_results.get("status") != "READY":
        issues.append(_issue("MISSING_MEMBER_RESULTS", field="member_results"))
    elif not isinstance(member_results.get("items"), list) or not member_results["items"]:
        issues.append(_issue("MISSING_MEMBER_RESULTS", field="member_results.items"))
    if not isinstance(summary, dict) or summary.get("status") != "READY":
        issues.append(_issue("MISSING_RESULTS_SUMMARY", field="results_summary"))
    else:
        if summary.get("maximum_displacement") is None:
            issues.append(_issue("MISSING_DISPLACEMENT_RESULT", field="results_summary.maximum_displacement"))
        if summary.get("total_mass_g") is None:
            issues.append(_issue("MISSING_MASS_RESULT", field="results_summary.total_mass_g"))
    return _block(issues)


def _limitations(package):
    limitations = package.get("validation_limitations") if isinstance(package, dict) else None
    if not isinstance(limitations, dict) or limitations.get("status") != "READY":
        return _block([_issue("MISSING_VALIDATION_LIMITATIONS", field="validation_limitations")])
    return {
        "status": "READY",
        "issues": [],
        "limitations": [
            {
                "code": "EULER_STABILITY_UNAVAILABLE",
                "status": "UNAVAILABLE",
                "scope": "stability",
                "message_key": "euler_stability_unavailable",
            },
            {
                "code": "REPORT_NOT_CODE_COMPLIANCE_REVIEW",
                "status": "NOT_APPLICABLE",
                "scope": "professional_review",
                "message_key": "report_not_code_compliance_review",
            },
        ],
    }


def evaluate_report_completeness(report_package):
    """Evaluate technical readiness from one already-built authoritative package."""
    blocks = {
        "analysis_provenance": _analysis_provenance(report_package),
        "model": _model(report_package),
        "materials_sections": _block(_material_issues(report_package.get("materials_sections"))),
        "supports_loads": _supports_loads(report_package),
        "results": _results(report_package),
        "limitations": _limitations(report_package),
        "student_reasoning": {
            "status": "NOT_APPLICABLE",
            "issues": [{"code": "STUDENT_AUTHORED_POLICY_PENDING"}],
        },
    }
    overall_status = "MISSING" if any(
        blocks[name]["status"] == "MISSING" for name in _REQUIRED_BLOCKS
    ) else "READY"
    provenance = report_package.get("provenance") if isinstance(report_package, dict) else {}
    return {
        "overall": {"status": overall_status, "issues": []},
        "blocks": blocks,
        "stale": bool(isinstance(provenance, dict) and provenance.get("is_stale")),
    }
