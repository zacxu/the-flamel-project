import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { ResearchProvider } from './data/ResearchData';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Application root is missing.');
createRoot(root).render(<StrictMode><ResearchProvider><App /></ResearchProvider></StrictMode>);
