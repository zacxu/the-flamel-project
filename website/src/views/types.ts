import type { CoreData } from '../data/ResearchData';
import type { RouteState } from '../state/route';

export interface ViewProps {
  readonly data: CoreData;
  readonly state: RouteState;
  readonly update: (patch: Partial<RouteState>) => void;
  readonly onSources: (ids?: readonly string[]) => void;
  readonly onGlossary: () => void;
  readonly playing: boolean;
  readonly setPlaying: (playing: boolean) => void;
  readonly registerCancellation: (callback: () => void) => () => void;
  readonly reset: () => void;
}
