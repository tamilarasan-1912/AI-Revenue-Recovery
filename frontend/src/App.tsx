import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
export default function App() {
  return (
    <BrowserRouter>
      <div className='flex h-screen bg-razorpay-light'>
        <aside className='w-64 bg-razorpay-dark text-white p-6'>
          <h1 className='text-2xl font-bold text-razorpay-blue'>RecoverAI</h1>
          <nav className='mt-8 space-y-4'>
            <Link to='/' className='block hover:text-razorpay-blue'>Dashboard</Link>
            <Link to='/simulation' className='block hover:text-razorpay-blue'>Simulation Lab</Link>
            <Link to='/audit' className='block hover:text-razorpay-blue'>Audit Log</Link>
          </nav>
        </aside>
        <main className='flex-1 p-8 overflow-auto'>
          <Routes>
            <Route path='/' element={<Dashboard />} />
            <Route path='/simulation' element={<SimulationLab />} />
            <Route path='/audit' element={<AuditLog />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
function Dashboard() { return <h1 className='text-3xl font-bold'>Executive Dashboard</h1>; }
function SimulationLab() { return <h1 className='text-3xl font-bold'>Simulation Lab</h1>; }
function AuditLog() { return <h1 className='text-3xl font-bold'>Audit Log</h1>; }
