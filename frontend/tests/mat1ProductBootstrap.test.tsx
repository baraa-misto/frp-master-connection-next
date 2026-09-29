import { render, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MAT1ProductBootstrap } from "../src/app/MAT1ProductBootstrap";
import * as mat1Service from "../src/api/mat1Service";
import { clearMAT1Sessions, mat1Snapshot } from "../src/state/mat1Session";

vi.mock("../src/app/App", () => ({ App: () => <div>Product application</div> }));

afterEach(() => { vi.unstubAllGlobals(); clearMAT1Sessions(); });

it("loads the catalog at the product mount and deactivates on unmount", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ contract: "MAT1-CATALOG-RC0", records: [{
    id: "ICE", revision: "RC0", content_digest: "digest", display_name: "ICE", properties: [],
  }] }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<MAT1ProductBootstrap />);
  await waitFor(() => { expect(mat1Snapshot().catalog[0]?.id).toBe("ICE"); });
  expect(mat1Snapshot().active).toBe(true);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  view.unmount();
  expect(mat1Snapshot().active).toBe(false);
});

it("shows service errors only while mounted and handles unknown errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  const first = render(<MAT1ProductBootstrap />);
  await waitFor(() => { expect(mat1Snapshot().catalogError).toContain("MAT1 service could not be reached"); });
  first.unmount();
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue("offline"));
  const second = render(<MAT1ProductBootstrap />);
  await waitFor(() => { expect(mat1Snapshot().catalogError).toBe("MAT1 service could not be reached."); });
  second.unmount();
});

it("suppresses late catalog results after unmount", async () => {
  let resolveResponse: ((value: Response) => void) | undefined;
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise<Response>((resolve) => { resolveResponse = resolve; })));
  const view = render(<MAT1ProductBootstrap />);
  view.unmount();
  resolveResponse?.(new Response(JSON.stringify({ contract: "MAT1-CATALOG-RC0", records: [{
    id: "LATE", revision: "RC0", content_digest: "digest", display_name: "late", properties: [],
  }] }), { status: 200 }));
  await Promise.resolve();
  expect(mat1Snapshot().catalog.some((record) => record.id === "LATE")).toBe(false);
});

it("suppresses a late catalog rejection after unmount", async () => {
  let rejectResponse: ((reason: Error) => void) | undefined;
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise<Response>((_resolve, reject) => { rejectResponse = reject; })));
  const view = render(<MAT1ProductBootstrap />);
  view.unmount();
  rejectResponse?.(new Error("late failure"));
  await Promise.resolve();
  expect(mat1Snapshot().catalogError).not.toBe("late failure");
});

it("shows a safe fallback if a service implementation rejects with a non-Error value", async () => {
  const service = vi.spyOn(mat1Service, "loadMAT1Catalog").mockRejectedValue("unexpected payload");
  try {
    const view = render(<MAT1ProductBootstrap />);
    await waitFor(() => { expect(mat1Snapshot().catalogError).toBe("Material catalog unavailable."); });
    view.unmount();
  } finally {
    service.mockRestore();
  }
});
