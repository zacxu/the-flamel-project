import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SavedStage } from '../data/contracts';
import { cellEdges, fractionalToCartesian, geometryBounds, wrapFractional } from '../crystal/geometry';
import { createFailureGate, createFrameOwner, createResourceScope } from '../crystal/lifecycle';
import { fitDistanceForSphere } from '../crystal/camera';
import { cartesianOrientationAxes, latticeViewDirection, makeLatticeAxes, LATTICE_AXES } from '../crystal/orientation';
import CrystalViewerControls, { type CameraPreset } from './CrystalViewerControls';
import '../crystal/viewer.css';
import { useTourScene } from '../tour/TourContext';

interface CrystalViewerProps {
  record: SavedStage;
  elementColours: Readonly<Record<string, string>>;
  compact?: boolean;
  onFailure: (reason: string) => void;
}
interface ViewerActions {
  rotate: (horizontal: number, vertical: number) => void;
  zoom: (closer: boolean) => void;
  reset: () => void;
  preset: (preset: CameraPreset) => void;
  select: (position: number) => void;
  configure: (autoRotate: boolean, touchRotation: boolean, showAxes: boolean) => void;
}
const idleActions: ViewerActions = {
  rotate() {}, zoom() {}, reset() {}, preset() {}, select() {}, configure() {},
};

