import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../src/api/wiWallMomentClient";
import type { WIWallMomentDesign, WIWallMomentResponse } from "../src/api/wiWallMomentContracts";
import { loadWIWallMomentBenchmark } from "../src/fixtures/wiWallMomentBenchmarks";
import { WIWallMomentWorkspace } from "../src/workspace/WIWallMomentWorkspace";
import { wallMomentVisibleFailures } from "../src/workspace/wiWallMomentFailures";
import { PREVIEW_DEBOUNCE_MS } from "../src/workspace/previewWorkflow";
import { wallDesignFixture, wallPureShearDesignFixture } from "./wiWallMomentFixtures";

vi.mock("../src/visualization/VisualizationPanel", () => ({VisualizationPanel: () => <div>Canonical viewer</div>}));
afterEach(() => {vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();});
const flush = async () => {await act(async () => {await Promise.resolve();});};
const readyPreview = () => vi.spyOn(client,"previewWIWallMoment").mockImplementation(request => {
  const design = request.actions.axial.value === "0" ? wallPureShearDesignFixture() : wallDesignFixture();
  return Promise.resolve({...design,resistance_evaluated:false,result:design.result.preview});
});
function required<T>(value:T | null | undefined):T { if(value == null) throw new Error("Required native fixture record missing"); return value; }
const emptyDesign = (): WIWallMomentDesign => ({...wallPureShearDesignFixture().result,status:"SOURCE_REQUIRED",
  native_failed_checks:[],web_bearing:[],flange_bearing:[],connector_results:[],attachment_results:[],common_web_bolts:[],local_checks:[]});

describe("Stage 4.2 sidebar correction", () => {
  it("keeps geometry, member bolts, wall anchors and source references in separate full-width groups", async () => {
    readyPreview(); const view=render(<WIWallMomentWorkspace/>); await screen.findByText("Canonical viewer");
    for (const family of ["Flange angles","Web clip angles"]) {
      const geometry=screen.getByLabelText(`${family} Inside Radius`);
      const body=geometry.closest(".sidebar-group-body");
      const member=screen.getByLabelText(`${family} Bolt diameter`).closest("fieldset");
      const wall=screen.getByLabelText(`${family} Anchor diameter`).closest("fieldset");
      expect(geometry.closest("fieldset")).toBeNull();
      expect(member?.parentElement).toBe(body); expect(wall?.parentElement).toBe(body);
      expect(member).not.toBe(wall); expect(member?.parentElement).not.toHaveClass("field-grid");
      expect(member?.querySelector("legend")).toHaveTextContent("Member bolts");
      expect(wall?.querySelector("legend")).toHaveTextContent("Wall anchors");
      for (const label of ["Member bolts across count","Member bolts along count","Member bolts gauge","Member bolts pitch","Member bolts centroid distance","Hole diameter","Thread condition"]) expect(member).toContainElement(screen.getByLabelText(`${family} ${label}`));
      for (const label of ["Wall anchors across count","Wall anchors along count","Wall anchors gauge","Wall anchors pitch","Wall anchors centroid distance","Anchor hole diameter","Anchor embedment"]) expect(wall).toContainElement(screen.getByLabelText(`${family} ${label}`));
      for (const label of ["Qualified connector source reference","Qualified member-attachment source reference"]) {
        const input=screen.getByLabelText(`${family} ${label}`);
        expect(input.closest("label")?.parentElement).toBe(body); expect(input.closest("fieldset")).toBeNull();
      }
    }
    expect(view.container.textContent).not.toMatch(/member_pattern|support_pattern/);
  });

  it("preserves exact input payloads and mirrored bindings after readable-label edits", async () => {
    vi.useFakeTimers(); const preview=readyPreview(); render(<WIWallMomentWorkspace/>); await flush();
    const expected=loadWIWallMomentBenchmark("US_CUSTOMARY");
    expect(preview.mock.calls[0]?.[0]).toEqual(expected);
    fireEvent.change(screen.getByLabelText("Flange angles Member bolts centroid distance"),{target:{value:"2.125"}});
    fireEvent.change(screen.getByLabelText("Flange angles Wall anchors across count"),{target:{value:"3"}});
    fireEvent.change(screen.getByLabelText("Web clip angles Qualified connector source reference"),{target:{value:"owner-source"}});
    expected.top.member_pattern.center.value="2.125"; expected.top.support_pattern.across=3;
    expected.bottom=structuredClone(expected.top);
    expected.positive_web.connector_source_reference="owner-source"; expected.negative_web=structuredClone(expected.positive_web);
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(preview.mock.calls.at(-1)?.[0]).toEqual(expected);
  });
});

