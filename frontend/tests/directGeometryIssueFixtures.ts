import type { DirectFaceClearance } from "../src/api/multirowContracts";

export const clearanceWitness: DirectFaceClearance = {
  bolt_id: "B_R2_L1", component_id: "member-a", physical_element_id: "TOP_FLANGE",
  surface_id: "TOP_FLANGE:TEST_PATCH", face_point_local: [".086", "2"],
  boundaries: [
    { boundary_id: "E1", start_local: ["0", "0"], end_local: ["8", "0"], distance: "2", dimension_end_local: [".086", "0"] },
    { boundary_id: "E2", start_local: ["8", "0"], end_local: ["8", "10"], distance: "7.914", dimension_end_local: ["8", "2"] },
    { boundary_id: "E3", start_local: ["8", "10"], end_local: ["0", "10"], distance: "8", dimension_end_local: [".086", "10"] },
    { boundary_id: "E4", start_local: ["0", "10"], end_local: ["0", "0"], distance: ".086", dimension_end_local: ["0", "2"] },
  ],
  controlling_boundary_id: "E4", center_to_boundary: ".086", bolt_radius: ".25",
  hole_radius: ".2815", washer_radius: ".5", chapter_8_minimum: ".75",
  validator_minimum: ".75", hole_ligament: "-.1955", washer_ligament: "-.414",
  plane_offset: "0", valid: false,
};
