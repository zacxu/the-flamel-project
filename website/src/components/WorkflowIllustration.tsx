import { useId } from 'react';
import type { ReactNode } from 'react';
import type { CoreData } from '../data/ResearchData';
import { policyColour } from '../presentation/policyColours';

export type WorkflowIllustrationStage = 'propose' | 'generate' | 'screen' | 'select' | 'relax' | 'validate' | 'compare';
interface Props { readonly stage: WorkflowIllustrationStage; readonly data: CoreData }
interface Card { readonly label: string; readonly title: string; readonly description: ReactNode; readonly graphic: ReactNode }

const colour = {
  paper: '#f6f2e9', white: '#fffefa', ink: '#202a31', copper: '#92522f',
  blue: '#164b6b', paleBlue: '#e5edf1', paleCopper: '#efe1d4', line: '#d8d3c8', muted: '#52606a',
} as const;

function Diagram({ title, description, children, height = 140 }: { readonly title: string; readonly description: string; readonly children: ReactNode; readonly height?: 140 | 220 }) {
  const id = useId();
  return <svg className={`workflow-illustration-art${height === 220 ? ' workflow-illustration-art-tall' : ''}`} viewBox={`0 0 220 ${height}`} role="img" aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} style={{ fontFamily: 'system-ui, sans-serif', color: colour.ink }}>
    <title id={`${id}-title`}>{title}</title><desc id={`${id}-description`}>{description}</desc>
    {children}
  </svg>;
}

function Dot({ x, y, r = 8, fill = colour.copper, label }: { readonly x: number; readonly y: number; readonly r?: number; readonly fill?: string; readonly label?: string }) {
  return <g><circle cx={x} cy={y} r={r} fill={fill} stroke={colour.white} strokeWidth="2" />{label && <text x={x} y={y + 4} textAnchor="middle" fill={colour.white} fontSize="11" fontWeight="600">{label}</text>}</g>;
}

function Arrow({ x1, y1, x2, y2, stroke = colour.muted }: { readonly x1: number; readonly y1: number; readonly x2: number; readonly y2: number; readonly stroke?: string }) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const a = { x: x2 - 6 * Math.cos(angle - Math.PI / 6), y: y2 - 6 * Math.sin(angle - Math.PI / 6) };
  const b = { x: x2 - 6 * Math.cos(angle + Math.PI / 6), y: y2 - 6 * Math.sin(angle + Math.PI / 6) };
  return <g fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round"><path d={`M${x1} ${y1} L${x2} ${y2}`} /><path d={`M${a.x} ${a.y} L${x2} ${y2} L${b.x} ${b.y}`} /></g>;
}

function Cube({ atoms = false }: { readonly atoms?: boolean }) {
  return <g>
    <path d="M51 40 110 15 170 43 111 70Z M51 40v62l60 27 59-28V43 M111 70v59" fill={colour.paleBlue} fillOpacity=".35" stroke={colour.blue} strokeWidth="1.5" strokeLinejoin="round" />
    <path d="M51 102 110 76l60 25 M110 15v61" fill="none" stroke={colour.blue} strokeOpacity=".35" strokeWidth="1.5" strokeDasharray="4 4" />
    {atoms && <><Dot x={51} y={40} /><Dot x={110} y={15} fill={colour.blue} /><Dot x={170} y={43} /><Dot x={111} y={70} fill={colour.blue} /><Dot x={51} y={102} fill={colour.blue} /><Dot x={111} y={129} /><Dot x={170} y={101} fill={colour.blue} /><Dot x={110} y={76} /></>}
  </g>;
}

function TinyTree({ x, y }: { readonly x: number; readonly y: number }) {
  return <g transform={`translate(${x} ${y})`} stroke={colour.blue} strokeWidth="1.4" fill={colour.white}>
    <path d="M0 5v10m0 0-12 11m12-11 12 11m-12 0-7 10m7-10 7 10m12-10-7 10m7-10 7 10" fill="none" />
    <circle cy="5" r="4" fill={colour.blue} /><circle cx="-12" cy="26" r="3.5" /><circle cx="12" cy="26" r="3.5" />
    {[-19, -5, 5, 19].map((cx) => <circle key={cx} cx={cx} cy="37" r="2.5" fill={colour.copper} stroke="none" />)}
  </g>;
}

function Check({ x, y, muted = false }: { readonly x: number; readonly y: number; readonly muted?: boolean }) {
  return <g transform={`translate(${x} ${y})`}><circle r="9" fill={muted ? colour.paper : colour.paleBlue} stroke={muted ? colour.line : colour.blue} /><path d="m-4 0 3 3 5-6" fill="none" stroke={muted ? colour.line : colour.blue} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></g>;
}

