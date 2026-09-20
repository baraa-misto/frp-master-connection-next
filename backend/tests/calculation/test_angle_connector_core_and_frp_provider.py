"""Controlled CS7-RC2 G1-G72 and adverse-case tests; no production fixture reader."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import fields, replace
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation import angle_connector_core as core_module
from frp_master_connection.calculation.angle_connector_core import (
    CORE_METHOD,
    EXTERNAL_DISTRIBUTION,
    AngleConnectorFrame,
    AngleConnectorGeometry,
    AngleCoreRequest,
    AngleCoreResult,
    AngleWrench,
    angle_fingerprint,
    components,
    exact_decimal,
    resolve_angle_connector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.angle_connector_providers import (
    PROVIDER_CONTRACT,
    PROVIDER_NOT_IMPLEMENTED,
    AngleProviderResult,
    angle_provider_registry,
    evaluate_angle_provider,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.equations import EndUsePropertyTrace, adjust_frp_property
from frp_master_connection.calculation.frp_angle_connector_provider import (
    COMPONENT_NAMES,
    DISCLAIMER_ID,
    ENVELOPE_METHOD,
    FRP_PROVIDER_ID,
    INSTEP_METHOD,
    INTERACTION_METHOD,
    REVIEW_PASS,
    FRPAngleContext,
    FRPAngleDetail,
    FRPSourceBinding,
    QualifiedCoverage,
    QualifiedFRPAngleSource,
    SignedDesignStrength,
    frp_source_binding,
)
from frp_master_connection.calculation.inputs import EndUseFactors
from frp_master_connection.calculation.properties import (
    FRPPropertyEntry,
    FRPPropertyKind,
    MaterialPropertySnapshot,
    PropertyBehavior,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus, SourceClassification
from frp_master_connection.domain.material_architecture import (
    ConnectorMaterialFamily,
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    PropertySourceConfirmation,
)

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT
    / "backend/tests/golden"
    / "calculation_slice_7_angle_connector_core_and_frp_provider_golden_benchmarks_rc2.json"
)
DATA = cast(dict[str, Any], json.loads(GOLDEN.read_text(encoding="utf-8")))
G = {int(row["id"].split("_")[0][1:]): row["expected"] for row in DATA["benchmarks"]}
D = Decimal


def q(value: str, unit: Unit = Unit.IN) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def vector(values: tuple[str, str, str], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(q(v, unit) for v in values))


def values(vector_: ExactQuantityVector3D, unit: Unit) -> list[Decimal]:
    return [v.to(unit).magnitude for v in (vector_.x, vector_.y, vector_.z)]


def request() -> AngleCoreRequest:
    return AngleCoreRequest(
        AngleConnectorGeometry(q("8"), q("4"), q("4"), q("0.5"), q("0.25"), (q("0"), q("0"))),
        AngleConnectorFrame((D(1), D(0), D(0)), (D(0), D(1), D(0)), (D(0), D(0), D(1))),
        AngleWrench(
            vector(("0", "2.5", "0"), Unit.IN),
            vector(("4", "6", "-1"), Unit.KIP),
            vector(("1.5", "-0.5", "1"), Unit.KIP_IN),
        ),
        vector(("0", "0", "2"), Unit.IN),
    )


def context() -> FRPAngleContext:
    entry = FRPPropertyEntry(
        FRPPropertyKind.FSH_LT,
        q("8", Unit.KSI),
        PropertyBehavior.IN_PLANE_SHEAR,
        SourceClassification.QUALIFIED_TEST_DATA,
        QualificationStatus.QUALIFIED,
        "CS7 arithmetic-only material fixture",
        "RC2",
    )
    material = MaterialPropertySnapshot(
        "cs7-test-material",
        "TEST ONLY",
        True,
        SourceClassification.QUALIFIED_TEST_DATA,
        (QualificationStatus.QUALIFIED,),
        (entry,),
    )
    trace = EndUsePropertyTrace(
        FRPPropertyKind.FSH_LT,
        entry.value,
        QualificationStatus.QUALIFIED,
        D(1),
        D(1),
        D(1),
        entry.value,
    )
    return FRPAngleContext(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        True,
        material,
        trace,
        angle_fingerprint("test-member-fasteners"),
        angle_fingerprint("test-support-fixture"),
    )


def qualified(core: AngleCoreResult, ctx: FRPAngleContext) -> FRPAngleContext:
    # RC2 specification section 23 explicitly retains these RC1 arithmetic-only strengths.
    numbers = (("25", "20"), ("30", "40"), ("15", "15"), ("12", "10"), ("20", "20"), ("18", "24"))
    strengths = tuple(
        SignedDesignStrength(
            q(p, Unit.KIP if i < 3 else Unit.KIP_IN), q(n, Unit.KIP if i < 3 else Unit.KIP_IN)
        )
        for i, (p, n) in enumerate(numbers)
    )
    source = EngineeringPropertySource(
        EngineeringPropertySourceKind.TEST_QUALIFIED_DATA,
        "TEST-ONLY-CS7-ARITHMETIC",
        "RC2",
        PropertySourceConfirmation.TEST_QUALIFIED,
        ("RC2-section-23-arithmetic-only",),
        True,
        approval_authority_id="test-only-authority",
        qualification_record_ids=("test-only-not-physical-qualification",),
    )
    package = QualifiedFRPAngleSource(
        source, frp_source_binding(core, ctx), strengths, tuple(QualifiedCoverage), True
    )
    return replace(ctx, qualified_source=package)


def detail(result: AngleProviderResult) -> FRPAngleDetail:
    assert isinstance(result.detail, FRPAngleDetail)
    return result.detail


def package(ctx: FRPAngleContext) -> QualifiedFRPAngleSource:
    assert ctx.qualified_source is not None
    return ctx.qualified_source


@pytest.fixture
def core() -> AngleCoreResult:
    return resolve_angle_connector(request())


@pytest.fixture
def ctx(core: AngleCoreResult) -> FRPAngleContext:
    return qualified(core, context())


def test_g1_complete_rc2_package_and_hashes() -> None:
    assert list(G) == list(range(1, 73))
    assert DATA["contract"] == "CS7-RC2"
    assert G[1] == {"superseded_package": "CS7-RC1-preexecution", "execute_old_package": False}
    paths = (
        (
            "docs/governance/CALCULATION_SLICE_7_ANGLE_CONNECTOR_CORE_AND_FRP_PROVIDER_DECISION_RC2.md",
            "930517D8198A553206BCBC18CA4435D04DA98E7922186DDDEDBA8F4CAAB8CFC2",
        ),
        (
            "docs/engineering/CALCULATION_SLICE_7_ANGLE_CONNECTOR_CORE_AND_FRP_PROVIDER_ENGINEERING_SPECIFICATION_RC2.md",
            "DB578929B9E3355E77A8B703AB8857DC713F100FA9D1884D1D071B4751939F83",
        ),
        (
            str(GOLDEN.relative_to(ROOT)),
            "74CC12CB079A3C8429BD7249E0DE4E16CE066B156D50AF824992000E27701722",
        ),
        (
            "docs/qa/CALCULATION_SLICE_7_ANGLE_CONNECTOR_CORE_AND_FRP_PROVIDER_AUTHORITY_LEDGER_RC2.md",
            "3A214576C1BF7DB976010CD4AEC0F1D1FAFEFC92B99D3B7633A5559E89E46D9D",
        ),
    )
    for path, expected in paths:
        raw = (ROOT / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == expected
        if path.endswith(".md"):
            assert raw.decode().rstrip().endswith("RC2**")


def test_g2_g5_contracts_and_registry(core: AngleCoreResult) -> None:
    assert G[2]["core"] == CORE_METHOD
    assert G[3]["provider_contract"] == PROVIDER_CONTRACT
    assert list(angle_provider_registry()) == G[3]["implemented_providers"]
    assert core.request.frame.c == (D(0), D(0), D(1))
    assert G[5]["right_handed"] == "A_A_x_B_A_equals_C_A"
    assert evaluate_angle_provider(core, "316SS").status == G[4]["status"]


def test_g6_g15_exact_geometry_references_wrenches_equilibrium(core: AngleCoreResult) -> None:
    geometry = core.request.geometry
    assert [
        v.to(Unit.IN).magnitude
        for v in (
            geometry.length,
            geometry.member_leg,
            geometry.support_leg,
            geometry.thickness,
            geometry.inside_radius,
        )
    ] == [D(v) for v in G[6].values()]
    for actual, key in (
        (core.heel.reference, "r_H"),
        (core.request.member_action.reference, "r_M"),
        (core.connector_on_support.reference, "r_S"),
    ):
        assert values(actual, Unit.IN) == [D(v) for v in G[7][key]]
    for actual, unit, number, key in (
        (core.request.member_action.force, Unit.KIP, 8, "F_kip"),
        (core.request.member_action.moment, Unit.KIP_IN, 9, "M_kip_in"),
        (core.heel.force, Unit.KIP, 10, "F_H_kip"),
        (core.heel.moment, Unit.KIP_IN, 11, "M_H_kip_in"),
        (core.connector_on_support.force, Unit.KIP, 12, "F_support_kip"),
        (core.connector_on_support.moment, Unit.KIP_IN, 13, "M_support_kip_in"),
    ):
        assert values(actual, unit) == [D(v) for v in G[number][key]]
    assert (components(core.equilibrium.force) == (Fraction(0), Fraction(0), Fraction(0))) is G[14][
        "exact"
    ]
    assert (components(core.equilibrium.moment) == (Fraction(0), Fraction(0), Fraction(0))) is G[
        15
    ]["exact"]
    reaction = shift_angle_wrench(core.support_on_connector, core.heel.reference)
    assert values(reaction.moment, Unit.KIP_IN) == [D(1), D("0.5"), D(9)]


def test_g16_g20_provider_independence(core: AngleCoreResult, ctx: FRPAngleContext) -> None:
    frp = evaluate_angle_provider(core, "FRP", ctx)
    unknown = evaluate_angle_provider(core, "316SS", ctx)
    assert frp.provider_id == G[18]["provider_id"]
    assert unknown.provider_id == G[19]["provider_id"]
    assert unknown.status == G[19]["status"]
    assert frp.core_fingerprint == unknown.core_fingerprint == core.fingerprint
    assert unknown.detail is None
    assert frp.fingerprint != unknown.fingerprint != core.fingerprint
    assert not G[16]["includes_material_provider"]
    assert G[17]["same_core_fingerprint"]
    assert not G[20]["unsupported_provider_falls_back_to_FRP"]
    assert evaluate_angle_provider(core, "frp", ctx).status == PROVIDER_NOT_IMPLEMENTED
    assert evaluate_angle_provider(core, "unknown", ctx).status == PROVIDER_NOT_IMPLEMENTED
    assert evaluate_angle_provider(core, "FRP").status == "INVALID"


def test_g21_g27_frp_axes_and_instep(core: AngleCoreResult, ctx: FRPAngleContext) -> None:
    record = detail(evaluate_angle_provider(core, "FRP", ctx))
    axes = record.material_axes
    assert (axes.lw, axes.member_cw, axes.support_cw) == (
        core.request.frame.a,
        core.request.frame.b,
        core.request.frame.c,
    )
    assert (axes.member_tt, axes.support_tt) == ((D(0), D(0), D(1)), (D(0), D(-1), D(0)))
    assert G[21]["LW"] == "A_A"
    instep = record.instep
    assert instep is not None
    assert instep.method == G[22]["method"]
    assert instep.factors.phi == D(G[22]["phi"])
    assert instep.length.to(Unit.IN).magnitude == D(G[23]["l_sp_in"])
    assert instep.factors.design_resistance.to(Unit.KIP).magnitude == D(G[24]["phi_R_kip"])
    assert instep.demand.to(Unit.KIP).magnitude == D(G[25]["V_instep_kip"])
    assert instep.utilization == D(G[26]["U"])
    assert instep.covered_component == "F_A"
    assert G[27]["only_F_A_component"]
    assert not G[27]["other_components_covered_by_eq_8_15"]


def test_g28_g36_qualified_full_wrench(core: AngleCoreResult, ctx: FRPAngleContext) -> None:
    result = evaluate_angle_provider(core, "FRP", ctx)
    body = detail(result).body
    assert G[28]["nonzero_full_wrench"]
    assert not G[28]["anonymous_numeric_source_allowed"]
    assert [f.name for f in fields(FRPSourceBinding)] == [
        "geometry",
        "material",
        "member_fasteners",
        "support_fixture",
        "references",
    ]
    assert not G[29]["interpolation"]
    assert package(ctx).strengths[0].positive != package(ctx).strengths[0].negative
    assert package(ctx).strengths[3].positive != package(ctx).strengths[3].negative
    assert G[30]["positive_negative_distinct"]
    assert G[31]["positive_negative_distinct"]
    assert set(package(ctx).coverage) == set(QualifiedCoverage)
    assert all(G[32].values())
    assert body.interaction_method == G[33]["method"]
    assert body.utilization == D(G[34]["U_Q"])
    assert body.status == result.status == G[35]["status"]
    assert result.status != "PASS"
    assert not G[36]["ordinary_PASS"]
    assert tuple(t.component for t in body.terms) == COMPONENT_NAMES
    assert [t.selected_design_strength for t in body.terms] == [
        package(ctx).strengths[i].positive if i < 2 else package(ctx).strengths[i].negative
        for i in range(6)
    ]


def test_g37_missing_qualified_source(core: AngleCoreResult) -> None:
    result = evaluate_angle_provider(core, "FRP", context())
    assert result.status == G[37]["no_qualified_source_nonzero_demand"]
    assert detail(result).instep is not None


@pytest.mark.parametrize("field", [f.name for f in fields(FRPSourceBinding)])
def test_g38_every_binding_mismatch(
    core: AngleCoreResult, ctx: FRPAngleContext, field: str
) -> None:
    changed = replace(package(ctx), binding=replace(package(ctx).binding, **{field: "a" * 64}))
    assert (
        evaluate_angle_provider(core, "FRP", replace(ctx, qualified_source=changed)).status
        == G[38]["status"]
    )


def test_g39_g42_missing_signed_strength_authority_coverage(
    core: AngleCoreResult, ctx: FRPAngleContext
) -> None:
    src = package(ctx)
    cases = (
        (
            39,
            replace(src, strengths=(replace(src.strengths[0], positive=None), *src.strengths[1:])),
        ),
        (40, replace(src, linear_interaction_authorized=False)),
        (
            41,
            replace(
                src, coverage=tuple(c for c in src.coverage if c is not QualifiedCoverage.HEEL)
            ),
        ),
        (
            42,
            replace(
                src, coverage=tuple(c for c in src.coverage if c is not QualifiedCoverage.PRYING)
            ),
        ),
    )
    for number, changed in cases:
        assert (
            evaluate_angle_provider(core, "FRP", replace(ctx, qualified_source=changed)).status
            == G[number]["status"]
        )


def test_g43_zero_demand_needs_no_qualified_source() -> None:
    req = request()
    core = resolve_angle_connector(
        replace(
            req,
            member_action=replace(
                req.member_action,
                force=vector(("0", "0", "0"), Unit.KIP),
                moment=vector(("0", "0", "0"), Unit.KIP_IN),
            ),
        )
    )
    result = evaluate_angle_provider(core, "FRP", context())
    assert result.status == G[43]["status"]
    assert not G[43]["source_required"]


def test_g44_g46_external_handoff(core: AngleCoreResult, ctx: FRPAngleContext) -> None:
    assert not any(G[44].values())
    assert not G[45]["individual_anchor_forces_fabricated"]
    assert core.support_distribution_status == G[46]["state"] == EXTERNAL_DISTRIBUTION
    for key, data in (("FRP", ctx), ("FRP", context()), ("316SS", None)):
        assert evaluate_angle_provider(core, key, data).core_fingerprint == core.fingerprint
        assert values(core.connector_on_support.moment, Unit.KIP_IN) == [D(11), D("-8.5"), D(-9)]
    assert not any("anchor_forces" in f.name or "capacity" in f.name for f in fields(core))


def convert_vector(value: ExactQuantityVector3D, unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(v.to(unit) for v in (value.x, value.y, value.z)))


def test_g47_g50_us_si_and_separate_records(core: AngleCoreResult, ctx: FRPAngleContext) -> None:
    req = request()
    g = req.geometry
    si = resolve_angle_connector(
        replace(
            req,
            geometry=AngleConnectorGeometry(
                g.length.to(Unit.MM),
                g.member_leg.to(Unit.MM),
                g.support_leg.to(Unit.MM),
                g.thickness.to(Unit.MM),
                g.inside_radius.to(Unit.MM),
                (g.heel_end_reliefs[0].to(Unit.MM), g.heel_end_reliefs[1].to(Unit.MM)),
            ),
            member_action=AngleWrench(
                convert_vector(req.member_action.reference, Unit.MM),
                convert_vector(req.member_action.force, Unit.N),
                convert_vector(req.member_action.moment, Unit.N_MM),
            ),
            support_reference=convert_vector(req.support_reference, Unit.MM),
        )
    )
    assert si == core
    assert all(G[47].values())
    si_trace = replace(
        ctx.instep_property,
        source_property=ctx.instep_property.source_property.to(Unit.MPA),
        adjusted_property=ctx.instep_property.adjusted_property.to(Unit.MPA),
    )
    si_material = replace(
        ctx.material,
        properties=tuple(replace(p, value=p.value.to(Unit.MPA)) for p in ctx.material.properties),
    )
    si_source = replace(
        package(ctx),
        strengths=tuple(
            SignedDesignStrength(
                s.positive.to(Unit.N if i < 3 else Unit.N_MM) if s.positive is not None else None,
                s.negative.to(Unit.N if i < 3 else Unit.N_MM) if s.negative is not None else None,
            )
            for i, s in enumerate(package(ctx).strengths)
        ),
    )
    si_ctx = replace(
        ctx, instep_property=si_trace, material=si_material, qualified_source=si_source
    )
    a, b = evaluate_angle_provider(core, "FRP", ctx), evaluate_angle_provider(si, "FRP", si_ctx)
    assert a.fingerprint == b.fingerprint
    assert detail(a).instep == detail(b).instep
    assert detail(a).body == detail(b).body
    assert all(G[48].values())
    assert G[49]["separate_records"]
    assert G[50]["separate_provider_fingerprint"]
    assert isinstance(core, AngleCoreResult)
    assert isinstance(a, AngleProviderResult)
    assert core.fingerprint != a.fingerprint


def test_g51_g55_provider_architecture_no_new_product(core: AngleCoreResult) -> None:
    source = inspect.getsource(core_module)
    assert "frp_angle_connector_provider" not in source
    assert "8-15" not in source
    assert "316SS" not in source
    assert "MaterialPropertySnapshot" not in source
    assert G[51]["architectural_contract"]
    assert evaluate_angle_provider(core, "316SS").status == PROVIDER_NOT_IMPLEMENTED
    assert not any(G[52].values())
    assert not G[53]["implemented"]
    assert not G[54]["frontend_option"]
    assert not any(G[55].values())


def test_g56_g59_successor_safe_protected_identity_record() -> None:
    # Historical identities, not successor HEAD or mandatory local tag refs.
    manifest_path = (
        ROOT / "docs/governance/STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE_MANIFEST.json"
    )
    assert (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
        == "2C79F811EECFD89C04862359E583A240284872C10A0603E3D6CA276D657CED77"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert (
        manifest["repository_identities"]["trees"]["frontend/src"]["git_tree"]
        == "18f335ef899d501a7a8a66beae2fd513d66149a6"
    )
    handoff = json.loads((ROOT / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    for number, key in (
        (56, "frontend_production"),
        (57, "dependencies"),
        (58, "workflows"),
        (59, "tags"),
    ):
        assert handoff["calculation_slice_7_rc2"]["change_counts"][key] == G[number]["count"]


@pytest.mark.parametrize(
    ("number", "name", "digest"),
    [
        (
            60,
            "STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE_MANIFEST.json",
            "2C79F811EECFD89C04862359E583A240284872C10A0603E3D6CA276D657CED77",
        ),
        (
            61,
            "STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_FREEZE_MANIFEST.json",
            "A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F",
        ),
        (
            64,
            "STAGE_3_7_COLUMN_BASE_SHEAR_FAMILY_FREEZE_MANIFEST.json",
            "8C7CD0238C7A95E54E4B6DC987E4A558AE2910DA80342137C7772B7FCF6EC9AE",
        ),
        (
            65,
            "STAGE_3_6_WI_WEB_SPLICE_FAMILY_FREEZE_MANIFEST.json",
            "58AA05F545984EAAC0EDED666B4BA086BA05ADE40E59C39D3B7821BFFEB60658",
        ),
        (
            66,
            "STAGE_3_5_CONCRETE_SUPPORT_SHEAR_FAMILY_FREEZE_MANIFEST.json",
            "671DF6992BC35AFED3C7CE9CB0230F7778C74CE8E7F412C16A9467F080AB7258",
        ),
        (
            67,
            "STAGE_3_4_MULTI_MEMBER_TEE_FAMILY_FREEZE_MANIFEST.json",
            "EE4BADFE145B9FA5815D547C079A371C8C907613CB7253E4A12F922CBF9833DD",
        ),
        (
            68,
            "STAGE_3_3_CLIP_ANGLE_FAMILY_FREEZE_MANIFEST.json",
            "74E7180E37E223E8EC6550A46F316A344FF29C6496C25D0A01916AC5B4174CC4",
        ),
        (
            69,
            "STAGE_3_2_TEE_CONNECTION_FREEZE_MANIFEST.json",
            "25A244EBFBC3AC7990B45657025FD6A1FD0C59544BE2ECB13738DFBCC34C9E7E",
        ),
        (
            70,
            "STAGE_2_3_INTERFACE_GEOMETRY_FREEZE.md",
            "5901DCC3F7FB05932A9841BA4D1FF63FF7A147BE871E67D89D4B46229641D9AB",
        ),
    ],
)
def test_g60_g70_immutable_freeze_records(number: int, name: str, digest: str) -> None:
    assert G[number]["change"] == "NONE"
    assert (
        hashlib.sha256((ROOT / "docs/governance" / name).read_bytes()).hexdigest().upper() == digest
    )


def test_g62_g63_historical_resultant_authority() -> None:
    manifest = json.loads(
        (
            ROOT / "docs/governance/STAGE_4_1_BEAM_MOMENT_SPLICE_FAMILY_FREEZE_MANIFEST.json"
        ).read_text(encoding="utf-8")
    )
    entries = manifest["repository_identities"]["trees"]["backend/src"]["entries"]
    for number, name in ((62, "wi_moment_resultants.py"), (63, "channel_moment_resultants.py")):
        record = next(r for r in entries if r["path"].endswith("/" + name))
        assert (
            hashlib.sha256((ROOT / "backend/src" / record["path"]).read_bytes()).hexdigest().upper()
            == record["sha256"]
        )
        assert G[number]["change"] == "NONE"


def test_g71_g72_review_metadata_and_no_physical_product(
    core: AngleCoreResult, ctx: FRPAngleContext
) -> None:
    record = detail(evaluate_angle_provider(core, "FRP", ctx))
    assert record.review_required == G[71]["review_required"]
    assert record.qualification == G[71]["qualification"]
    assert record.disclaimer_id == G[71]["disclaimer_id"] == DISCLAIMER_ID
    assert "not complete connection approval" in record.disclaimer
    handoff = json.loads((ROOT / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    assert handoff["calculation_slice_7_rc2"]["physical_stage_4_2_not_begun"] == G[72]["not_begun"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("heel_end_reliefs", []),
        ("heel_end_reliefs", (q("0"),)),
        ("length", q("8", Unit.KIP)),
        ("length", "8"),
        ("length", q("0")),
        ("member_leg", q("0.25")),
        ("support_leg", q("0.5")),
        ("inside_radius", q("-0.1")),
        ("inside_radius", q("3.5")),
        ("heel_end_reliefs", (q("-0.1"), q("0"))),
        ("heel_end_reliefs", (q("4"), q("4"))),
    ],
)
def test_reject_invalid_geometry(field: str, value: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(request().geometry, **cast(dict[str, Any], {field: value}))


@pytest.mark.parametrize(
    "axis",
    [[], (D(1),), (1, 0, 0), (D("NaN"), D(0), D(0)), (D(2), D(0), D(0)), (D(-1), D(0), D(0))],
)
def test_reject_invalid_frame(axis: object) -> None:
    with pytest.raises(ValueError, match=r"Frame axes|right-handed"):
        replace(request().frame, a=cast(Any, axis))


@pytest.mark.parametrize("field", ["geometry", "frame", "member_action", "support_reference"])
def test_reject_invalid_core_records(field: str) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(request(), **cast(dict[str, Any], {field: None}))


@pytest.mark.parametrize("field", ["reference", "force", "moment"])
def test_reject_wrong_wrench_dimensions(field: str) -> None:
    with pytest.raises(ValueError, match="Expected an exact"):
        replace(request().member_action, **{field: vector(("0", "0", "0"), Unit.KSI)})


def test_finite_decimal_exactness_and_corrupt_transport_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="nonterminating"):
        exact_decimal(Fraction(1, 3))
    with pytest.raises(TypeError, match="floating"):
        angle_fingerprint(0.1)
    action = request().member_action
    target = vector(("0.12345678901234567890123456789", "-9.555", "33.3"), Unit.MM)
    with localcontext() as decimal_context:
        decimal_context.prec = 3
        shifted = shift_angle_wrench(action, target)
        back = shift_angle_wrench(shifted, action.reference)
    assert back == action
    original = core_module.shift_angle_wrench
    calls = 0

    def corrupt(wrench: AngleWrench, point: ExactQuantityVector3D) -> AngleWrench:
        nonlocal calls
        calls += 1
        result = original(wrench, point)
        if calls == 3:
            return replace(result, moment=vector(("1", "0", "0"), Unit.N_MM))
        return result

    monkeypatch.setattr(core_module, "shift_angle_wrench", corrupt)
    with pytest.raises(ArithmeticError, match="not suppressed"):
        resolve_angle_connector(request())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", None),
        ("binding", None),
        ("strengths", []),
        ("strengths", ()),
        ("strengths", (None,) * 6),
        ("coverage", []),
        ("coverage", ("HEEL",)),
        ("coverage", (QualifiedCoverage.HEEL, QualifiedCoverage.HEEL)),
        ("linear_interaction_authorized", "yes"),
    ],
)
def test_reject_invalid_qualified_records(ctx: FRPAngleContext, field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(package(ctx), **cast(dict[str, Any], {field: value}))


@pytest.mark.parametrize("value", ["anonymous", "A" * 64, None])
def test_reject_invalid_binding_digest(ctx: FRPAngleContext, value: object) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        replace(package(ctx).binding, geometry=cast(str, value))


@pytest.mark.parametrize("value", [q("0", Unit.KIP), q("-1", Unit.KIP), "25"])
def test_reject_nonpositive_or_untyped_strength(value: object) -> None:
    with pytest.raises(ValueError, match="DESIGN strength"):
        SignedDesignStrength(cast(PhysicalQuantity, value), None)


@pytest.mark.parametrize("index", [0, 3])
def test_reject_wrong_signed_strength_dimension(ctx: FRPAngleContext, index: int) -> None:
    strengths = list(package(ctx).strengths)
    strengths[index] = SignedDesignStrength(q("1"), None)
    with pytest.raises(ValueError, match="wrong dimension"):
        replace(package(ctx), strengths=tuple(strengths))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("family", "FRP"),
        ("homogeneous_pultruded_l_angle", "yes"),
        ("material", None),
        ("instep_property", None),
        ("qualified_source", {}),
        ("support_fixture_fingerprint", ""),
    ],
)
def test_reject_invalid_context(ctx: FRPAngleContext, field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(ctx, **cast(dict[str, Any], {field: value}))


def test_pending_unqualified_and_anonymous_source(
    core: AngleCoreResult, ctx: FRPAngleContext
) -> None:
    src = package(ctx)
    for changed in (
        replace(src.source, confirmation=PropertySourceConfirmation.PENDING_CONFIRMATION),
        replace(src.source, qualification_record_ids=()),
    ):
        result = evaluate_angle_provider(
            core, "FRP", replace(ctx, qualified_source=replace(src, source=changed))
        )
        assert result.status == "SOURCE_REQUIRED"
    with pytest.raises(ValueError, match="approval authority"):
        replace(src.source, approval_authority_id=None)


def test_wrong_material_and_unavailable_property_are_invalid(
    core: AngleCoreResult, ctx: FRPAngleContext
) -> None:
    cases = (
        replace(ctx, family=ConnectorMaterialFamily.STAINLESS_STEEL_316),
        replace(ctx, homogeneous_pultruded_l_angle=False),
        replace(ctx, material=replace(ctx.material, locked=False)),
        replace(ctx, material=replace(ctx.material, properties=())),
        replace(
            ctx, instep_property=replace(ctx.instep_property, adjusted_property=q("0", Unit.KSI))
        ),
        replace(ctx, instep_property=replace(ctx.instep_property, cm=D(0))),
        replace(
            ctx, instep_property=replace(ctx.instep_property, property_kind=FRPPropertyKind.FT_L)
        ),
        replace(
            ctx, instep_property=replace(ctx.instep_property, source_property=q("9", Unit.KSI))
        ),
        replace(
            ctx,
            instep_property=replace(
                ctx.instep_property, qualification_status=QualificationStatus.SOURCE_PENDING
            ),
        ),
        replace(
            ctx,
            material=replace(
                ctx.material,
                properties=(replace(ctx.material.properties[0], use_in_chapter_8_equations=False),),
            ),
        ),
    )
    for changed in cases:
        result = evaluate_angle_provider(core, "FRP", changed)
        assert result.status == "INVALID"
        assert detail(result).instep is None


def test_adjustment_applied_once_and_physical_end_cutbacks(core: AngleCoreResult) -> None:
    ctx = context()
    trace = adjust_frp_property(
        FRPPropertyKind.FSH_LT,
        ctx.instep_property.source_property,
        QualificationStatus.QUALIFIED,
        EndUseFactors(D("0.5"), D("0.8"), D(1), "test-adjustment", ("test-authority",)),
    )
    cut = resolve_angle_connector(
        replace(
            core.request, geometry=replace(core.request.geometry, heel_end_reliefs=(q("1"), q("2")))
        )
    )
    record = detail(evaluate_angle_provider(cut, "FRP", replace(ctx, instep_property=trace)))
    assert record.instep is not None
    assert record.instep.length == q("5")
    expected = Fraction(trace.adjusted_property.to(Unit.KSI).magnitude) * Fraction(7, 4)
    assert record.instep.factors.design_resistance.magnitude == exact_decimal(expected)
    # The inherited adjustment engine retains 60 digits; do not re-round its property.
    assert abs(record.instep.factors.design_resistance.magnitude - D("5.6")) < D("1e-55")
    assert record.instep.factors.property_traces == (trace,)
    assert record.instep.factors.lambda_factor == D(1)


@pytest.mark.parametrize(
    ("component", "unit"),
    [
        (0, Unit.KIP),
        (1, Unit.KIP),
        (2, Unit.KIP),
        (3, Unit.KIP_IN),
        (4, Unit.KIP_IN),
        (5, Unit.KIP_IN),
    ],
)
@pytest.mark.parametrize("sign", [1, -1])
def test_all_six_signed_strengths_boundaries_and_missing_sign(
    component: int, unit: Unit, sign: int
) -> None:
    # Zero lever arm isolates the requested signed component at the qualified heel reference.
    req = request()
    demand_values = ["0"] * 6
    demand_values[component] = str(sign)
    action = AngleWrench(
        vector(("0", "0", "0"), Unit.IN),
        vector(cast(tuple[str, str, str], tuple(demand_values[:3])), Unit.KIP),
        vector(cast(tuple[str, str, str], tuple(demand_values[3:])), Unit.KIP_IN),
    )
    core = resolve_angle_connector(replace(req, member_action=action))
    ctx = qualified(core, context())
    strengths = [SignedDesignStrength(None, None) for _ in range(6)]
    strengths[component] = SignedDesignStrength(
        q("1", unit) if sign > 0 else None, q("1", unit) if sign < 0 else None
    )
    src = replace(package(ctx), strengths=tuple(strengths))
    result = evaluate_angle_provider(core, "FRP", replace(ctx, qualified_source=src))
    assert result.status == REVIEW_PASS
    assert detail(result).body.utilization == D(1)
    assert detail(result).body.method == ENVELOPE_METHOD
    assert detail(result).body.interaction_method == INTERACTION_METHOD
    assert result.provider_id == FRP_PROVIDER_ID
    strengths[component] = SignedDesignStrength(q("0.999", unit), q("0.999", unit))
    fail = evaluate_angle_provider(
        core, "FRP", replace(ctx, qualified_source=replace(src, strengths=tuple(strengths)))
    )
    assert fail.status == "FAIL"
    strengths[component] = SignedDesignStrength(None, None)
    missing = evaluate_angle_provider(
        core, "FRP", replace(ctx, qualified_source=replace(src, strengths=tuple(strengths)))
    )
    assert missing.status == "NOT_EVALUATED_SIGNED_STRENGTH_REQUIRED"


def test_instep_limit_and_other_components_do_not_create_instep_capacity() -> None:
    req = request()
    for force, expected in (("22.4", True), ("22.4000000000000000000001", False), ("-22.4", True)):
        core = resolve_angle_connector(
            replace(
                req,
                member_action=replace(req.member_action, force=vector((force, "0", "0"), Unit.KIP)),
            )
        )
        result = evaluate_angle_provider(core, "FRP", context())
        record = detail(result).instep
        assert record is not None
        assert record.method == INSTEP_METHOD
        assert record.passed is expected
        assert result.status == ("SOURCE_REQUIRED" if expected else "FAIL")


def test_geometry_reference_input_and_provider_changes_have_distinct_identities(
    core: AngleCoreResult, ctx: FRPAngleContext
) -> None:
    req = request()
    changed_requests = (
        replace(req, geometry=replace(req.geometry, inside_radius=q("0.3"))),
        replace(req, support_reference=vector(("0", "0", "2.01"), Unit.IN)),
        replace(
            req,
            member_action=replace(
                req.member_action, moment=vector(("1.6", "-0.5", "1"), Unit.KIP_IN)
            ),
        ),
        replace(
            req,
            frame=AngleConnectorFrame((D(0), D(1), D(0)), (D(-1), D(0), D(0)), (D(0), D(0), D(1))),
        ),
    )
    for changed in changed_requests:
        assert resolve_angle_connector(changed).fingerprint != core.fingerprint
    original = evaluate_angle_provider(core, "FRP", ctx)
    for src in (
        replace(package(ctx), source=replace(package(ctx).source, revision="RC2-test-revision")),
        replace(package(ctx), linear_interaction_authorized=False),
    ):
        changed_result = evaluate_angle_provider(core, "FRP", replace(ctx, qualified_source=src))
        assert changed_result.fingerprint != original.fingerprint
        assert changed_result.core_fingerprint == original.core_fingerprint
