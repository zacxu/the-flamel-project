/** Distance enclosing a sphere in both axes of a perspective viewport, in the input length unit. */
export function fitDistanceForSphere(radius: number, aspect: number, verticalFovDegrees = 40, padding = 1.2): number {
  if (!Number.isFinite(radius) || radius <= 0 || !Number.isFinite(aspect) || aspect <= 0 ||
    !Number.isFinite(verticalFovDegrees) || verticalFovDegrees <= 0 || verticalFovDegrees >= 180 ||
    !Number.isFinite(padding) || padding < 1) throw new Error('Invalid crystal camera fit parameters.');
  const halfAngle = verticalFovDegrees * Math.PI / 360;
  const limitingHalfAngle = Math.atan(Math.tan(halfAngle) * Math.min(1, aspect));
  return radius / Math.sin(limitingHalfAngle) * padding;
}
