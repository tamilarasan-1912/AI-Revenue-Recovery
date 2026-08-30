import AppRedesign from './AppRedesign';
import Enhancer from './Enhancer';
import SimulationSafe from './SimulationSafe';
import RecoverySafe from './RecoverySafe';

export default function App() {
  if (window.location.pathname === '/simulation') return <SimulationSafe />;
  if (window.location.pathname === '/recovery') return <RecoverySafe />;
  return <><AppRedesign /><Enhancer /></>;
}
