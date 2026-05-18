import { useState } from 'react'

const STATUS = {
  running: { dot: 'bg-green-400 animate-pulse', text: 'text-green-400', label: 'Running' },
  stopped: { dot: 'bg-gray-500',                text: 'text-gray-400',  label: 'Stopped' },
  failed:  { dot: 'bg-red-500',                 text: 'text-red-400',   label: 'Failed'  },
  unknown: { dot: 'bg-yellow-500',              text: 'text-yellow-400',label: 'Unknown' },
}

export default function ServiceCard({ service, onStart, onStop, onRestart, onEdit, onDelete, onPull }) {
  const [busy, setBusy] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const cfg = service.config ?? service
  const s = STATUS[service.status] ?? STATUS.unknown
  const running = service.status === 'running'

  const run = async (key, fn) => { setBusy(key); try { await fn() } finally { setBusy(null) } }

  const Btn = ({ id, title, onClick, children, cls = '' }) => (
    <button title={title} onClick={onClick} disabled={!!busy}
      className={`p-1.5 rounded-lg text-gray-500 hover:text-gray-200 hover:bg-gray-700 disabled:opacity-40 transition ${cls}`}>
      {busy === id ? <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin block" /> : children}
    </button>
  )

  return (
    <div className={`bg-gray-900 border rounded-xl p-4 flex flex-col gap-3 transition ${service.status === 'failed' ? 'border-red-900/60' : 'border-gray-800'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.dot}`} />
            <h3 className="text-sm font-semibold text-white truncate">{cfg.name}</h3>
          </div>
          {cfg.description && <p className="text-xs text-gray-500 mt-0.5 ml-4 truncate">{cfg.description}</p>}
        </div>
        <span className={`text-xs font-medium flex-shrink-0 ${s.text}`}>{s.label}</span>
      </div>

      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600 ml-4">
        {cfg.port && <span>:{cfg.port}</span>}
        {cfg.folder && <span className="font-mono truncate" title={cfg.folder}>{cfg.folder.split('/').pop()}</span>}
        {cfg.github_url && <span className="flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" /></svg>
          git
        </span>}
      </div>

      <div className="flex items-center justify-between mt-auto pt-1 border-t border-gray-800">
        <div className="flex items-center gap-0.5">
          {!running
            ? <Btn id="start" title="Start" onClick={() => run('start', onStart)}><svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.84A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.27l9.344-5.891a1.5 1.5 0 000-2.538L6.3 2.84z" /></svg></Btn>
            : <Btn id="stop" title="Stop" onClick={() => run('stop', onStop)}><svg className="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5z" /></svg></Btn>
          }
          <Btn id="restart" title="Restart" onClick={() => run('restart', onRestart)}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
          </Btn>
          {cfg.github_url && <Btn id="pull" title="Pull & restart" onClick={() => run('pull', onPull)}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
          </Btn>}
          {cfg.web_interface && cfg.url && (
            <a href={cfg.url} target="_blank" rel="noopener noreferrer" title="Open service"
              className="p-1.5 rounded-lg text-gray-500 hover:text-brand-400 hover:bg-gray-700 transition">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>
            </a>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <Btn id="edit" title="Edit" onClick={onEdit}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" /></svg>
          </Btn>
          {confirmDelete
            ? <div className="flex items-center gap-1 ml-1">
                <span className="text-xs text-red-400">Sure?</span>
                <button onClick={onDelete} className="text-xs px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded-md transition">Yes</button>
                <button onClick={() => setConfirmDelete(false)} className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-md transition">No</button>
              </div>
            : <Btn id="delete" title="Delete" onClick={() => setConfirmDelete(true)}>
                <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
              </Btn>
          }
        </div>
      </div>
    </div>
  )
}
