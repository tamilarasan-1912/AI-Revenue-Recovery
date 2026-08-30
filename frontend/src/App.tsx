import AppRedesign from './AppRedesign';
import Enhancer from './Enhancer';

// Keep a single production UI path. The older Safe pages were useful during
// incident recovery, but routing different pages to different implementations
// made the deployed app appear inconsistent and could hide backend regressions.
export default function App() {
  return <><AppRedesign /><Enhancer /></>;
}
