import { createContext, useContext } from 'react';
import type { TourSnapshot } from './model';

export const TourContext = createContext<TourSnapshot>({ status: 'idle', step: 0, elapsed: 0, scene: null });
export function useTourScene() { return useContext(TourContext); }