describe("Stage 4.2 native failure traceability", () => {
  it("exposes all eight real pure-shear bearing failures without changing any native value or fingerprint", () => {
    const response=wallPureShearDesignFixture(), before=structuredClone(response);
    const rows=wallMomentVisibleFailures(response.result);
    expect(response.assembly_status).toBe("FAIL"); expect(response.result.native_failed_checks).toEqual([]);
    expect(response.result.native_governing_check_ids).toEqual([]);
    expect(rows.map(r=>r.checkId)).toEqual(response.result.web_bearing.filter(b=>b.comparison.numerical_comparison==="FAIL").map(b=>b.check_id));
    expect(rows).toHaveLength(8);
    expect(rows.find(r=>r.checkId==="BEARING:WI_WEB:COMMON_WEB:B_R1_L1")).toMatchObject({component:"WI_WEB",utilization:"2.14623947496383496776394125347462861449484568853006270253511",resistance:{value:"9007.6487709025125",unit:"N"}});
    expect(response).toEqual(before);
    expect(response.result_fingerprint).toBe("dc758641c2f59866c9ccc3f92d1d7bf13dba8fac6a7199b581105ca72534e4f1");
    const combined=wallDesignFixture();
    expect(wallMomentVisibleFailures(combined.result).slice(0,combined.result.native_failed_checks.length).map(r=>r.checkId)).toEqual(combined.result.native_failed_checks.map(c=>c.result_id));
    expect(combined.result.native_governing_check_ids).toEqual(["FIRST_ROW:TOP_FLANGE_ANGLE"]);
  });

  it("shows fresh pure shear as a supported native FAIL, not an empty table or missing-source override", async () => {
    vi.useFakeTimers(); readyPreview(); const design=vi.spyOn(client,"designWIWallMoment").mockResolvedValue(wallPureShearDesignFixture());
    render(<WIWallMomentWorkspace/>); await flush();
    fireEvent.change(screen.getByLabelText("Axial force P_L"),{target:{value:"0"}});
    fireEvent.change(screen.getByLabelText("Structural major moment M_T"),{target:{value:"0"}});
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    expect(design).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"})); await flush();
    expect(design.mock.calls[0]?.[0].actions).toEqual({axial:{value:"0",unit:"kip"},major_shear:{value:"-10",unit:"kip"},structural_major_moment:{value:"0",unit:"kip-in"}});
    expect(screen.getByText("Internal design: FAIL")).toBeInTheDocument();
    expect(screen.getByText(/Governing native group: None selected by the native group-mode engine/)).toBeInTheDocument();
    const trace=within(screen.getByRole("region",{name:"Design-check trace"}));
    expect(trace.getAllByRole("row")).toHaveLength(9);
    expect(trace.getByText("BEARING:WI_WEB:COMMON_WEB:B_R1_L1")).toBeInTheDocument();
    expect(trace.getByText(/Design result fingerprint: dc758641/)).toBeInTheDocument();
    expect(trace.getByText("POSITIVE_WEB_ANGLE:CONNECTOR_SOURCE:SOURCE_REQUIRED")).toBeInTheDocument();
  });

  it("hides combined results when edited and refuses superseded design responses after accepting pure shear", async () => {
    vi.useFakeTimers(); readyPreview();
    let late: ((r:WIWallMomentResponse<WIWallMomentDesign>)=>void)|undefined;
    const design=vi.spyOn(client,"designWIWallMoment").mockResolvedValueOnce(wallDesignFixture()).mockImplementationOnce(()=>new Promise(resolve=>{late=resolve;})).mockResolvedValue(wallPureShearDesignFixture());
    render(<WIWallMomentWorkspace/>); await flush();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"})); await flush();
    expect(screen.getByText("Governing native group: FIRST_ROW:TOP_FLANGE_ANGLE")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    fireEvent.change(screen.getByLabelText("Axial force P_L"),{target:{value:"0"}});
    fireEvent.change(screen.getByLabelText("Structural major moment M_T"),{target:{value:"0"}});
    expect(screen.getByText(/Design results are stale/)).toBeInTheDocument();
    expect(screen.queryByRole("region",{name:"Design-check trace"})).toBeNull();
    expect(design.mock.calls[1]?.[1].aborted).toBe(true);
    await act(async()=>{await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);});
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"})); await flush();
    await act(async()=>{late?.(wallDesignFixture()); await Promise.resolve();});
    expect(screen.getByText(/Governing native group: None selected/)).toBeInTheDocument();
    expect(screen.queryByText("FIRST_ROW:TOP_FLANGE_ANGLE")).toBeNull();
    expect(screen.getByText("BEARING:WI_WEB:COMMON_WEB:B_R1_L1")).toBeInTheDocument();
  });

  it("retains source-only status and gives explicit native reasons if an aggregate FAIL lacks individual records", async () => {
    readyPreview(); const sourceOnly={...wallPureShearDesignFixture(),assembly_status:"SOURCE_REQUIRED",result:emptyDesign()};
    const design=vi.spyOn(client,"designWIWallMoment").mockResolvedValueOnce(sourceOnly).mockResolvedValueOnce({...sourceOnly,result:{...sourceOnly.result,status:"FAIL",status_reason:"NATIVE_PROVIDER_FAILURE"}});
    render(<WIWallMomentWorkspace/>); await screen.findByText("Canonical viewer");
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByText("Internal design: SOURCE_REQUIRED")).toBeInTheDocument();
    expect(screen.getByText("No evaluated failures returned for this design.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
    fireEvent.click(screen.getByRole("button",{name:"Run Design Check"}));
    expect(await screen.findByText("Native aggregate status")).toBeInTheDocument();
    expect(screen.getByText(/NATIVE_PROVIDER_FAILURE — no individual failure record returned/)).toBeInTheDocument();
    expect(design).toHaveBeenCalledTimes(2);
  });

  it("projects provider/attachment/common-bolt failures with their native reasons, without inventing scalar demands", () => {
    // Transport-status cases only; these are not new engineering fixtures or strengths.
    const baseline=wallPureShearDesignFixture().result, empty=emptyDesign();
    const provider=required(baseline.connector_results[0]);
    const body={...required(provider.detail).body,status:"FAIL",utilization:"2"};
    const instep={...required(required(provider.detail).instep),passed:false};
    const value:WIWallMomentDesign={...empty,connector_results:[{...provider,status:"FAIL",detail:{body,instep}}, {...provider,core_fingerprint:"unmatched-native-core",status:"FAIL",reason:"NATIVE_REASON",detail:null}, {...provider,status:"FAIL",detail:{body:{...body,status:"SOURCE_REQUIRED"},instep:null}}],
      attachment_results:[{...required(baseline.attachment_results[0]),check:body}],
      common_web_bolts:[{...required(baseline.common_web_bolts[0]),status:"FAIL"}],
      local_checks:[{connector_id:"LOCAL",layer_id:"LAYER",scope_status:"FAIL"}],
      flange_bearing:[required(baseline.web_bearing[0])],
      native_failed_checks:[{result_id:"NATIVE_ID",limit_state:"NATIVE_LIMIT",utilization:null,demand:null,design_resistance:null,numerical_comparison:"FAIL"},{result_id:"NOT_FAILED",limit_state:"NATIVE_LIMIT",utilization:null,demand:null,design_resistance:null,numerical_comparison:"NOT_EVALUATED"}]};
    const rows=wallMomentVisibleFailures(value);
    expect(rows).toHaveLength(9);
    expect(rows[0]?.component).toBe("NATIVE_ID");
    expect(rows.find(r=>r.checkId===instep.method)?.resistance).toEqual(instep.factors.design_resistance);
    expect(rows.find(r=>r.component==="unmatched-native-core")?.reason).toBe("NATIVE_REASON");
    expect(rows.find(r=>r.checkId===baseline.common_web_bolts[0]?.bolt_id)?.demand).toBeNull();
    expect(rows.find(r=>r.checkId===body.method)?.nativeRecord).toEqual(body);
  });

  it("rejects missing or malformed failure transport instead of silently dropping a failure category", async () => {
    const fetcher=vi.fn(); vi.stubGlobal("fetch",fetcher);
    const good=wallPureShearDesignFixture();
    const bad=[{...good.result,web_bearing:undefined},{...good.result,flange_bearing:undefined},{...good.result,web_bearing:[{check_id:"bad"}]},{...good.result,connector_results:[{...good.result.connector_results[0],reason:undefined}]},{...good.result,attachment_results:[{...good.result.attachment_results[0],check:{status:"FAIL"}}]},{...good.result,common_web_bolts:[{bolt_id:"bad",status:"FAIL"}]}];
    for(const result of bad) {
      fetcher.mockResolvedValueOnce(new Response(JSON.stringify({...good,result})));
      await expect(client.designWIWallMoment(loadWIWallMomentBenchmark("US_CUSTOMARY"),new AbortController().signal)).rejects.toMatchObject({kind:"RESPONSE"});
    }
    fetcher.mockResolvedValueOnce(new Response(JSON.stringify(good)));
    expect(await client.designWIWallMoment(loadWIWallMomentBenchmark("US_CUSTOMARY"),new AbortController().signal)).toEqual(good);
  });
});
