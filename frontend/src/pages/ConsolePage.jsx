import { useState, useEffect, useRef } from 'react'
import { getToken, system as systemApi } from '../api'

const LEVEL_STYLES = { ERROR: 'text-red-400', WARNING: 'text-yellow-400', WARN: 'text-yellow-400', INFO: 'text-blue-300', DEBUG: 'text-gray-500' }

function detectLevel(text) {
  const u = text.toUpperCase()
  if (u.includes('ERROR')) return 'ERROR'
  if (u.includes('WARN')) return 'WARNING'
  if (u.includes('DEBUG')) return 'DEBUG'
  return 'INFO'
}

export default function ConsolePage() {
  const [lines, setLines] = useState([])
  const [serviceFilter, setServiceFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [paused, setPaused] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [services, setServices] = useState([])
  const [hasUpdate, setHasUpdate] = useState(false)
  const [pulling, setPulling] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    fetch('/api/services', { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(r => r.json()).then(d => setServices(d.data?.services?.map(s => s.name) ?? [])).catch(() => {})
  }, [])

  // Check if AutoRun itself has an update available
  useEffect(() => {
    systemApi.checkSelfUpdate().then(d => setHasUpdate(d.data?.has_update ?? false)).catch(() => {})
    const id = setInterval(() => {
      systemApi.checkSelfUpdate().then(d => setHasUpdate(d.data?.has_update ?? false)).catch(() => {})
    }, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  async function handleSelfPull() {
    setPulling(true)
    try {
      const res = await systemApi.pullSelf()
      setHasUpdate(false)
      setLines(prev => [...prev, { text: `✓ ${res.message}`, level: 'INFO', ts: new Date().toISOString() }])
    } catch (e) {
      setLines(prev => [...prev, { text: `✗ Pull failed: ${e.message}`, level: 'ERROR', ts: new Date().toISOString() }])
      setPulling(false)
    }
  }

  useEffect(() => {
    if (paused) return
    const svc = serviceFilter === 'all' ? '' : serviceFilter
    const url = `/api/logs/stream${svc ? `?service=${svc}&` : '?'}token=${getToken()}`
    const source = new EventSource(url)
    source.onmessage = e => {
      try {
        const entry = JSON.parse(e.data)
        setLines(prev => { const n = [...prev, entry]; return n.length > 2000 ? n.slice(-2000) : n })
      } catch {
        setLines(prev => { const n = [...prev, { text: e.data, level: detectLevel(e.data), ts: new Date().toISOString() }]; return n.length > 2000 ? n.slice(-2000) : n })
      }
    }
    source.onerror = () => source.close()
    return () => source.close()
  }, [paused, serviceFilter])

  useEffect(() => { if (autoScroll && bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth' }) }, [lines, autoScroll])

  const filtered = lines.filter(l => !search || (l.text ?? l.MESSAGE ?? JSON.stringify(l)).toLowerCase().includes(search.toLowerCase()))

  function download() {
    const blob = new Blob([filtered.map(l => l.text ?? l.MESSAGE ?? JSON.stringify(l)).join('\n')], { type: 'text/plain' })
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `autorun-logs-${new Date().toISOString().slice(0,10)}.txt` })
    a.click(); URL.revokeObjectURL(a.href)
  }

  const CtrlBtn = ({ active, title, onClick, children }) => (
    <button onClick={onClick} title={title} className={`p-1.5 rounded-lg border transition ${active ? 'border-brand-600 text-brand-400 bg-brand-950/30' : 'border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800'}`}>{children}</button>
  )

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-xl font-bold text-white">Console</h1>
        <div className="flex items-center gap-2">
          <select value={serviceFilter} onChange={e => setServiceFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500">
            <option value="all">All services</option>
            {services.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={handleSelfPull} disabled={pulling}
            title="Pull latest AutoRun from GitHub and restart"
            className={`relative flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition disabled:opacity-50 ${hasUpdate ? 'border-green-500 text-green-400 bg-green-500/10 hover:bg-green-500/20' : 'border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800'}`}>
            {hasUpdate && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />}
            {pulling
              ? <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
              : <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>}
            {hasUpdate ? 'Update available' : 'Update AutoRun'}
          </button>
          <div className="relative">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Filter…" className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg pl-7 pr-3 py-1.5 w-40 focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <CtrlBtn active={paused} title={paused ? 'Resume' : 'Pause'} onClick={() => setPaused(p => !p)}>
            {paused ? <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6.3 2.84A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.27l9.344-5.891a1.5 1.5 0 000-2.538L6.3 2.84z" /></svg>
                    : <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z" /></svg>}
          </CtrlBtn>
          <CtrlBtn active={autoScroll} title="Auto-scroll" onClick={() => setAutoScroll(a => !a)}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" /></svg>
          </CtrlBtn>
          <CtrlBtn title="Clear" onClick={() => setLines([])}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
          </CtrlBtn>
          <CtrlBtn title="Download" onClick={download}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
          </CtrlBtn>
        </div>
      </div>

      <div className="flex-1 bg-gray-950 border border-gray-800 rounded-xl overflow-y-auto scrollbar-thin font-mono text-xs p-3 min-h-0">
        {filtered.length === 0 && <div className="flex items-center justify-center h-full"><p className="text-gray-700">{paused ? 'Stream paused' : 'Waiting for logs…'}</p></div>}
        {filtered.map((line, i) => {
          const text = line.text ?? line.MESSAGE ?? JSON.stringify(line)
          const level = line.level ?? detectLevel(text)
          const ts = line.ts ?? line.__REALTIME_TIMESTAMP ?? ''
          return (
            <div key={i} className="flex gap-2 hover:bg-gray-900/50 px-1 py-0.5 rounded">
              {ts && <span className="text-gray-700 flex-shrink-0 select-none">{new Date(typeof ts === 'string' ? ts : parseInt(ts) / 1000).toLocaleTimeString()}</span>}
              <span className={`flex-shrink-0 w-14 ${LEVEL_STYLES[level] ?? 'text-gray-400'}`}>{level}</span>
              <span className="text-gray-300 break-all">{text}</span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
      <p className="text-xs text-gray-700 mt-2 flex-shrink-0">{filtered.length} lines{search ? ` matching "${search}"` : ''}{paused && ' · paused'}</p>
    </div>
  )
}
