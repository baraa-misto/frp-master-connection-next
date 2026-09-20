import type { MultiRowQuantity } from "../api/multirowContracts";
import {
  SHARED_SUPPORT_OPTIONS,
  type SharedSupportProfileRequest,
  type SharedSupportTargetId,
} from "../api/sharedSupportContracts";
import { PROFILE_SURFACE_LABELS } from "./teeProfileOptions";

interface Props {
  readonly targetId: SharedSupportTargetId;
  readonly profile: SharedSupportProfileRequest;
  readonly onTargetChange: (target: SharedSupportTargetId) => void;
  readonly onProfileChange: (change: (profile: SharedSupportProfileRequest) => void) => void;
  readonly allowedTargets?: readonly SharedSupportTargetId[];
}

type SupportQuantityKey =
  | "member_length"
  | "depth"
  | "flange_width"
  | "web_thickness"
  | "flange_thickness"
  | "leg_y"
  | "leg_z"
  | "thickness"
  | "width"
  | "wall_thickness";

const TARGET_FIELDS: Readonly<
  Record<SharedSupportTargetId, readonly [SupportQuantityKey, string][]>
> = {
  W_COLUMN_FLANGE: [["member_length", "Support member / view length"], ["depth", "Support depth"], ["flange_width", "Support flange width"], ["web_thickness", "Support web thickness"], ["flange_thickness", "Support flange thickness"]],
  W_BEAM_FLANGE: [["member_length", "Support member / view length"], ["depth", "Support depth"], ["flange_width", "Support flange width"], ["web_thickness", "Support web thickness"], ["flange_thickness", "Support flange thickness"]],
  W_COLUMN_WEB: [["member_length", "Support member / view length"], ["depth", "Support depth"], ["flange_width", "Support flange width"], ["web_thickness", "Support web thickness"], ["flange_thickness", "Support flange thickness"]],
  CHANNEL_COLUMN_WEB: [["member_length", "Support member / view length"], ["depth", "Support depth"], ["flange_width", "Support flange width"], ["web_thickness", "Support web thickness"], ["flange_thickness", "Support flange thickness"]],
  ANGLE_COLUMN_LEG: [["member_length", "Support member / view length"], ["leg_y", "Support Leg Y"], ["leg_z", "Support Leg Z"], ["thickness", "Support thickness"]],
  RECTANGULAR_HOLLOW_COLUMN_WALL: [["member_length", "Support member / view length"], ["width", "Support outside width"], ["depth", "Support outside depth"], ["wall_thickness", "Support wall thickness"]],
  SOLID_RECTANGULAR_COLUMN_FACE: [["member_length", "Support member / view length"], ["width", "Support width"], ["depth", "Support depth"]],
};

const TARGET_SURFACES: Readonly<Record<SharedSupportTargetId, readonly SharedSupportProfileRequest["selected_profile_surface"][]>> = {
  W_COLUMN_FLANGE: ["FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  W_BEAM_FLANGE: ["FLANGE_POS_OUTER", "FLANGE_NEG_OUTER"],
  W_COLUMN_WEB: ["WEB_POS_FACE", "WEB_NEG_FACE"],
  CHANNEL_COLUMN_WEB: ["WEB_OUTER"],
  ANGLE_COLUMN_LEG: ["LEG_Y_OUTER", "LEG_Z_OUTER"],
  RECTANGULAR_HOLLOW_COLUMN_WALL: ["Z_POS_FACE", "Z_NEG_FACE", "Y_POS_FACE", "Y_NEG_FACE"],
  SOLID_RECTANGULAR_COLUMN_FACE: ["Z_POS_FACE", "Z_NEG_FACE", "Y_POS_FACE", "Y_NEG_FACE"],
};

function QuantityField({
  label,
  quantity,
  onChange,
}: {
  readonly label: string;
  readonly quantity: MultiRowQuantity;
  readonly onChange: (value: string) => void;
}) {
  return (
    <label className="field-control">
      <span>{label}</span>
      <span className="input-with-unit">
        <input
          aria-label={label}
          inputMode="decimal"
          type="text"
          value={quantity.value}
          onChange={(event) => {
            onChange(event.currentTarget.value);
          }}
        />
        <small>{quantity.unit}</small>
      </span>
    </label>
  );
}

export function SupportingMemberEditor({
  targetId,
  profile,
  onTargetChange,
  onProfileChange,
  allowedTargets,
}: Props) {
  const options = allowedTargets === undefined
    ? SHARED_SUPPORT_OPTIONS
    : SHARED_SUPPORT_OPTIONS.filter((option) => allowedTargets.includes(option.id));
  return (
    <>
      <label className="field-control">
        <span>Supporting member</span>
        <select
          aria-label="Supporting member"
          value={targetId}
          onChange={(event) => {
            onTargetChange(event.currentTarget.value as SharedSupportTargetId);
          }}
        >
          {options.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-control">
        <span>Selected contact face</span>
        <select
          aria-label="Support contact face"
          value={profile.selected_profile_surface}
          onChange={(event) => {
            const selectedSurface = event.currentTarget.value as SharedSupportProfileRequest["selected_profile_surface"];
            onProfileChange((next) => {
              next.selected_profile_surface = selectedSurface;
            });
          }}
        >
          {TARGET_SURFACES[targetId].map((surface) => (
            <option key={surface} value={surface}>
              {PROFILE_SURFACE_LABELS[surface]}
            </option>
          ))}
        </select>
      </label>
      {targetId === "ANGLE_COLUMN_LEG" ? (
        <label className="field-control">
          <span>Profile roll</span>
          <select
            aria-label="Support profile roll"
            value={profile.profile_orientation}
            onChange={(event) => {
              const orientation = event.currentTarget.value as SharedSupportProfileRequest["profile_orientation"];
              onProfileChange((next) => {
                next.profile_orientation = orientation;
              });
            }}
          >
            <option value="ROTATION_0">0°</option>
            <option value="ROTATION_90">90°</option>
            <option value="ROTATION_180">180°</option>
            <option value="ROTATION_270">270°</option>
          </select>
        </label>
      ) : null}
      <div className="field-grid">
        {TARGET_FIELDS[targetId].map(([key, label]) => {
          const quantity = profile[key];
          return quantity === undefined ? null : (
            <QuantityField
              key={key}
              label={label}
              quantity={quantity}
              onChange={(value) => {
                onProfileChange((next) => {
                  const current = next[key];
                  if (current !== undefined) current.value = value;
                });
              }}
            />
          );
        })}
      </div>
    </>
  );
}
