import type { SavedStage } from '../data/contracts';
import { formatNumber } from './Shared';

/** Original saved coordinates remain available independently of WebGL. */
export function CrystalCoordinates({ record }: { record: SavedStage }) {
  return <details className="coordinate-details">
    <summary>Inspect saved lattice and fractional coordinates</summary>
    <p>Lattice vectors are rows in Å. Cartesian positions equal fractional coordinates × lattice. These are original saved values. The viewer wraps periodic coordinates into the cell for display only; no images or extra physical atoms are added.</p>
    <p className="small-text">Periodic axes: {record.geometry.pbc.map((value, index) => `${['a', 'b', 'c'][index]} ${value ? 'periodic' : 'not periodic'}`).join(' · ')}. Saved site indices are preserved. The CIF download retains full precision.</p>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Lattice vectors"><table><caption>Lattice row vectors · Å</caption><thead><tr><th scope="col">Vector</th><th scope="col">x</th><th scope="col">y</th><th scope="col">z</th></tr></thead><tbody>{record.geometry.latticeRowsAngstrom.map((vector, index) => <tr key={index}><th scope="row">{['a', 'b', 'c'][index]}</th>{vector.map((value, column) => <td key={column} className="numeric">{formatNumber(value, 8)}</td>)}</tr>)}</tbody></table></div>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Fractional atomic coordinates"><table><caption>Original saved sites · fractional coordinates (dimensionless)</caption><thead><tr><th scope="col">Saved site index</th><th scope="col">Species / occupancy</th><th scope="col">f₁</th><th scope="col">f₂</th><th scope="col">f₃</th></tr></thead><tbody>{record.geometry.sites.map((site, index) => <tr key={site.siteIndex}><th scope="row">{site.siteIndex}</th><td>{site.species.map(species => `${species.element} / ${formatNumber(species.occupancy, 3)}`).join(', ')}</td>{record.geometry.fractionalCoordinates[index].map((value, column) => <td key={column} className="numeric">{formatNumber(value, 8)}</td>)}</tr>)}</tbody></table></div>
  </details>;
}
