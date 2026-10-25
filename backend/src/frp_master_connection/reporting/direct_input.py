"""Concise Direct input reports; unvalidated drafts never supply design results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.platypus import Flowable

from frp_master_connection.reporting.reader_data import readable_value
from frp_master_connection.reporting.snapshot import ReportSnapshot
from frp_master_connection.reporting.units import resolved_display_units

if TYPE_CHECKING:
    from frp_master_connection.reporting.pdf import ReportOptions


def render_direct_input_pdf(snapshot: ReportSnapshot, options: ReportOptions) -> bytes:
    from frp_master_connection.reporting.pdf import (
        _append_bounded_tables,
        _finish_multirow_pdf,
        _flatten,
        _font_setup,
        _paragraph,
        _styles,
        _table,
    )

    _font_setup()
    styles = _styles()
    system = resolved_display_units(snapshot.request, snapshot.result, options.display_units)
    root = snapshot.request.get("client_draft", snapshot.request)
    legacy = root.get("legacy_request", root)
    assignments = root.get("assignments", root.get("mat1_assignments", {}))
    decision = snapshot.result["final_decision"]
    status = decision["final_status"] + " — " + decision["final_status_reason"]
    story: list[Flowable] = [
        _paragraph("Direct inputs report — design not evaluated", styles["title"]),
        _paragraph("0  Design status — " + status, styles["heading"]),
        _paragraph(
            "No current validated engineering result. These submitted inputs have not established "
            "a PASS, FAIL, qualification, resistance or governing design. "
            "Correct the inputs and run Design Check.",
            styles["body"],
        ),
        _table(
            [
                ("Snapshot identity", snapshot.digest[:12]),
                ("Geometry / physical model", "Not validated; no current canonical physical model"),
                ("Numerical checks", "None evaluated"),
                ("Qualification", "Not evaluated; no approved record established"),
                (
                    "Validation issues",
                    readable_value(snapshot.result.get("validation_issues"), system),
                ),
            ],
            styles,
        ),
        _paragraph("1  Submitted geometry and detailing", styles["heading"]),
    ]
    excluded = {
        "physical_connection",
        "layers",
        "provenance",
        "layer_snapshots",
        "fastener_snapshot",
    }
    rows = [
        (name.replace("_", " ").title(), readable_value(value, system))
        for name, value in legacy.items()
        if name not in excluded
    ]
    _append_bounded_tables(story, rows, styles)
    physical = legacy.get("physical_connection", {})
    if isinstance(physical, dict):
        story.append(_paragraph("2  Submitted members, interfaces and actions", styles["heading"]))
        joint = physical.get("joint_assembly", {})
        story.append(
            _table(
                [
                    ("Submitted joint / members / actions", readable_value(joint, system)),
                    (
                        "Interface / placement",
                        readable_value(physical.get("geometry_template"), system),
                    ),
                    (
                        "Installed hardware",
                        readable_value(physical.get("fastener_snapshot"), system),
                    ),
                ],
                styles,
            )
        )
    story.append(
        _paragraph("3  Submitted material, hardware and project conditions", styles["heading"])
    )
    _append_bounded_tables(
        story, [("Submitted assignments", readable_value(assignments, system))], styles
    )
    story.append(_paragraph("4  Design and source limitations", styles["heading"]))
    story.append(
        _paragraph(
            "These are input declarations, including selected source identities. "
            "They do not authenticate product qualification or source approval. "
            "No prior design result is carried into this input report. Complete exact draft "
            "fields and validation records are retained in the Full Technical Audit.",
            styles["body"],
        )
    )
    if options.mode == "FULL_TECHNICAL_AUDIT":
        story.append(
            _paragraph("Technical audit — complete captured input and result", styles["heading"])
        )
        _append_bounded_tables(story, _flatten("request", snapshot.request), styles)
        _append_bounded_tables(story, _flatten("result", snapshot.result), styles)
        _append_bounded_tables(story, _flatten("provenance", snapshot.input_provenance), styles)
    return _finish_multirow_pdf(story, snapshot, options, status, styles)