export default function CrystalViewer({ record, elementColours, compact = false, onFailure }: CrystalViewerProps) {
  const host = useRef<HTMLDivElement>(null);
  const compass = useRef<SVGSVGElement>(null);
  const actions = useRef<ViewerActions>(idleActions);
  const failureCallback = useRef(onFailure);
  failureCallback.current = onFailure;
  const configuration = useRef({ autoRotate: false, touchRotation: false, showAxes: true });
  const [status, setStatus] = useState<'preparing' | 'ready' | 'failed'>('preparing');
  const [cameraReadout, setCameraReadout] = useState<{ distance: number; azimuth: number; polar: number } | null>(null);
  const [selectedPosition, setSelectedPosition] = useState(0);
  const [autoRotate, setAutoRotate] = useState(false);
  const [touchRotation, setTouchRotation] = useState(false);
  const [showAxes, setShowAxes] = useState(true);
  const [activePreset, setActivePreset] = useState<CameraPreset | 'custom'>('isometric');
  const [reducedMotion, setReducedMotion] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const helpId = useId();
  const geometry = record.geometry;
  const tour = useTourScene();
  const tourOwnsRotation = useRef(false);
  useEffect(() => {
    if (tour.scene?.id === 'crystal-mgo') {
      tourOwnsRotation.current = true;
      setAutoRotate(tour.status === 'running' && !reducedMotion);
    } else if (tourOwnsRotation.current) {
      tourOwnsRotation.current = false;
      setAutoRotate(false);
    }
  }, [tour.scene?.id, tour.status, reducedMotion]);
  configuration.current = { autoRotate: autoRotate && !reducedMotion, touchRotation, showAxes };

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      setReducedMotion(preference.matches);
      if (preference.matches) setAutoRotate(false);
    };
    preference.addEventListener('change', update);
    update();
    return () => preference.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    const resources = createResourceScope();
    const fail = createFailureGate(() => resources.dispose(), reason => {
      actions.current = idleActions;
      setStatus('failed');
      failureCallback.current(reason);
    });
    setStatus('preparing');
    setCameraReadout(null);
    setSelectedPosition(0);
    setActivePreset('isometric');
    try {
      if (!geometry.sites.length || geometry.sites.length !== geometry.fractionalCoordinates.length ||
        geometry.actualAtoms !== geometry.sites.length) throw new Error('Saved physical site count is inconsistent.');
      const canvas = document.createElement('canvas');
      canvas.className = 'crystal-canvas';
      canvas.tabIndex = 0;
      canvas.setAttribute('role', 'application');
      canvas.setAttribute('aria-label', `Interactive saved crystal ${geometry.formula}, ${geometry.actualAtoms} physical sites`);
      canvas.setAttribute('aria-describedby', helpId);
      container.appendChild(canvas);
      resources.defer(() => canvas.remove());
      const context = canvas.getContext('webgl2', { alpha: true, antialias: true, powerPreference: 'low-power' });
      if (!context) throw new Error('WebGL 2 is unavailable on this browser or device.');
      // Register the context before renderer construction, which itself may throw.
      resources.defer(() => {
        if (!context.isContextLost()) context.getExtension('WEBGL_lose_context')?.loseContext();
      });
      const renderer = new THREE.WebGLRenderer({ canvas, context, alpha: true, antialias: true, powerPreference: 'low-power' });
      resources.defer(() => {
        renderer.renderLists.dispose();
        renderer.dispose();
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setClearColor(0xf2efe8, 1);
      const scene = new THREE.Scene();
      scene.add(new THREE.AmbientLight(0xffffff, 2));
      const light = new THREE.DirectionalLight(0xffffff, 3);
      light.position.set(1, 2, 3);
      scene.add(light);
      const wrapped = geometry.fractionalCoordinates.map(fractional => wrapFractional(fractional, geometry.pbc));
      const positions = wrapped.map(fractional => fractionalToCartesian(fractional, geometry.latticeRowsAngstrom));
      const bounds = geometryBounds(geometry.latticeRowsAngstrom, positions);
      const centre = new THREE.Vector3(...bounds.center);
      // Reference labels extend beyond the cell; pad only the camera framing.
      const axisPadding = Math.min(...geometry.latticeRowsAngstrom.map(row => Math.hypot(...row))) * 0.25;
      const radius = Math.max(bounds.radius + axisPadding, 0.1);
      const aspect = Math.max(1, container.clientWidth) / Math.max(1, container.clientHeight);
      const camera = new THREE.PerspectiveCamera(40, aspect, Math.max(0.001, radius / 1000), radius * 100);
      const initialDirection = new THREE.Vector3(1.35, 1.05, 1.6).normalize();
      const fitDistance = (viewportAspect: number) => fitDistanceForSphere(radius, viewportAspect);
      const initialDistance = fitDistance(aspect);
      let framingDistance = initialDistance;
      camera.position.copy(centre).addScaledVector(initialDirection, initialDistance);
      camera.lookAt(centre);
      // Capture before OrbitControls: ordinary touch keeps page pan; Ctrl+wheel opts into zoom.
      let pointerStart: { x: number; y: number } | null = null;
      const permitTouch = (event: PointerEvent) => {
        pointerStart = { x: event.clientX, y: event.clientY };
        if (event.pointerType === 'touch' && !configuration.current.touchRotation) event.stopImmediatePropagation();
      };
      const permitWheel = (event: WheelEvent) => {
        if (!event.ctrlKey && !event.metaKey) event.stopImmediatePropagation();
      };
      canvas.addEventListener('pointerdown', permitTouch, true);
      canvas.addEventListener('wheel', permitWheel, { capture: true, passive: true });
      resources.defer(() => canvas.removeEventListener('pointerdown', permitTouch, true));
      resources.defer(() => canvas.removeEventListener('wheel', permitWheel, true));
      const controls = new OrbitControls(camera, canvas);
      resources.defer(() => controls.dispose());
      controls.target.copy(centre);
      controls.enableDamping = false;
      controls.enablePan = false;
      controls.minDistance = radius * 1.2;
      controls.maxDistance = initialDistance * 4;
      controls.autoRotateSpeed = 0.6;
      controls.update();
      controls.saveState();
      const updateCameraReadout = () => setCameraReadout({
        distance: controls.getDistance(),
        azimuth: THREE.MathUtils.radToDeg(controls.getAzimuthalAngle()),
        polar: THREE.MathUtils.radToDeg(controls.getPolarAngle()),
      });
      controls.addEventListener('end', updateCameraReadout);
      resources.defer(() => controls.removeEventListener('end', updateCameraReadout));
      const startManualMovement = () => { setAutoRotate(false); setActivePreset('custom'); };
      controls.addEventListener('start', startManualMovement);
      resources.defer(() => controls.removeEventListener('start', startManualMovement));
      canvas.style.touchAction = configuration.current.touchRotation ? 'none' : 'pan-y';

      const edgeGeometry = new THREE.BufferGeometry().setFromPoints(
        cellEdges(geometry.latticeRowsAngstrom).flatMap(edge => edge.map(point => new THREE.Vector3(...point))));
      resources.defer(() => edgeGeometry.dispose());
      const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x56656d, transparent: true, opacity: 0.7 });
      resources.defer(() => edgeMaterial.dispose());
      scene.add(new THREE.LineSegments(edgeGeometry, edgeMaterial));
      const latticeAxes = makeLatticeAxes(geometry.latticeRowsAngstrom);
      resources.defer(latticeAxes.dispose);
      latticeAxes.group.visible = configuration.current.showAxes;
      scene.add(latticeAxes.group);
      const atomRadius = Math.max(0.13, Math.min(0.38, radius * 0.065));
      const siteGroups: THREE.Group[] = [];
      const pickable: THREE.Mesh[] = [];
      for (let position = 0; position < geometry.sites.length; position += 1) {
        const site = geometry.sites[position];
        const group = new THREE.Group();
        group.position.set(...positions[position]);
        scene.add(group);
        siteGroups.push(group);
        let occupiedFraction = 0;
        for (const item of site.species) {
          // Mixed occupancies retain their recorded fractions as coloured surface sectors.
          const meshGeometry = new THREE.SphereGeometry(atomRadius, 20, 14,
            occupiedFraction * Math.PI * 2, item.occupancy * Math.PI * 2);
          resources.defer(() => meshGeometry.dispose());
          occupiedFraction += item.occupancy;
          const material = new THREE.MeshStandardMaterial({
            color: elementColours[item.element] || '#69757d', roughness: 0.55, metalness: 0.08,
          });
          resources.defer(() => material.dispose());
          const mesh = new THREE.Mesh(meshGeometry, material);
          mesh.userData.sitePosition = position;
          mesh.userData.siteIndex = site.siteIndex;
          group.add(mesh);
          pickable.push(mesh);
        }
      }
      const selectionGeometry = new THREE.SphereGeometry(atomRadius * 1.25, 16, 10);
      resources.defer(() => selectionGeometry.dispose());
      const selectionMaterial = new THREE.MeshBasicMaterial({ color: 0x252f33, wireframe: true, transparent: true, opacity: 0.5 });
      resources.defer(() => selectionMaterial.dispose());
      const selection = new THREE.Mesh(selectionGeometry, selectionMaterial);
      selection.position.copy(siteGroups[0].position);
      scene.add(selection);
      let painted = false;
      const frames = createFrameOwner({
        requestFrame: callback => window.requestAnimationFrame(callback),
        cancelFrame: handle => window.cancelAnimationFrame(handle),
        render: delta => {
          controls.update(delta);
          for (const axis of cartesianOrientationAxes(camera.quaternion)) {
            const group = compass.current?.querySelector<SVGGElement>(`[data-cartesian-axis="${axis.label}"]`);
            const x = 48 + axis.x * 25;
            const y = 50 + axis.y * 25;
            const length = Math.hypot(axis.x, axis.y);
            group?.setAttribute('opacity', axis.depth < -0.1 ? '0.55' : '1');
            group?.querySelector('line')?.setAttribute('x2', x.toFixed(2));
            group?.querySelector('line')?.setAttribute('y2', y.toFixed(2));
            group?.querySelector('circle')?.setAttribute('cx', x.toFixed(2));
            group?.querySelector('circle')?.setAttribute('cy', y.toFixed(2));
            group?.querySelector('text')?.setAttribute('x', (x + (length > 0.1 ? axis.x / length * 10 : 0)).toFixed(2));
            group?.querySelector('text')?.setAttribute('y', (y + (length > 0.1 ? axis.y / length * 10 : -13)).toFixed(2));
          }
          renderer.render(scene, camera);
          if (!painted) { painted = true; setStatus('ready'); }
        },
        onError: () => fail('The interactive renderer could not draw this saved structure.'),
      });
      resources.defer(() => frames.dispose());
      const invalidate = () => frames.invalidate();
      controls.addEventListener('change', invalidate);
      resources.defer(() => controls.removeEventListener('change', invalidate));
      const resize = () => {
        if (resources.disposed) return;
        const width = Math.max(1, container.clientWidth);
        const height = Math.max(1, container.clientHeight);
        camera.aspect = width / height;
        const nextFramingDistance = fitDistance(camera.aspect);
        // Preserve the user's relative zoom while fitting the limiting viewport dimension.
        camera.position.sub(controls.target).multiplyScalar(nextFramingDistance / framingDistance).add(controls.target);
        framingDistance = nextFramingDistance;
        controls.maxDistance = framingDistance * 4;
        controls.position0.copy(centre).addScaledVector(initialDirection, framingDistance);
        controls.target0.copy(centre);
        camera.updateProjectionMatrix();
        controls.update(0);
        updateCameraReadout();
        renderer.setSize(width, height, false);
        frames.invalidate();
      };
      const observer = new ResizeObserver(resize);
      observer.observe(container);
      resources.defer(() => observer.disconnect());
      const intersection = new IntersectionObserver(entries => {
        frames.setVisible(entries.some(entry => entry.isIntersecting));
      });
      intersection.observe(container);
      resources.defer(() => intersection.disconnect());
      const visibility = () => frames.setHidden(document.hidden);
      document.addEventListener('visibilitychange', visibility);
      resources.defer(() => document.removeEventListener('visibilitychange', visibility));
      const contextLost = (event: Event) => fail('The browser lost its WebGL context. The saved figure remains available.', event);
      canvas.addEventListener('webglcontextlost', contextLost);
      resources.defer(() => canvas.removeEventListener('webglcontextlost', contextLost));
      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      const pick = (event: PointerEvent) => {
        const started = pointerStart;
        pointerStart = null;
        if (!started || Math.hypot(event.clientX - started.x, event.clientY - started.y) > 5) return;
        const rectangle = canvas.getBoundingClientRect();
        pointer.set((event.clientX - rectangle.left) / rectangle.width * 2 - 1,
          -(event.clientY - rectangle.top) / rectangle.height * 2 + 1);
        raycaster.setFromCamera(pointer, camera);
        const hit = raycaster.intersectObjects(pickable, false)[0];
        if (hit) setSelectedPosition(hit.object.userData.sitePosition as number);
      };
      // The capture listener above records touch taps without capturing the pointer.
      canvas.addEventListener('pointerup', pick);
      resources.defer(() => canvas.removeEventListener('pointerup', pick));
      actions.current = {
        rotate(horizontal, vertical) { controls.rotateLeft(horizontal); controls.rotateUp(vertical); controls.update(); updateCameraReadout(); frames.invalidate(); },
        zoom(closer) { if (closer) controls.dollyIn(1 / 1.2); else controls.dollyOut(1 / 1.2); controls.update(); updateCameraReadout(); frames.invalidate(); },
        reset() {
          controls.autoRotate = false;
          frames.setContinuous(false);
          controls.reset();
          updateCameraReadout(); frames.invalidate();
        },
        preset(preset) {
          controls.autoRotate = false;
          frames.setContinuous(false);
          if (preset === 'isometric') controls.reset();
          else {
            const distance = controls.getDistance();
            camera.position.copy(controls.target).addScaledVector(latticeViewDirection(preset, geometry.latticeRowsAngstrom), distance);
            // OrbitControls retains its fixed Y-up basis and safely clamps pole views.
            controls.update();
          }
          updateCameraReadout(); frames.invalidate();
        },
        select(position) {
          const group = siteGroups[position];
          if (group) { selection.position.copy(group.position); frames.invalidate(); }
        },
        configure(rotate, touch, axes) {
          controls.autoRotate = rotate;
          latticeAxes.group.visible = axes;
          canvas.style.touchAction = touch ? 'none' : 'pan-y';
          frames.setContinuous(rotate);
          updateCameraReadout();
          frames.invalidate();
        },
      };
      actions.current.configure(configuration.current.autoRotate, configuration.current.touchRotation, configuration.current.showAxes);
      visibility();
      resize();
      frames.invalidate();
      resources.defer(() => { actions.current = idleActions; });
    } catch (error) {
      fail(error instanceof Error ? error.message : 'The interactive renderer is unavailable.');
    }
    return () => { actions.current = idleActions; resources.dispose(); };
  }, [record, geometry, elementColours, helpId]);

  useEffect(() => { actions.current.select(selectedPosition); }, [selectedPosition, record]);
  useEffect(() => {
    actions.current.configure(autoRotate && !reducedMotion, touchRotation, showAxes);
  }, [autoRotate, reducedMotion, touchRotation, showAxes]);

  function rotateCamera(horizontal: number, vertical: number) {
    setAutoRotate(false); setActivePreset('custom');
    actions.current.rotate(horizontal, vertical);
  }
  function resetCamera() {
    setAutoRotate(false); setActivePreset('isometric'); actions.current.reset();
  }
  function setCameraPreset(preset: CameraPreset) {
    setAutoRotate(false); setActivePreset(preset); actions.current.preset(preset);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!(event.target instanceof HTMLCanvasElement)) return;
    const step = Math.PI / 12;
    switch (event.key) {
      case 'ArrowLeft': rotateCamera(step, 0); break;
      case 'ArrowRight': rotateCamera(-step, 0); break;
      case 'ArrowUp': rotateCamera(0, step); break;
      case 'ArrowDown': rotateCamera(0, -step); break;
      case '+': case '=': actions.current.zoom(true); break;
      case '-': case '_': actions.current.zoom(false); break;
      case 'Home': resetCamera(); break;
      default: return;
    }
    event.preventDefault();
  }
  return <div className={`crystal-viewer ${compact ? 'crystal-viewer-compact' : ''}`} data-viewer-stage={record.stageId}>
    <div className="crystal-viewport">
      <div className="crystal-surface" ref={host} onKeyDown={onKeyDown} />
      <div className="crystal-viewport-badge" role="status"><span aria-hidden="true" />{status === 'ready' ? 'Interactive 3D' : status === 'failed' ? 'View unavailable' : 'Preparing geometry…'}{status === 'ready' && <b>{geometry.actualAtoms} sites</b>}</div>
      {showAxes && status === 'ready' && <div className="crystal-lattice-key" aria-label="Lattice axis legend">{LATTICE_AXES.map(axis => <span key={axis.label} style={{ color: axis.color }}><i aria-hidden="true" />{axis.label}</span>)}<small>saved lattice</small></div>}
      <svg ref={compass} className="crystal-axis-compass" viewBox="0 0 96 100" role="img" aria-label="Cartesian viewer orientation: X, Y and Z" style={{ display: showAxes && status === 'ready' ? 'block' : 'none' }}>
        <rect x="1" y="1" width="94" height="98" rx="12" />
        <text className="crystal-compass-title" x="48" y="14">VIEWER XYZ</text>
        <circle className="crystal-compass-origin" cx="48" cy="50" r="2.5" />
        {(['x', 'y', 'z'] as const).map((axis, index) => <g key={axis} data-cartesian-axis={axis} style={{ color: LATTICE_AXES[index].color }}><line x1="48" y1="50" x2="48" y2="50" /><circle cx="48" cy="50" r="3" /><text x="48" y="50">{axis.toUpperCase()}</text></g>)}
        <text className="crystal-compass-note" x="48" y="92">camera reference</text>
      </svg>
    </div>
    <CrystalViewerControls record={record} elementColours={elementColours} compact={compact} status={status}
      selectedPosition={selectedPosition} onSelect={setSelectedPosition} cameraReadout={cameraReadout}
      autoRotate={autoRotate} onAutoRotate={enabled => { setAutoRotate(enabled); if (enabled) setActivePreset('custom'); }}
      touchRotation={touchRotation} onTouchRotation={setTouchRotation} reducedMotion={reducedMotion}
      onRotate={rotateCamera} onZoom={closer => actions.current.zoom(closer)} onReset={resetCamera}
      onPreset={setCameraPreset} activePreset={activePreset} showAxes={showAxes} onShowAxes={setShowAxes} helpId={helpId} />
  </div>;
}
