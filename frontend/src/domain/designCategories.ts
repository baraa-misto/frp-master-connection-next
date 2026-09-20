export const PRIMARY_DESIGN_CATEGORIES = [
  {
    id: "shear",
    name: "Shear Connections",
    description: "Non-moment-resisting beam, brace, splice, and support connections.",
  },
  {
    id: "moment",
    name: "Moment Connections",
    description:
      "Joint assemblies containing at least one intentionally moment-resisting member interface, including applicable shear.",
  },
] as const;

export type PrimaryCategoryId = (typeof PRIMARY_DESIGN_CATEGORIES)[number]["id"];

export const PRIMARY_CATEGORY_NAME_BY_ID: Readonly<Record<PrimaryCategoryId, string>> = {
  shear: "Shear Connections",
  moment: "Moment Connections",
};
