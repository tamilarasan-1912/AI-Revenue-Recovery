import AppRedesign from './AppRedesign';
import Enhancer from './Enhancer';
import SimulationSafe from './SimulationSafe';

export default function App() {
  if (window.location.pathname === '/simulation') return <SimulationSafe />;
  return <><AppRedesign /><Enhancer /></>;
}
