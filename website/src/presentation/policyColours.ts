import type { EvaluationPolicy, ThemeDataset } from '../data/contracts.ts';

/** Presentation-only contrast corrections. The frozen theme and scientific exports
 * retain their original palette. Names, line dashes and table values also identify
 * each policy, so colour never carries the comparison by itself. */
const ACCESSIBLE_OVERRIDES: Partial<Readonly<Record<EvaluationPolicy, string>>> = {
  full: '#9B4275', uncertainty: '#8C6200', quality_diversity: '#007C5B',
};
export function policyColour(theme: ThemeDataset, policy: EvaluationPolicy): string {
  return ACCESSIBLE_OVERRIDES[policy] ?? theme.policyColours[policy];
}
