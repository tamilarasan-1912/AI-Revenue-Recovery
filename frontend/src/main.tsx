import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PaymentsSafe from './PaymentsSafe'
import './index.css'

class AppErrorBoundary extends React.Component<React.PropsWithChildren, { hasError: boolean; message: string }> {
  state = { hasError: false, message: '' }

  static getDerivedStateFromError(error: unknown) {
    return { hasError: true, message: error instanceof Error ? error.message : 'Unexpected application error' }
  }

  componentDidCatch(error: unknown) {
    console.error('RecoverAI application error:', error)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    if (window.location.pathname === '/payments') return <PaymentsSafe />

    return (
      <div className="min-h-screen bg-[#f7f9fb] p-8 text-[#17191d]">
        <div className="mx-auto mt-20 max-w-xl rounded-xl border border-red-200 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-extrabold">RecoverAI could not render this page</h1>
          <p className="mt-3 text-sm text-[#656a73]">The application recovered from the runtime crash instead of showing a blank screen.</p>
          <pre className="mt-4 overflow-auto rounded bg-red-50 p-3 text-xs text-red-700">{this.state.message}</pre>
          <button onClick={() => window.location.reload()} className="mt-5 rounded bg-black px-4 py-2.5 text-sm font-bold text-white">Reload application</button>
        </div>
      </div>
    )
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><AppErrorBoundary><App /></AppErrorBoundary></React.StrictMode>
)
