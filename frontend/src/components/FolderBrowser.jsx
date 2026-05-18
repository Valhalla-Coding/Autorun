import { useState, useEffect } from 'react'
import { system } from '../api'

export default function FolderBrowser({ onSelect, onClose, initialPath = '' }) {
  const [currentPath, setCurrentPath] = useState('')
  const [folders, setFolders] = useState([])
  const [parent, setParent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(initialPath)

  useEffect(() => { navigate(initialPath || null) }, [])

  async function navigate(path) {
    setLoading(true); setError('')
    try {
      const data = await system.browseFolders(path)
      setCurrentPath(data.data.current_path)
      setFolders(data.data.folders)
      setParent(data.data.parent)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md shadow-2xl flex flex-col" style={{ maxHeight: '80vh' }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <h2 className="text-base font-semibold text-white">Select Folder</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-200 transition">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="px-5 py-2.5 border-b border-gray-800 bg-gray-950/50">
          <p className="text-xs text-gray-500 font-mono truncate">{currentPath || '…'}</p>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin px-2 py-2">
          {loading && <div className="flex justify-center py-8"><div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>}
          {error && <div className="mx-3 my-2 text-sm text-red-400 bg-red-950/50 border border-red-900 rounded-lg px-3 py-2">{error}</div>}
          {!loading && !error && (
            <>
              {parent && (
                <button onClick={() => navigate(parent)}
                  className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                  <span className="font-mono text-xs">..</span>
                </button>
              )}
              {folders.length === 0 && <p className="text-sm text-gray-600 text-center py-6">No subdirectories</p>}
              {folders.map(f => (
                <button key={f.path} onClick={() => { setSelected(f.path); if (f.has_children) navigate(f.path) }}
                  className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm transition ${selected === f.path ? 'bg-brand-600/20 text-brand-300' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>
                  <svg className="w-4 h-4 flex-shrink-0 text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" /></svg>
                  <span className="truncate">{f.name}</span>
                  {f.has_children && <svg className="w-3.5 h-3.5 ml-auto text-gray-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>}
                </button>
              ))}
            </>
          )}
        </div>
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-500 truncate flex-1 font-mono">{selected || 'No folder selected'}</p>
          <div className="flex gap-2 flex-shrink-0">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition">Cancel</button>
            <button onClick={() => selected && onSelect(selected)} disabled={!selected}
              className="px-4 py-2 text-sm text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-40 rounded-lg transition">Select</button>
          </div>
        </div>
      </div>
    </div>
  )
}
