import type { MultiRowQuantity } from "../api/multirowContracts";
import type {
  TeeConnectedMemberProfileRequest,
  TeeProfileFamily,
  TeeProfileOrientation,
  TeeProfileSurface,
} from "../api/teeContracts";
import { initialMultiMemberTeeProfile } from "../fixtures/multiMemberTeeBenchmarks";
import {
  PROFILE_SURFACE_LABELS,
  TEE_PROFILE_DEFINITIONS,
} from "./teeProfileOptions";

type SupportedFamily = Exclude<TeeProfileFamily, "ROUND_HOLLOW_SECTION">;

const PROFILE_FAMILIES: readonly SupportedFamily[] = [
  "FLAT_PLATE",
  "ANGLE",
  "CHANNEL",
  "WIDE_FLANGE_I",
  "RECTANGULAR_HOLLOW_SECTION",
  "SOLID_RECTANGULAR_SECTION",
];

interface Props {
  readonly label: string;
  readonly unitSystem: "US_CUSTOMARY" | "SI";
  readonly profile: TeeConnectedMemberProfileRequest;
  readonly onChange: (profile: TeeConnectedMemberProfileRequest) => void;
}

function QuantityField({
  label,
  value,
  onChange,
}: {
  readonly label: string;
  readonly value: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return (
    <label className="field-control">
      <span>{label}</span>
      <span className="input-with-unit">
        <input
          aria-label={label}
          inputMode="decimal"
          value={value.value}
          onChange={(event) => { onChange(event.currentTarget.value); }}
        />
        <small>{value.unit}</small>
      </span>
    </label>
  );
}

export function MultiMemberTeeProfileEditor({ label, unitSystem, profile, onChange }: Props) {
  const family = profile.profile_family as SupportedFamily;
  const definition = TEE_PROFILE_DEFINITIONS[family];
  const replace = (change: (next: TeeConnectedMemberProfileRequest) => void) => {
    const next = structuredClone(profile);
    change(next);
    onChange(next);
  };
  return (
    <section className="node-profile-editor" aria-label={`${label} profile`}>
      <h4>Connected profile</h4>
      <label className="field-control">
        <span>Profile family</span>
        <select
          aria-label={`${label} profile family`}
          value={family}
          onChange={(event) => {
            onChange(initialMultiMemberTeeProfile(
              event.currentTarget.value as SupportedFamily,
              unitSystem,
              profile.profile_id,
            ));
          }}
        >
          {PROFILE_FAMILIES.map((item) => (
            <option key={item} value={item}>{TEE_PROFILE_DEFINITIONS[item].label}</option>
          ))}
        </select>
      </label>
      <label className="field-control">
        <span>Profile roll</span>
        <select
          aria-label={`${label} profile roll`}
          value={profile.profile_orientation}
          onChange={(event) => {
            replace((next) => { next.profile_orientation = event.currentTarget.value as TeeProfileOrientation; });
          }}
        >
          <option value="ROTATION_0">0°</option>
          <option value="ROTATION_90">90°</option>
          <option value="ROTATION_180">180°</option>
          <option value="ROTATION_270">270°</option>
        </select>
      </label>
      <label className="field-control">
        <span>Contact face</span>
        <select
          aria-label={`${label} contact face`}
          value={profile.selected_profile_surface}
          onChange={(event) => {
            replace((next) => { next.selected_profile_surface = event.currentTarget.value as TeeProfileSurface; });
          }}
        >
          {definition.surfaces.map((surface) => (
            <option key={surface} value={surface}>{PROFILE_SURFACE_LABELS[surface]}</option>
          ))}
        </select>
      </label>
      <div className="field-grid">
        {definition.dimensions.map(({ key, label: dimensionLabel }) => {
          const value = profile.dimensions[key];
          return value === undefined ? null : (
            <QuantityField
              key={key}
              label={`${label} ${dimensionLabel}`}
              value={value}
              onChange={(nextValue) => {
                replace((next) => {
                  const dimension = next.dimensions[key];
                  /* v8 ignore else -- a rendered dimension control proves this key exists */
                  if (dimension !== undefined) dimension.value = nextValue;
                });
              }}
            />
          );
        })}
      </div>
    </section>
  );
}
