import { useId } from 'react';
import type { SavedStage } from '../data/contracts';
import '../crystal/controls.css';

/** Presets look toward the cell along its saved lattice vectors, not Cartesian x/y/z. */
export type CameraPreset = 'isometric' | 'a' | 'b' | 'c';
export interface CrystalViewerControlsProps {
  record: SavedStage;
  elementColours: Readonly<Record<string, string>>;
  status: 'preparing' | 'ready' | 'failed';
  selectedPosition: number;
  onSelect: (position: number) => void;
  autoRotate: boolean;
  onAutoRotate: (enabled: boolean) => void;
  touchRotation: boolean;
  onTouchRotation: (enabled: boolean) => void;
  reducedMotion: boolean;
  cameraReadout: { distance: number; azimuth: number; polar: number } | null;
  onRotate: (horizontal: number, vertical: number) => void;
  onZoom: (closer: boolean) => void;
  onReset: () => void;
  onPreset: (preset: CameraPreset) => void;
  activePreset?: CameraPreset | 'custom';
  compact?: boolean;
  showAxes: boolean;
  onShowAxes: (enabled: boolean) => void;
  /** Also referenced by the renderer canvas's aria-describedby. */
  helpId: string;
}

type IconName = 'left' | 'right' | 'up' | 'down' | 'plus' | 'minus' | 'reset' | 'cube' | 'rotate' | 'touch' | 'axes';
function ViewerIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, string> = {
    left: 'M19 12H5m6-6-6 6 6 6',
    right: 'M5 12h14m-6-6 6 6-6 6',
    up: 'M12 19V5m-6 6 6-6 6 6',
    down: 'M12 5v14m-6-6 6 6 6-6',
    plus: 'M5 12h14M12 5v14',
    minus: 'M5 12h14',
    reset: 'M4 11a8 8 0 1 1 2 7M4 5v6h6',
    cube: 'm12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 9v9M4 7.5l8 4.5 8-4.5',
    rotate: 'M4 9a8 8 0 0 1 14-3l2 3M20 3v6h-6M20 15a8 8 0 0 1-14 3l-2-3M4 21v-6h6',
    touch: 'M9 13V5a2 2 0 0 1 4 0v6l2-1 5 3-1 6-3 2h-5l-6-7a2 2 0 0 1 3-2l1 1Z',
    axes: 'M5 19V4m0 15h15M5 19l12-12M2 7l3-3 3 3m9 9 3 3-3 3M13 7h4v4',
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

const describeSpecies = (site: SavedStage['geometry']['sites'][number]) =>
  site.species.map(species => `${species.element} (occupancy ${species.occupancy})`).join(', ');
const displayCoordinate = (value: number) => {
  if (value === 0) return '0';
  if (Math.abs(value) < 0.000005) return '≈0';
  return Number(value.toPrecision(6)).toString();
};
const stageLabels: Record<SavedStage['stage'], string> = {
  generated: 'Generated geometry', prototype_initial: 'Initial prototype', catalog_initial: 'Catalog geometry',
  generated_excluded: 'Excluded generation', model_relaxed: 'CHGNet-relaxed geometry', accepted_dft: 'Accepted DFT geometry',
};

export default function CrystalViewerControls({
  record, elementColours, status, selectedPosition, onSelect, autoRotate, onAutoRotate,
  touchRotation, onTouchRotation, reducedMotion, cameraReadout, onRotate, onZoom, onReset,
  onPreset, activePreset = 'custom', compact = false, showAxes, onShowAxes, helpId,
}: CrystalViewerControlsProps) {
  const siteId = useId();
  const geometry = record.geometry;
  const site = geometry.sites[selectedPosition] || geometry.sites[0];
  const fractional = geometry.fractionalCoordinates[selectedPosition] || geometry.fractionalCoordinates[0];
  const species = [...new Set(geometry.sites.flatMap(item => item.species.map(part => part.element)))];
  const ready = status === 'ready';
  const step = Math.PI / 12;
  const directions = [
    { icon: 'left' as const, label: 'Rotate crystal left', horizontal: step, vertical: 0 },
    { icon: 'right' as const, label: 'Rotate crystal right', horizontal: -step, vertical: 0 },
    { icon: 'up' as const, label: 'Rotate crystal up', horizontal: 0, vertical: step },
    { icon: 'down' as const, label: 'Rotate crystal down', horizontal: 0, vertical: -step },
  ];
  return <div className={`crystal-control-dock${compact ? ' is-compact' : ''}`}>
    {!compact && <div className="crystal-view-summary"><span className="crystal-view-stage">{stageLabels[record.stage]} · {geometry.actualAtoms} physical sites</span></div>}

    <section className="crystal-camera-dock" aria-label="Crystal camera controls">
      <div className="crystal-dock-heading"><span>Explore the cell</span><small>Drag to rotate · select an atom to inspect</small></div>
      <div className="crystal-manual-controls">
        <div className="crystal-control-cluster crystal-rotation-cluster" role="group" aria-label="Rotate crystal">
          <span className="crystal-cluster-label">Rotate</span>
          <div className="crystal-rotation-pad">{directions.map(direction => <button key={direction.icon} type="button" className="crystal-dock-button crystal-arrow-button" disabled={!ready} aria-label={direction.label} title={direction.label} onClick={() => onRotate(direction.horizontal, direction.vertical)}><ViewerIcon name={direction.icon} /></button>)}</div>
        </div>
        <div className="crystal-control-cluster" role="group" aria-label="Zoom crystal">
          <span className="crystal-cluster-label">Zoom</span>
          <div className="crystal-zoom-controls"><button type="button" className="crystal-dock-button" disabled={!ready} aria-label="Zoom crystal in" title="Zoom in" onClick={() => onZoom(true)}><ViewerIcon name="plus" /></button><button type="button" className="crystal-dock-button" disabled={!ready} aria-label="Zoom crystal out" title="Zoom out" onClick={() => onZoom(false)}><ViewerIcon name="minus" /></button></div>
        </div>
        <div className="crystal-reset-control"><button type="button" className="crystal-dock-button crystal-reset-button" disabled={!ready} onClick={onReset}><ViewerIcon name="reset" /><span>Reset view</span></button><span>Restore the starting camera</span></div>
      </div>
      <div className="crystal-preset-row" role="group" aria-label="Camera presets">
        <span className="crystal-cluster-label">Quick views</span>
        <div className="crystal-preset-buttons"><button type="button" className="crystal-dock-button crystal-preset-button" disabled={!ready} aria-pressed={activePreset === 'isometric'} onClick={() => onPreset('isometric')}><ViewerIcon name="cube" />Isometric</button>{(['a', 'b', 'c'] as const).map(axis => <button key={axis} type="button" className={`crystal-dock-button crystal-preset-button axis-${axis}`} disabled={!ready} aria-label={`Look along lattice ${axis} axis`} aria-pressed={activePreset === axis} onClick={() => onPreset(axis)}>Along <b>{axis}</b></button>)}</div>
      </div>
      <div className="crystal-toggle-row" role="group" aria-label="Viewer preferences">
        <button type="button" className="crystal-toggle-button" aria-pressed={autoRotate && !reducedMotion} disabled={reducedMotion || !ready} onClick={() => onAutoRotate(!autoRotate)} title={reducedMotion ? 'Disabled by your reduced motion preference' : 'Toggle automatic rotation'}><ViewerIcon name="rotate" /><span>Auto-rotate</span><span className="crystal-toggle-indicator" aria-hidden="true" /></button>
        <button type="button" className="crystal-toggle-button" aria-label="Enable touch rotation" aria-pressed={touchRotation} disabled={!ready} onClick={() => onTouchRotation(!touchRotation)}><ViewerIcon name="touch" /><span>Touch rotate</span><span className="crystal-toggle-indicator" aria-hidden="true" /></button>
        <button type="button" className="crystal-toggle-button" aria-pressed={showAxes} disabled={!ready} onClick={() => onShowAxes(!showAxes)}><ViewerIcon name="axes" /><span>Lattice axes</span><span className="crystal-toggle-indicator" aria-hidden="true" /></button>
      </div>
      {reducedMotion && <p className="crystal-preference-note">Auto-rotation is off for your reduced motion preference.</p>}
    </section>

    {!compact && <section className="crystal-atom-card" aria-label="Physical site inspector">
      <div className="crystal-atom-heading"><label htmlFor={siteId}>Inspect an atom</label><ul className="crystal-element-key" aria-label="Element colour legend">{species.map(element => <li key={element}><span style={{ backgroundColor: elementColours[element] || '#69757d' }} aria-hidden="true" />{element}</li>)}</ul></div>
      <select id={siteId} value={selectedPosition} onChange={event => onSelect(Number(event.target.value))}>
        {geometry.sites.map((item, position) => <option value={position} key={item.siteIndex}>Site {item.siteIndex} · {describeSpecies(item)}</option>)}
      </select>
      {site && fractional && <div className="crystal-selected-site" aria-live="polite">
        <div className="crystal-site-meta"><strong>Site {site.siteIndex}</strong><span>{site.species.map(item => `${item.element} · occupancy ${item.occupancy}`).join(' / ')}</span></div>
        <dl className="crystal-coordinate-chips" aria-label="Saved fractional coordinates">{fractional.map((value, index) => <div key={index}><dt><span className={`axis-dot axis-${(['a', 'b', 'c'] as const)[index]}`} aria-hidden="true" />f{index + 1} <span>along {(['a', 'b', 'c'] as const)[index]}</span></dt><dd title={value.toString()}>{displayCoordinate(value)}</dd></div>)}</dl>
        <p className="crystal-coordinate-caption">Saved fractional coordinates · unitless · ≈0 means |f| &lt; 0.000005</p>
      </div>}
    </section>}

    {compact ? <p className="visually-hidden" id={helpId}>Drag with a mouse to rotate. Ctrl + wheel or the buttons zoom. Focus the canvas for arrow keys, + / − and Home. Touch scrolls the page until touch rotation is enabled. Lattice axes a, b and c follow the saved cell vectors.</p> : <details className="crystal-viewer-details"><summary>Controls, axis reference &amp; saved values</summary>
      <div className="crystal-details-content">
        <p id={helpId}>Drag with a mouse to rotate. Ctrl + wheel or the zoom buttons change the distance. Focus the canvas for arrow keys, + / − and Home. Touch scrolls the page until touch rotation is enabled.</p>
        <p><strong>Axis reference.</strong> <span className="axis-a">a</span>, <span className="axis-b">b</span> and <span className="axis-c">c</span> follow the saved lattice vectors; they need not be perpendicular. Fractional coordinates give each site's position in this basis. Quick views look from the positive end of the selected vector toward the cell centre. The corner XYZ compass shows the viewer's Cartesian axes as the camera moves.</p>
        {cameraReadout && <dl className="crystal-camera-metrics"><div><dt>Camera distance</dt><dd>{cameraReadout.distance.toFixed(3)} Å</dd></div><div><dt>Azimuth</dt><dd>{cameraReadout.azimuth.toFixed(1)}°</dd></div><div><dt>Polar angle</dt><dd>{cameraReadout.polar.toFixed(1)}°</dd></div></dl>}
        <p>Camera angles use the viewer's Cartesian frame. The readout updates after manual movement or when auto-rotation stops.</p>
        {site && fractional && <p className="crystal-raw-coordinates"><strong>Site {site.siteIndex}, unrounded saved values:</strong><code>({fractional.map(value => value.toString()).join(', ')})</code></p>}
        <p>Display only: coordinates wrap along periodic axes into the saved cell; no periodic image atoms are added. Saved coordinates and physical site IDs stay unchanged. Atom radii are schematic. No bonds or new geometry are inferred.</p>
      </div>
    </details>}
  </div>;
}