export function WorkflowIllustration({ stage, data }: Props) {
  const captionId = useId();
  const counts = data.summary.counts;
  const quality = data.summary.policyStatistics.quality;
  const full = data.summary.policyStatistics.full;
  const n = (value: number) => value.toFixed(1);
  const content: Record<WorkflowIllustrationStage, { readonly title: string; readonly caption: string; readonly cards: readonly Card[] }> = {
    propose: {
      title: 'From oxide formulas to a bounded proposal set',
      caption: 'Simplified composition and catalog-check diagrams. A formula absent from the two pinned snapshots is new to those references; this does not establish global novelty or exclusion from CrystalFormer pretraining.',
      cards: [
        {
          label: '01 · Material family', title: 'Start with simple oxides',
          description: <>Metal elements and oxygen define the composition. CaMg₂O₃ is one recorded proposal.</>,
          graphic: <Diagram title="An oxide composition" description="Illustrative calcium, magnesium and oxygen symbols surround the formula CaMg2O3; this is a composition diagram, not an atomic structure.">
            <path d="M56 42 110 91 167 42" fill="none" stroke={colour.line} strokeWidth="2" /><Dot x={56} y={42} r={22} label="Ca" /><Dot x={167} y={42} r={22} fill={colour.blue} label="Mg" /><Dot x={110} y={91} r={23} fill={colour.muted} label="O" />
            <text x="110" y="136" textAnchor="middle" fill={colour.ink} fontSize="18" fontFamily="Georgia, serif">CaMg₂O₃</text>
          </Diagram>,
        },
        {
          label: '02 · Reference check', title: 'Check both frozen catalogs',
          description: <>Compare reduced compositions against the pinned Materials Project and WBM snapshots.</>,
          graphic: <Diagram title="Two separate snapshot checks" description="Two catalog sheets labeled MP and WBM each show zero matching composition records for CaMg2O3.">
            {[{ x: 23, name: 'MP' }, { x: 121, name: 'WBM' }].map(({ x, name }) => <g key={name}>
              <rect x={x} y="16" width="77" height="106" rx="3" fill={colour.white} stroke={colour.line} /><rect x={x} y="16" width="77" height="27" rx="3" fill={colour.paleBlue} /><text x={x + 38.5} y="35" textAnchor="middle" fill={colour.blue} fontSize="13" fontWeight="600">{name}</text>
              {[58, 69, 80].map((y) => <path key={y} d={`M${x + 13} ${y}h51`} stroke={colour.line} strokeWidth="2" />)}
              <text x={x + 38.5} y="108" textAnchor="middle" fill={colour.copper} fontSize="13" fontWeight="600">0 matches</text>
            </g>)}
          </Diagram>,
        },
        {
          label: '03 · Frozen scope', title: 'Keep proposals and controls distinct',
          description: <>Six new-to-reference formulas, with known controls and four prepared prototypes on separate branches.</>,
          graphic: <Diagram title="Six formula proposals on their own branch" description="Six copper proposal symbols are separated from two blue control symbols and four outlined prototype symbols.">
            <rect x="16" y="15" width="189" height="61" rx="5" fill={colour.paleCopper} />
            {[43, 77, 111, 145, 179].map((x) => <Dot key={x} x={x} y={35} r={6} />)}<Dot x={43} y={57} r={6} />
            <text x="132" y="62" textAnchor="middle" fill={colour.copper} fontSize="12">6 proposals</text>
            <path d="M16 88h189" stroke={colour.line} strokeDasharray="4 3" />
            <Dot x={35} y={113} r={8} fill={colour.blue} /><Dot x={57} y={113} r={8} fill={colour.blue} />
            {[116, 138, 160, 182].map((x) => <rect key={x} x={x - 6} y="107" width="12" height="12" fill={colour.white} stroke={colour.muted} />)}
          </Diagram>,
        },
      ],
    },
    generate: {
      title: 'A pretrained transformer samples a crystal',
      caption: 'Generalized CrystalFormer architecture: structured embeddings, causal attention/feed-forward blocks, and discrete/continuous output distributions. The diagram omits exact layer counts and implementation details. P1 and nontrivial symmetry conditioning use the same frozen pretrained model. The requested cell-size gate is checked after sampling.',
      cards: [
        {
          label: '01 · Structured representation', title: 'Embed composition, symmetry and sites',
          description: <>Composition and space-group conditioning accompany Wyckoff, element and fractional-coordinate tokens. Coordinates use periodic features.</>,
          graphic: <Diagram height={220} title="CrystalFormer structured inputs and embeddings" description="Formula and space group provide conditions. An earlier-site token sequence contains Wyckoff position, element and fractional x, y, z coordinates. Learned embeddings and periodic coordinate features feed the transformer. The requested cell count is not shown as a model condition.">
            <rect x="14" y="10" width="192" height="40" rx="3" fill={colour.white} stroke={colour.line} /><text x="110" y="28" textAnchor="middle" fill={colour.blue} fontSize="13">composition + space group</text><text x="110" y="43" textAnchor="middle" fill={colour.muted} fontSize="11">generation conditions</text>
            <Arrow x1={110} y1={55} x2={110} y2={69} />
            {['W', 'A', 'x', 'y', 'z'].map((label, index) => <g key={label}><rect x={14 + index * 39} y="76" width="34" height="30" rx="2" fill={index < 2 ? colour.paleCopper : colour.paleBlue} stroke={index < 2 ? colour.copper : colour.blue} /><text x={31 + index * 39} y="96" textAnchor="middle" fill={colour.ink} fontSize="14">{label}</text></g>)}
            <text x="110" y="125" textAnchor="middle" fill={colour.muted} fontSize="12">earlier sites · token sequence</text><Arrow x1={110} y1={134} x2={110} y2={149} />
            <rect x="14" y="156" width="192" height="52" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><text x="110" y="177" textAnchor="middle" fill={colour.blue} fontSize="13" fontWeight="600">embeddings + projection</text><text x="110" y="196" textAnchor="middle" fill={colour.blue} fontSize="11">periodic coordinate features</text>
          </Diagram>,
        },
        {
          label: '02 · Repeated transformer blocks', title: 'Attend to earlier tokens, then transform',
          description: <>Causal multi-head attention masks future tokens. Feed-forward blocks, layer normalization and residual connections refine the representation.</>,
          graphic: <Diagram height={220} title="Generalized causal transformer block" description="A causal lower-triangular attention mask allows earlier and current tokens but excludes future tokens. Multi-head attention and a feed-forward network use layer normalization and residual additions. The block repeats, without specifying an exact layer count.">
            <text x="110" y="15" textAnchor="middle" fill={colour.muted} fontSize="11">layer normalization</text><Arrow x1={110} y1={20} x2={110} y2={29} />
            <rect x="29" y="34" width="174" height="69" rx="3" fill={colour.paleBlue} stroke={colour.blue} />
            {Array.from({ length: 16 }, (_, index) => { const row = Math.floor(index / 4); const col = index % 4; return <rect key={index} x={42 + col * 10} y={47 + row * 10} width="8" height="8" fill={col <= row ? colour.blue : colour.line} />; })}
            <text x="139" y="55" textAnchor="middle" fill={colour.blue} fontSize="12" fontWeight="600">multi-head</text><text x="139" y="72" textAnchor="middle" fill={colour.blue} fontSize="12" fontWeight="600">self-attention</text><text x="139" y="91" textAnchor="middle" fill={colour.muted} fontSize="10">future tokens masked</text>
            <path d="M17 18v95h83" fill="none" stroke={colour.copper} strokeWidth="1.4" /><Arrow x1={110} y1={105} x2={110} y2={112} /><circle cx="110" cy="117" r="8" fill={colour.white} stroke={colour.copper} /><text x="110" y="121" textAnchor="middle" fill={colour.copper} fontSize="14">+</text>
            <text x="110" y="144" textAnchor="middle" fill={colour.muted} fontSize="11">layer normalization</text><rect x="29" y="153" width="174" height="30" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><text x="116" y="173" textAnchor="middle" fill={colour.blue} fontSize="13">feed-forward network</text>
            <path d="M17 127v72h83" fill="none" stroke={colour.copper} strokeWidth="1.4" /><Arrow x1={110} y1={187} x2={110} y2={193} /><circle cx="110" cy="199" r="8" fill={colour.white} stroke={colour.copper} /><text x="110" y="203" textAnchor="middle" fill={colour.copper} fontSize="14">+</text><text x="171" y="211" textAnchor="middle" fill={colour.muted} fontSize="10">repeat block</text>
          </Diagram>,
        },
        {
          label: '03 · Distribution heads + assembly', title: 'Sample sites, expand symmetry and build a cell',
          description: <>Discrete site/element and continuous coordinate/lattice distributions supply the crystal. <span className="workflow-illustration-metric">{counts.actualCrystalFormerDraws} draws</span> were saved across all cohorts.</>,
          graphic: <Diagram height={220} title="CrystalFormer discrete and continuous distributions and crystal assembly" description="The output representation produces discrete Wyckoff and element probabilities and continuous coordinate and lattice distributions. Sampled sites are expanded by symmetry to assemble a periodic crystal. The illustrated distribution shapes and crystal are conceptual.">
            <rect x="12" y="10" width="92" height="86" rx="3" fill={colour.white} stroke={colour.line} /><rect x="116" y="10" width="92" height="86" rx="3" fill={colour.white} stroke={colour.line} />
            <text x="58" y="29" textAnchor="middle" fill={colour.blue} fontSize="12">discrete</text><text x="162" y="29" textAnchor="middle" fill={colour.copper} fontSize="12">continuous</text>
            {[15, 29, 20, 8].map((h, index) => <rect key={index} x={29 + index * 15} y={68 - h} width="9" height={h} fill={colour.blue} />)}<path d="M129 68c10 0 10-29 21-29s12 29 19 29 7-19 16-19 8 19 10 19" fill="none" stroke={colour.copper} strokeWidth="2" />
            <text x="58" y="85" textAnchor="middle" fill={colour.muted} fontSize="10">Wyckoff · element</text><text x="162" y="85" textAnchor="middle" fill={colour.muted} fontSize="10">coordinates · lattice</text>
            <path d="M58 100 110 115 162 100" fill="none" stroke={colour.line} strokeWidth="1.5" /><text x="110" y="134" textAnchor="middle" fill={colour.blue} fontSize="12">sample + symmetry expansion</text>
            <g transform="translate(67 142) scale(.4)"><Cube atoms /></g><text x="110" y="214" textAnchor="middle" fill={colour.muted} fontSize="11">periodic cell → eligibility gate</text>
          </Diagram>,
        },
      ],
    },
    screen: {
      title: 'The cell gate determines what can proceed',
      caption: 'Simplified eligibility checks grounded in the saved generation audit. The six-formula branch stops at 0/48 eligible draws. The separate known-MgO control and prepared-prototype branches continue independently.',
      cards: [
        {
          label: '01 · Structural checks', title: 'Inspect the generated cell',
          description: <>Check species counts, requested cell size, lattice and geometric validity against the frozen rules.</>,
          graphic: <Diagram title="Structural screening checklist" description="Three checklist rows represent composition counts, exact cell size and geometry checks; no individual candidate is claimed to pass all checks.">
            <g transform="translate(-20 -4) scale(.65)"><Cube /></g>
            {[{ y: 30, label: 'Species counts' }, { y: 70, label: 'Exact cell' }, { y: 110, label: 'Geometry' }].map(({ y, label }) => <g key={label}><rect x="100" y={y - 13} width="108" height="27" rx="3" fill={colour.white} stroke={colour.line} /><text x="154" y={y + 4} textAnchor="middle" fill={colour.blue} fontSize="12">{label}</text></g>)}
          </Diagram>,
        },
        {
          label: '02 · Exact-cell example', title: 'A reduced formula is insufficient',
          description: <>A twelve-atom CaMg₂O₃ draw has the right ratio but fails the requested six-atom cell gate.</>,
          graphic: <Diagram title="Six requested atoms versus twelve generated atoms" description="A six-dot requested cell is compared with a twelve-dot generated cell. A cross marks the cell-size mismatch.">
            <rect x="12" y="19" width="78" height="90" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><rect x="130" y="19" width="78" height="90" rx="3" fill={colour.paleCopper} stroke={colour.copper} />
            {Array.from({ length: 6 }, (_, i) => <Dot key={`six-${i}`} x={35 + (i % 2) * 31} y={39 + Math.floor(i / 2) * 25} r={5} fill={colour.blue} />)}
            {Array.from({ length: 12 }, (_, i) => <Dot key={`twelve-${i}`} x={145 + (i % 3) * 23} y={32 + Math.floor(i / 3) * 21} r={4.5} />)}
            <path d="m103 56 14 14m0-14-14 14" stroke={colour.copper} strokeWidth="2" /><text x="51" y="130" textAnchor="middle" fill={colour.blue} fontSize="12">6 requested</text><text x="169" y="130" textAnchor="middle" fill={colour.copper} fontSize="12">12 generated</text>
          </Diagram>,
        },
        {
          label: '03 · Recorded outcome', title: 'No eligible new-formula shortlist',
          description: <><span className="workflow-illustration-metric">{counts.newFormulaExactValid}/{counts.newFormulaDraws} eligible</span> with {counts.excludedNewFormulaLargerCellDiagnostics} larger-cell diagnostics kept excluded.</>,
          graphic: <Diagram title="The new-formula branch stops before candidate DFT" description="Forty-eight new-formula draws reach an eligibility gate; zero are eligible, so this branch has no fresh candidate DFT.">
            {Array.from({ length: 48 }, (_, i) => <circle key={i} cx={21 + (i % 8) * 10} cy={33 + Math.floor(i / 8) * 12} r="2.7" fill={colour.copper} opacity=".55" />)}
            <path d="M115 18v88" stroke={colour.blue} strokeWidth="3" /><Arrow x1={99} y1={65} x2={111} y2={65} />
            <text x="165" y="73" textAnchor="middle" fill={colour.copper} fontSize="43" fontFamily="Georgia, serif">0</text><path d="M139 94h52" stroke={colour.copper} strokeWidth="2" /><text x="110" y="131" textAnchor="middle" fill={colour.muted} fontSize="12">new-formula path ends here</text>
          </Diagram>,
        },
      ],
    },
    select: {
      title: 'Use uncertainty as a selection signal',
      caption: 'Simplified historical-selector diagram. The five bootstrapped ExtraTrees members are separate from CrystalFormer and CHGNet. The historical replay reveals existing WBM targets; no fresh QE result is fed back into these hull-distance labels.',
      cards: [
        {
          label: '01 · Ensemble predictor', title: 'Five bootstrap members',
          description: <>Each ExtraTrees member contains 128 trees and uses 408 initial-geometry and composition descriptors.</>,
          graphic: <Diagram title="A five-member ExtraTrees ensemble" description="Five tree icons represent five outer-bootstrap ensemble members, each containing 128 trees; these are not five individual fitted trees.">
            {[37, 110, 183].map((x) => <TinyTree key={x} x={x} y={17} />)}{[73, 147].map((x) => <TinyTree key={x} x={x} y={78} />)}
            <path d="M35 68h150" stroke={colour.line} strokeDasharray="3 4" />
          </Diagram>,
        },
        {
          label: '02 · Predictive signals', title: 'Mean and calibrated disagreement',
          description: <>Use predicted hull distance and interval radius q × max(disagreement, 0.01 eV/atom).</>,
          graphic: <Diagram title="A mean prediction with a calibrated interval" description="An illustrative horizontal interval around an ensemble mean, with five member prediction ticks. Its position and width are conceptual, not a candidate prediction.">
            <path d="M24 88h172" stroke={colour.line} strokeWidth="1.5" /><path d="M51 57h117 M51 46v22 M168 46v22" stroke={colour.blue} strokeWidth="2" />
            {[82, 98, 108, 121, 129].map((x) => <path key={x} d={`M${x} 82v12`} stroke={colour.copper} strokeWidth="2" />)}<Dot x={110} y={57} r={8} fill={colour.blue} />
            <text x="110" y="29" textAnchor="middle" fill={colour.blue} fontSize="13">calibrated interval</text><text x="110" y="119" textAnchor="middle" fill={colour.muted} fontSize="12">historical hull-distance target</text>
          </Diagram>,
        },
        {
          label: '03 · Acquisition', title: 'Balance three selection signals',
          description: <>Quality, uncertainty and diversity inform the Full policy. Five policies each receive 50 historical queries per split.</>,
          graphic: <Diagram title="Three signals used for historical acquisition" description="Quality, uncertainty and diversity signals connect to a historical batch selection, followed by saved label reveal.">
            {[{ x: 36, label: 'Q' }, { x: 110, label: 'U' }, { x: 184, label: 'D' }].map(({ x, label }) => <g key={label}><Dot x={x} y={28} r={17} fill={label === 'Q' ? colour.blue : colour.copper} label={label} /><path d={`M${x} 48 110 76`} stroke={colour.line} strokeWidth="1.5" /></g>)}
            <rect x="45" y="77" width="130" height="29" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><text x="110" y="96" textAnchor="middle" fill={colour.blue} fontSize="12">select historical batch</text><text x="110" y="130" textAnchor="middle" fill={colour.muted} fontSize="12">then reveal saved labels</text>
          </Diagram>,
        },
      ],
    },
    relax: {
      title: 'A learned potential relaxes selected structures',
      caption: 'Generalized CHGNet architecture: a periodic atom graph and auxiliary bond graph encode local distances and angles; coupled message updates yield site-energy contributions. Forces and stress are energy derivatives used by FIRE. These are architecture schematics, not saved geometries or observed trajectories. CHGNet estimates remain separate from QE energies.',
      cards: [
        {
          label: '01 · Atom + auxiliary bond graph', title: 'Represent neighbors, distances and angles',
          description: <>Atoms and neighbor bonds form the crystal graph. An auxiliary graph treats bonds as nodes and connects bond pairs through their angles.</>,
          graphic: <Diagram height={220} title="CHGNet atom graph and auxiliary bond graph" description="Three schematic atoms and their neighbor bonds form part of a periodic atom graph. Two bonds sharing a central atom become two nodes in an auxiliary bond graph; their connecting edge encodes the bond angle. This does not depict three independent graphs or saved coordinates.">
            <text x="110" y="17" textAnchor="middle" fill={colour.blue} fontSize="12">periodic atom neighbors</text>
            <path d="M34 93 104 41 181 87" fill="none" stroke={colour.blue} strokeWidth="3" /><path d="M86 55q18 25 39 0" fill="none" stroke={colour.copper} strokeWidth="1.5" /><text x="107" y="79" textAnchor="middle" fill={colour.copper} fontSize="14">θ</text>
            <Dot x={34} y={93} r={12} /><Dot x={104} y={41} r={13} fill={colour.blue} /><Dot x={181} y={87} r={12} />
            <path d="M69 67 55 146 M143 64 165 146" fill="none" stroke={colour.line} strokeDasharray="4 4" strokeWidth="1.5" />
            <path d="M58 165h105" stroke={colour.copper} strokeWidth="2" /><circle cx="58" cy="165" r="17" fill={colour.paleBlue} stroke={colour.blue} /><circle cx="163" cy="165" r="17" fill={colour.paleBlue} stroke={colour.blue} />
            <text x="58" y="169" textAnchor="middle" fill={colour.blue} fontSize="12">bond</text><text x="163" y="169" textAnchor="middle" fill={colour.blue} fontSize="12">bond</text><text x="110" y="154" textAnchor="middle" fill={colour.copper} fontSize="13">θ</text>
            <text x="110" y="207" textAnchor="middle" fill={colour.muted} fontSize="12">bond graph · angle connections</text>
          </Diagram>,
        },
        {
          label: '02 · Coupled graph network', title: 'Exchange local messages and read out energy',
          description: <>Embedded atom, bond and angle features pass through coupled updates. Site-energy contributions are pooled into the total energy.</>,
          graphic: <Diagram height={220} title="Generalized CHGNet embeddings, coupled messages and energy readout" description="Atom, bond and angle feature embeddings enter coupled graph message updates. Atom and bond states exchange information; angular information updates bond environments. A site-energy readout and pooling produce total energy. No exact layer count is specified.">
            <text x="110" y="14" textAnchor="middle" fill={colour.muted} fontSize="11">atom · bond · angle embeddings</text>
            <Arrow x1={110} y1={20} x2={110} y2={34} /><rect x="14" y="41" width="192" height="82" rx="4" fill={colour.paleBlue} stroke={colour.blue} />
            <rect x="29" y="53" width="63" height="27" rx="3" fill={colour.white} stroke={colour.blue} /><rect x="128" y="53" width="63" height="27" rx="3" fill={colour.white} stroke={colour.blue} /><text x="60" y="71" textAnchor="middle" fill={colour.blue} fontSize="12">atoms</text><text x="160" y="71" textAnchor="middle" fill={colour.blue} fontSize="12">bonds</text><Arrow x1={96} y1={60} x2={123} y2={60} /><Arrow x1={123} y1={73} x2={96} y2={73} />
            <text x="61" y="106" textAnchor="middle" fill={colour.copper} fontSize="12">angles</text><Arrow x1={91} y1={101} x2={150} y2={86} /><text x="160" y="111" textAnchor="middle" fill={colour.muted} fontSize="10">repeat updates</text>
            <Arrow x1={110} y1={127} x2={110} y2={140} /><rect x="26" y="147" width="168" height="28" rx="3" fill={colour.white} stroke={colour.line} /><text x="110" y="166" textAnchor="middle" fill={colour.blue} fontSize="13">site-energy readout Eᵢ</text>
            <Arrow x1={110} y1={180} x2={110} y2={189} /><text x="110" y="211" textAnchor="middle" fill={colour.copper} fontSize="15" fontWeight="600">pool: E = Σ Eᵢ</text>
          </Diagram>,
        },
        {
          label: '03 · Derivatives + optimizer', title: 'Relax positions and cell with FIRE',
          description: <><span className="workflow-illustration-metric">{counts.modelSelectedStructures} converged</span> results, including one verified cached reuse, across controls, references and prototypes.</>,
          graphic: <Diagram height={220} title="Energy derivatives drive FIRE relaxation" description="Total model energy is differentiated with respect to atom positions and strain to obtain forces and stress. FIRE uses those derivatives to update positions and cell, then the model evaluates the updated geometry. This is a conceptual optimization loop, not a recorded trajectory or DFT calculation.">
            <rect x="55" y="8" width="110" height="31" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><text x="110" y="29" textAnchor="middle" fill={colour.blue} fontSize="14">total energy E</text>
            <Arrow x1={110} y1={44} x2={56} y2={61} /><Arrow x1={110} y1={44} x2={165} y2={61} />
            <rect x="12" y="69" width="93" height="45" rx="3" fill={colour.white} stroke={colour.line} /><rect x="115" y="69" width="93" height="45" rx="3" fill={colour.white} stroke={colour.line} /><text x="58" y="87" textAnchor="middle" fill={colour.copper} fontSize="13">forces</text><text x="58" y="104" textAnchor="middle" fill={colour.muted} fontSize="11">−∂E / ∂r</text><text x="162" y="87" textAnchor="middle" fill={colour.copper} fontSize="13">stress</text><text x="162" y="104" textAnchor="middle" fill={colour.muted} fontSize="10">strain derivative</text>
            <Arrow x1={58} y1={119} x2={94} y2={137} /><Arrow x1={162} y1={119} x2={126} y2={137} />
            <rect x="28" y="145" width="164" height="40" rx="3" fill={colour.paleCopper} stroke={colour.copper} /><text x="110" y="162" textAnchor="middle" fill={colour.copper} fontSize="13" fontWeight="600">FIRE optimizer</text><text x="110" y="178" textAnchor="middle" fill={colour.copper} fontSize="11">update positions + cell</text>
            <text x="110" y="211" textAnchor="middle" fill={colour.muted} fontSize="11">re-evaluate the updated geometry</text>
          </Diagram>,
        },
      ],
    },
    validate: {
      title: 'First-principles checks for the known-control branch',
      caption: 'Simplified Quantum ESPRESSO validation diagram. Three accepted geometries belong to generated MgO, source-reference MgO and source-reference CaO. Finite cutoff/k-point checks and known-phase recovery do not establish a complete competing-phase hull or a new stable material.',
      cards: [
        {
          label: '01 · Planned branch', title: 'Use the known-MgO control',
          description: <>The predetermined MgO control and compatible oxide reference structures are separate from the empty fresh-formula shortlist.</>,
          graphic: <Diagram title="Known-control and source-reference branches" description="Generated MgO and compatible source references occupy distinct branches before first-principles validation.">
            <rect x="14" y="14" width="192" height="43" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><text x="110" y="32" textAnchor="middle" fill={colour.blue} fontSize="12">generated MgO</text><text x="110" y="48" textAnchor="middle" fill={colour.muted} fontSize="11">known control</text>
            <path d="M14 70h192" stroke={colour.line} strokeDasharray="4 4" /><rect x="14" y="83" width="192" height="43" rx="3" fill={colour.white} stroke={colour.line} /><text x="110" y="101" textAnchor="middle" fill={colour.blue} fontSize="12">source MgO · source CaO</text><text x="110" y="117" textAnchor="middle" fill={colour.muted} fontSize="11">compatible references</text>
          </Diagram>,
        },
        {
          label: '02 · First-principles engine', title: 'Relax with QE / PBE',
          description: <>Plane-wave DFT uses pinned pseudopotentials and numerical settings. Accepted checks require more than a normal process exit.</>,
          graphic: <Diagram title="Conceptual plane-wave DFT calculation" description="Illustrative wave curves enter a Quantum ESPRESSO PBE calculation. The waves are a schematic, not a computed orbital or density.">
            <path d="M17 30c12-22 24 22 36 0s24 22 36 0 24 22 36 0 24 22 36 0 24 22 42 0 M17 46c12-22 24 22 36 0s24 22 36 0 24 22 36 0 24 22 36 0 24 22 42 0" fill="none" stroke={colour.copper} strokeWidth="1.5" />
            <Arrow x1={110} y1={62} x2={110} y2={76} /><rect x="35" y="83" width="150" height="44" rx="4" fill={colour.paleBlue} stroke={colour.blue} /><text x="110" y="101" textAnchor="middle" fill={colour.blue} fontSize="13" fontWeight="600">Quantum ESPRESSO</text><text x="110" y="117" textAnchor="middle" fill={colour.blue} fontSize="11">PBE · plane-wave DFT</text>
          </Diagram>,
        },
        {
          label: '03 · Acceptance checks', title: 'Audit the accepted geometry',
          description: <><span className="workflow-illustration-metric">{counts.acceptedRelaxedQeGeometries} geometries accepted</span> with terminal SCF, force/stress stationarity and finite sensitivity checks.</>,
          graphic: <Diagram title="Three acceptance requirements" description="A checklist shows terminal SCF, force and stress stationarity, and finite cutoff and k-point sensitivity. The broader competing-phase reference inventory remains incomplete.">
            {[{ y: 29, label: 'Terminal SCF' }, { y: 67, label: 'Force + stress' }, { y: 105, label: 'Cutoff + k-point' }].map(({ y, label }) => <g key={label}><Check x={32} y={y} /><text x="54" y={y + 4} fill={colour.blue} fontSize="13">{label}</text><path d={`M21 ${y + 18}h180`} stroke={colour.line} /></g>)}
          </Diagram>,
        },
      ],
    },
    compare: {
      title: 'Compare the evidence within each research track',
      caption: 'Historical bars use saved descriptive means across five overlapping chemical-system splits, each with 50 queries per policy. Near-stable means a historical signed hull target ≤0.05 eV/atom. Historical retrieval, model relaxation and fresh DFT remain distinct outcomes.',
      cards: [
        {
          label: '01 · Historical retrieval', title: 'Quality found more near-stable labels',
          description: <>Mean hits / 50: Quality <span className="workflow-illustration-metric">{n(quality.nearStableHits.mean)}</span>; Full <span className="workflow-illustration-metric">{n(full.nearStableHits.mean)}</span>. Full had fewer hits in all five paired splits.</>,
          graphic: <Diagram title="Mean historical near-stable hits per fifty queries" description={`Quality has ${n(quality.nearStableHits.mean)} mean near-stable hits and Full has ${n(full.nearStableHits.mean)}. Bars share a zero-to-fifty scale.`}>
            <text x="17" y="24" fill={colour.muted} fontSize="11">0</text><text x="201" y="24" textAnchor="end" fill={colour.muted} fontSize="11">50 queries</text>
            {[{ y: 41, label: 'Quality', mean: quality.nearStableHits.mean, fill: policyColour(data.theme, 'quality') }, { y: 92, label: 'Full', mean: full.nearStableHits.mean, fill: policyColour(data.theme, 'full') }].map(({ y, label, mean, fill }) => <g key={label}><text x="17" y={y} fill={colour.ink} fontSize="12">{label}</text><rect x="17" y={y + 8} width="184" height="19" fill={colour.line} /><rect x="17" y={y + 8} width={184 * mean / 50} height="19" fill={fill} /><text x="196" y={y + 22} textAnchor="end" fill={colour.ink} fontSize="12" fontWeight="600">{n(mean)}</text></g>)}
          </Diagram>,
        },
        {
          label: '02 · Breadth', title: 'Full visited more chemical systems',
          description: <>Mean systems queried: Quality <span className="workflow-illustration-metric">{n(quality.chemicalSystemCoverage.mean)}</span>; Full <span className="workflow-illustration-metric">{n(full.chemicalSystemCoverage.mean)}</span>. Greater breadth came with lower immediate retrieval.</>,
          graphic: <Diagram title="Mean chemical-system coverage in the historical replay" description={`Quality queries ${n(quality.chemicalSystemCoverage.mean)} chemical systems on average; Full queries ${n(full.chemicalSystemCoverage.mean)}. Bars share a zero-to-fifty scale.`}>
            <text x="17" y="24" fill={colour.muted} fontSize="11">0</text><text x="201" y="24" textAnchor="end" fill={colour.muted} fontSize="11">50 systems</text>
            {[{ y: 41, label: 'Quality', mean: quality.chemicalSystemCoverage.mean, fill: policyColour(data.theme, 'quality') }, { y: 92, label: 'Full', mean: full.chemicalSystemCoverage.mean, fill: policyColour(data.theme, 'full') }].map(({ y, label, mean, fill }) => <g key={label}><text x="17" y={y} fill={colour.ink} fontSize="12">{label}</text><rect x="17" y={y + 8} width="184" height="19" fill={colour.line} /><rect x="17" y={y + 8} width={184 * mean / 50} height="19" fill={fill} /><text x="196" y={y + 22} textAnchor="end" fill={colour.ink} fontSize="12" fontWeight="600">{n(mean)}</text></g>)}
          </Diagram>,
        },
        {
          label: '03 · Fresh-material conclusion', title: 'Known-phase recovery, bounded claims',
          description: <>MgO was recovered as a known control. <span className="workflow-illustration-metric">0 new stable materials</span> were established; the broader reference hull and perturbation validation remain incomplete.</>,
          graphic: <Diagram title="A known control is distinct from a new discovery" description="A checked known-phase control is separated from an unfilled new-discovery record. Zero newly established stable materials is the recorded conclusion.">
            <rect x="17" y="16" width="186" height="42" rx="3" fill={colour.paleBlue} stroke={colour.blue} /><Check x={37} y={37} /><text x="61" y="41" fill={colour.blue} fontSize="13">known MgO recovered</text>
            <path d="M17 72h186" stroke={colour.line} strokeDasharray="4 4" /><text x="55" y="118" textAnchor="middle" fill={colour.copper} fontSize="40" fontFamily="Georgia, serif">0</text><text x="87" y="100" fill={colour.muted} fontSize="12">new stable materials</text><text x="87" y="119" fill={colour.muted} fontSize="12">established</text>
          </Diagram>,
        },
      ],
    },
  };
  const illustration = content[stage];
  const modelReference = stage === 'generate' ? { label: 'CrystalFormer implementation', url: 'https://github.com/deepmodeling/CrystalFormer' }
    : stage === 'select' ? { label: 'ExtraTrees documentation', url: 'https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html' }
    : stage === 'relax' ? { label: 'CHGNet implementation', url: 'https://github.com/CederGroupHub/chgnet' } : null;
  return <figure className={`workflow-illustration workflow-illustration-${stage}`} data-stage={stage} aria-describedby={captionId}>
    <div className="workflow-illustration-heading"><span className="workflow-illustration-kicker">A visual explanation</span><h3>{illustration.title}</h3></div>
    <div className="workflow-illustration-grid">
      {illustration.cards.map((card) => <div className="workflow-illustration-card" key={card.label}>
        <p className="workflow-illustration-card-label">{card.label}</p>
        {card.graphic}
        <h4>{card.title}</h4><p>{card.description}</p>
      </div>)}
    </div>
    <figcaption className="workflow-illustration-caption" id={captionId}>{illustration.caption}{modelReference && <> <a href={modelReference.url} target="_blank" rel="noreferrer">{modelReference.label} ↗</a></>}</figcaption>
  </figure>;
}
