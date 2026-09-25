export const GRID_SPACING = 1;

export function gridNearest(value) {
  if (!Number.isFinite(value)) throw new TypeError("INVALID_GRID_VALUE");
  return Math.floor(value / GRID_SPACING + .5) * GRID_SPACING;
}

export function visibleGridLevels(projectedPixelsPerMm) {
  return {
    minor: projectedPixelsPerMm * GRID_SPACING >= 8,
    medium: projectedPixelsPerMm * GRID_SPACING * 10 >= 8,
    major: true,
  };
}
