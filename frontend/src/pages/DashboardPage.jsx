import { useState, useEffect, useCallback } from 'react'
import { services as api } from '../api'
import ServiceCard from '../components/ServiceCard'
import ServiceModal from '../components/ServiceModal'

export default function DashboardPage() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)

  const refresh = useCallback(async () => {
    try { const d = await api.list(); setList(d.data.services); setError('') }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t) }, [refresh])

  const running = list.filter(s => s.status === 'running').length
  const failed  = list.filter(s => s.status === 'failed').length

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Services</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {list.length === 0 ? 'No services yet' : `${running} of ${list.length} running${failed > 0 ? ` · ${failed} failed` : ''}`}
          </p>
        </div>
        <button onClick={() => setModal({ mode: 'add' })}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
          Add Service
        </button>
      </div>

      {list.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[{ label: 'Total', value: list.length, color: 'text-white' }, { label: 'Running', value: running, color: 'text-green-400' }, { label: 'Failed', value: failed, color: failed > 0 ? 'text-red-400' : 'text-gray-500' }].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {error && <div className="bg-red-950 border border-red-800 text-red-300 text-sm px-4 py-3 rounded-lg mb-4">{error}</div>}

      {loading && <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>}

      {!loading && list.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg>
          </div>
          <p className="text-gray-400 font-medium">No services yet</p>
          <p className="text-sm text-gray-600 mt-1">Add your first service to get started</p>
          <button onClick={() => setModal({ mode: 'add' })} className="mt-4 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition">Add Service</button>
        </div>
      )}

      {!loading && list.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {list.map(svc => (
            <ServiceCard key={svc.name} service={svc}
              onStart={async () => { await api.start(svc.name); await refresh() }}
              onStop={async () => { await api.stop(svc.name); await refresh() }}
              onRestart={async () => { await api.restart(svc.name); await refresh() }}
              onPull={async () => { await api.pull(svc.name); await refresh() }}
              onEdit={() => setModal({ mode: 'edit', service: svc })}
              onDelete={async () => { await api.delete(svc.name); await refresh() }}
            />
          ))}
        </div>
      )}

      {modal && (
        <ServiceModal mode={modal.mode} service={modal.service}
          onSave={async data => { modal.mode === 'add' ? await api.create(data) : await api.update(modal.service.name, data); await refresh() }}
          onClose={() => setModal(null)} />
      )}
    </div>
  )
}
