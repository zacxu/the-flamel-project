/** Display orientation only. Saved lattice vectors are rows, in Cartesian angstroms. */
import * as THREE from 'three';
import type { Matrix3 } from '../data/contracts';

export type LatticeViewPreset = 'iso' | 'a' | 'b' | 'c';
export const LATTICE_AXES = [
  { label: 'a', color: '#92522f' },
  { label: 'b', color: '#35658b' },
  { label: 'c', color: '#3f785b' },
] as const;

function latticeVectors(latticeRowsAngstrom: Matrix3): THREE.Vector3[] {
  const vectors = latticeRowsAngstrom.map(row => new THREE.Vector3(...row));
  const determinant = vectors[0].dot(new THREE.Vector3().crossVectors(vectors[1], vectors[2]));
  if (vectors.some(vector => !vector.toArray().every(Number.isFinite) || !Number.isFinite(vector.length()) || vector.length() <= 0) ||
    !Number.isFinite(determinant) || determinant === 0) throw new Error('Orientation requires a finite nonsingular saved lattice.');
  return vectors;
}

/** Camera offset from the cell centre toward +a/+b/+c, not a reciprocal-plane normal.
 * In nonorthogonal cells, looking along a vector is different from looking normal to its opposite cell face. */
export function latticeViewDirection(preset: LatticeViewPreset, latticeRowsAngstrom: Matrix3): THREE.Vector3 {
  const vectors = latticeVectors(latticeRowsAngstrom);
  if (preset === 'iso') return new THREE.Vector3(1.35, 1.05, 1.6).normalize();
  return vectors[{ a: 0, b: 1, c: 2 }[preset]].normalize();
}

/** Camera up projected perpendicular to the viewing direction, including views parallel to world Y. */
export function latticeViewUp(direction: THREE.Vector3): THREE.Vector3 {
  if (!direction.toArray().every(Number.isFinite) || !Number.isFinite(direction.length()) || direction.length() <= 0)
    throw new Error('A finite nonzero camera direction is required.');
  const normalized = direction.clone().normalize();
  const up = Math.abs(normalized.y) < 0.95 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
  return up.addScaledVector(normalized, -up.dot(normalized)).normalize();
}

export interface OrientationAxis {
  readonly label: 'x' | 'y' | 'z';
  readonly color: string;
  /** Unit screen-space vector. SVG uses downward-positive y; depth is toward the viewer. */
  readonly x: number;
  readonly y: number;
  readonly depth: number;
}

/** Project global Cartesian XYZ into the current camera frame for an optional SVG compass.
 * These are world axes; they must not be labelled a/b/c for a skew lattice. No extra animation owner is needed. */
export function cartesianOrientationAxes(cameraQuaternion: THREE.Quaternion): readonly OrientationAxis[] {
  const inverse = cameraQuaternion.clone().invert();
  return [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)].map((axis, index) => {
    axis.applyQuaternion(inverse);
    return { label: (['x', 'y', 'z'] as const)[index], color: LATTICE_AXES[index].color, x: axis.x, y: -axis.y, depth: axis.z };
  });
}

export interface AxisLabel {
  readonly sprite: THREE.Sprite;
  /** Disposes the label material and texture. */
  readonly dispose: () => void;
}
export type AxisLabelFactory = (label: string, color: string) => AxisLabel;

function canvasAxisLabel(label: string, color: string): AxisLabel {
  const canvas = document.createElement('canvas');
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('The lattice-axis label canvas is unavailable.');
  context.clearRect(0, 0, 128, 128);
  context.beginPath();
  context.arc(64, 64, 53, 0, Math.PI * 2);
  context.fillStyle = 'rgba(246,242,233,0.94)';
  context.fill();
  context.font = '700 83px system-ui, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillStyle = color;
  context.fillText(label, 64, 63);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  sprite.renderOrder = 20;
  return { sprite, dispose() { texture.dispose(); material.dispose(); } };
}

/** Physical a/b/c arrows start at saved cell origin and end at the exact saved row endpoints.
 * Labels sit just beyond those endpoints. This never transforms or adds physical sites.
 * The returned idempotent disposer owns every mesh geometry, material and label texture;
 * register it with the existing viewer resource scope. An optional factory permits headless geometry checks. */
export function makeLatticeAxes(latticeRowsAngstrom: Matrix3, createLabel: AxisLabelFactory = canvasAxisLabel): {
  readonly group: THREE.Group;
  readonly dispose: () => void;
} {
  const vectors = latticeVectors(latticeRowsAngstrom);
  const reference = Math.min(...vectors.map(vector => vector.length()));
  const group = new THREE.Group();
  group.name = 'Saved lattice a/b/c reference';
  const cleanups: (() => void)[] = [];
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    for (const cleanup of cleanups.reverse()) cleanup();
    group.removeFromParent();
    group.clear();
  };
  try {
    vectors.forEach((vector, index) => {
      const axis = LATTICE_AXES[index];
      const length = vector.length();
      const direction = vector.clone().normalize();
      const headLength = Math.min(reference * 0.16, length * 0.2);
      const shaftLength = length - headLength;
      const material = new THREE.MeshBasicMaterial({ color: axis.color });
      cleanups.push(() => material.dispose());
      const shaftGeometry = new THREE.CylinderGeometry(reference * 0.009, reference * 0.009, shaftLength, 10);
      cleanups.push(() => shaftGeometry.dispose());
      const headGeometry = new THREE.ConeGeometry(reference * 0.04, headLength, 12);
      cleanups.push(() => headGeometry.dispose());
      const shaft = new THREE.Mesh(shaftGeometry, material);
      const head = new THREE.Mesh(headGeometry, material);
      shaft.position.copy(direction).multiplyScalar(shaftLength / 2);
      head.position.copy(direction).multiplyScalar(length - headLength / 2);
      shaft.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
      head.quaternion.copy(shaft.quaternion);
      shaft.name = `${axis.label} lattice shaft`;
      head.name = `${axis.label} lattice arrowhead`;
      group.add(shaft, head);
      const label = createLabel(axis.label, axis.color);
      cleanups.push(() => label.dispose());
      label.sprite.position.copy(vector).addScaledVector(direction, reference * 0.11);
      label.sprite.scale.setScalar(reference * 0.22);
      label.sprite.name = `${axis.label} saved lattice vector`;
      group.add(label.sprite);
    });
    return { group, dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
