import { useState, useEffect, useRef } from 'react'
import FolderBrowser from './FolderBrowser'
import { github, system } from '../api'

// Fetch system username once and cache it
let _systemUser = null
async function getSystemUser() {
  if (_systemUser) return _systemUser
  try {
    const d = await system.health()
    _systemUser = d.data?.system_user || 'user'
  } catch { _systemUser = 'user' }
  return _systemUser
}

const RESTART_OPTIONS = ['always', 'on-failure', 'no']

const LOCAL_DEFAULT  = { name: '', description: '', folder: '', entrypoint: '', web_interface: false, port: '', url: '', auto_restart: 'always', enabled: true, github_url: null, auto_update: false }
const GITHUB_DEFAULT = { name: '', description: '', github_url: '', folder: '', entrypoint: '', web_interface: false, port: '', url: '', auto_restart: 'always', enabled: true, auto_update: true }

const Toggle = ({ value, onChange }) => (
  <button type="button" onClick={() => onChange(!value)}
    className={`relative w-10 h-6 rounded-full transition-colors flex-shrink-0 ${value ? 'bg-brand-600' : 'bg-gray-700'}`}>
    <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${value ? 'translate-x-4' : ''}`} />
  </button>
)

function EntrypointPicker({ folder, githubUrl, branch, value, onChange, inp }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    setFiles([])
    if (githubUrl && githubUrl.includes('github.com')) {
      // GitHub mode — fetch file tree from API
      setLoading(true)
      github.repoFiles(githubUrl, branch || 'main')
        .then(d => setFiles((d.data?.files ?? []).map(f => ({ name: f, path: f }))))
        .catch(() => setFiles([]))
        .finally(() => setLoading(false))
    } else if (folder) {
      // Local mode — browse filesystem
      setLoading(true)
      system.browseFiles(folder)
        .then(d => setFiles(d.data?.files ?? []))
        .catch(() => setFiles([]))
        .finally(() => setLoading(false))
    }
  }, [folder, githubUrl, branch])

  useEffect(() => {
    function handleClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const ready = !loading && files.length > 0
  const placeholder = loading ? 'Loading files…'
    : (githubUrl || folder) ? 'No .py files found — type manually'
    : githubUrl ? 'Enter GitHub URL first' : 'Set folder first'

  if (!ready) {
    return <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} className={inp} />
  }

  return (
    <div className="relative" ref={ref}>
      <button type="button" onClick={() => setOpen(o => !o)}
        className={`${inp} flex items-center justify-between text-left`}>
        <span className={value ? 'text-white' : 'text-gray-600'}>{value || 'Select entrypoint…'}</span>
        <svg className="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 top-full mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-y-auto max-h-48">
          {files.map(f => (
            <button key={f.path} type="button"
              onClick={() => { onChange(f.name); setOpen(false) }}
              className={`flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-gray-700 transition ${value === f.name ? 'text-brand-300 bg-brand-600/10' : 'text-gray-200'}`}>
              <svg className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              </svg>
              {f.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ServiceModal({ mode = 'add', service = null, onSave, onClose }) {
  const existingTab = mode === 'edit' && (service?.config?.github_url || service?.github_url) ? 'github' : 'local'
  const [tab, setTab] = useState(existingTab)
  const [showBrowser, setShowBrowser] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [githubLookup, setGithubLookup] = useState(null) // 'loading' | 'ok' | 'error'
  const [repoBranch, setRepoBranch] = useState('main')
  const githubDebounce = useRef(null)

  const [form, setForm] = useState(() => {
    if (mode === 'edit' && service) {
      const c = service.config ?? service
      return {
        name: c.name ?? '', description: c.description ?? '', folder: c.folder ?? '',
        entrypoint: c.entrypoint ?? '', web_interface: c.web_interface ?? false,
        port: c.port ?? '', url: c.url ?? '', auto_restart: c.auto_restart ?? 'always',
        enabled: c.enabled ?? true, github_url: c.github_url ?? '', auto_update: c.auto_update ?? false
      }
    }
    return { ...LOCAL_DEFAULT }
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  function switchTab(t) {
    setTab(t)
    setError('')
    setGithubLookup(null)
    if (mode === 'add') setForm(t === 'local' ? { ...LOCAL_DEFAULT } : { ...GITHUB_DEFAULT })
  }

  // Auto-populate name + description from GitHub URL
  function onGithubUrlChange(url) {
    set('github_url', url)
    setGithubLookup(null)
    clearTimeout(githubDebounce.current)
    if (!url || !url.includes('github.com')) return
    setGithubLookup('loading')
    githubDebounce.current = setTimeout(async () => {
      try {
        const [repoData, sysUser] = await Promise.all([github.repoInfo(url), getSystemUser()])
        const repo = repoData.data
        setRepoBranch(repo.default_branch || 'main')
        setForm(f => ({
          ...f,
          github_url: url,
          name: f.name || repo.name.toLowerCase().replace(/[^a-z0-9]/g, '-'),
          description: f.description || repo.description || '',
          folder: f.folder || `/home/${sysUser}/git/${repo.name}`,
        }))
        setGithubLookup('ok')
      } catch {
        setGithubLookup('error')
      }
    }, 600)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const payload = { ...form }
      if (tab === 'local') payload.github_url = null
      if (payload.web_interface) {
        if (payload.port !== '') payload.port = parseInt(payload.port)
        else delete payload.port
      } else {
        delete payload.port
        delete payload.url
      }
      await onSave(payload)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent placeholder-gray-600 transition"

  const WebInterfaceSection = () => (
    <>
      <div className="flex items-center justify-between py-1">
        <div>
          <p className="text-sm font-medium text-gray-200">Web interface</p>
          <p className="text-xs text-gray-500">Exposes a port and proxy URL</p>
        </div>
        <Toggle value={form.web_interface} onChange={v => set('web_interface', v)} />
      </div>
      {form.web_interface && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Port <span className="text-gray-600">(auto if blank)</span></label>
            <input type="number" value={form.port} onChange={e => set('port', e.target.value)} min={5001} max={5999} placeholder="auto" className={inp} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Proxy URL</label>
            <input value={form.url} onChange={e => set('url', e.target.value)} placeholder={`/${form.name || 'app'}`} className={inp} />
          </div>
        </div>
      )}
    </>
  )

  const RestartSection = () => (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1.5">Auto-restart</label>
      <div className="flex gap-2">
        {RESTART_OPTIONS.map(opt => (
          <button key={opt} type="button" onClick={() => set('auto_restart', opt)}
            className={`flex-1 py-2 text-xs font-medium rounded-lg border transition ${form.auto_restart === opt ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200'}`}>
            {opt}
          </button>
        ))}
      </div>
    </div>
  )

  const EnabledSection = () => (
    <div className="flex items-center justify-between py-1">
      <div>
        <p className="text-sm font-medium text-gray-200">Enabled</p>
        <p className="text-xs text-gray-500">Register with systemd on save</p>
      </div>
      <Toggle value={form.enabled} onChange={v => set('enabled', v)} />
    </div>
  )

  return (
    <>
      <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col" style={{ maxHeight: '90vh' }}>

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <h2 className="text-base font-semibold text-white">
              {mode === 'add' ? 'Add Service' : `Edit — ${service?.config?.name ?? service?.name}`}
            </h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-200 transition">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          {/* Tabs */}
          {mode === 'add' && (
            <div className="flex px-6 pt-4 gap-2">
              <button type="button" onClick={() => switchTab('local')}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg border transition ${tab === 'local' ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'}`}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7" /></svg>
                Local
              </button>
              <button type="button" onClick={() => switchTab('github')}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg border transition ${tab === 'github' ? 'bg-brand-600/20 border-brand-500 text-brand-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'}`}>
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" /></svg>
                GitHub
              </button>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto scrollbar-thin px-6 py-4 space-y-4">
            {error && <div className="bg-red-950 border border-red-800 text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}

            {/* ── GITHUB TAB ── */}
            {tab === 'github' && (
              <>
                {/* GitHub URL — first, with live lookup indicator */}
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">GitHub URL <span className="text-red-400">*</span></label>
                  <div className="relative">
                    <input value={form.github_url} onChange={e => onGithubUrlChange(e.target.value)}
                      required placeholder="https://github.com/user/repo" className={inp + ' pr-8'} />
                    <span className="absolute right-2.5 top-1/2 -translate-y-1/2">
                      {githubLookup === 'loading' && <span className="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin block" />}
                      {githubLookup === 'ok'      && <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
                      {githubLookup === 'error'   && <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" /></svg>}
                    </span>
                  </div>
                  {githubLookup === 'error' && <p className="text-xs text-yellow-500 mt-1">Couldn't fetch repo info — check the URL or add a GitHub token in Settings</p>}
                  <p className="text-xs text-gray-600 mt-1">Repo will be cloned automatically if the folder doesn't exist</p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Service name <span className="text-red-400">*</span></label>
                  <input value={form.name} onChange={e => set('name', e.target.value)} disabled={mode === 'edit'} required pattern="^[a-z0-9-]+$" placeholder="my-flask-app"
                    className={inp + (mode === 'edit' ? ' opacity-50 cursor-not-allowed' : '')} />
                  <p className="text-xs text-gray-600 mt-1">Lowercase letters, numbers, hyphens</p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
                  <input value={form.description} onChange={e => set('description', e.target.value)} placeholder="What does this service do?" className={inp} />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Clone to folder <span className="text-red-400">*</span></label>
                  <div className="flex gap-2">
                    <input value={form.folder} onChange={e => set('folder', e.target.value)} required placeholder="/home/user/my-app" className={inp + ' flex-1'} />
                    <button type="button" onClick={() => setShowBrowser(true)}
                      className="px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-400 hover:text-white transition" title="Browse">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" /></svg>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Entrypoint</label>
                  <EntrypointPicker folder={form.folder} githubUrl={form.github_url} branch={repoBranch} value={form.entrypoint} onChange={v => set('entrypoint', v)} inp={inp} />
                </div>

                <div className="flex items-center justify-between py-1">
                  <div>
                    <p className="text-sm font-medium text-gray-200">Auto-update</p>
                    <p className="text-xs text-gray-500">Pull and restart when new commits are pushed</p>
                  </div>
                  <Toggle value={form.auto_update} onChange={v => set('auto_update', v)} />
                </div>

                <WebInterfaceSection />
                <RestartSection />
                <EnabledSection />
              </>
            )}

            {/* ── LOCAL TAB ── */}
            {tab === 'local' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Service name <span className="text-red-400">*</span></label>
                  <input value={form.name} onChange={e => set('name', e.target.value)} disabled={mode === 'edit'} required pattern="^[a-z0-9-]+$" placeholder="my-flask-app"
                    className={inp + (mode === 'edit' ? ' opacity-50 cursor-not-allowed' : '')} />
                  <p className="text-xs text-gray-600 mt-1">Lowercase letters, numbers, hyphens</p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
                  <input value={form.description} onChange={e => set('description', e.target.value)} placeholder="What does this service do?" className={inp} />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Folder <span className="text-red-400">*</span></label>
                  <div className="flex gap-2">
                    <input value={form.folder} onChange={e => set('folder', e.target.value)} required placeholder="/home/user/my-app" className={inp + ' flex-1'} />
                    <button type="button" onClick={() => setShowBrowser(true)}
                      className="px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-400 hover:text-white transition" title="Browse">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" /></svg>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Entrypoint</label>
                  <EntrypointPicker folder={form.folder} value={form.entrypoint} onChange={v => set('entrypoint', v)} inp={inp} />
                </div>

                <WebInterfaceSection />
                <RestartSection />
                <EnabledSection />
              </>
            )}

          </form>

          {/* Footer */}
          <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-800">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition">Cancel</button>
            <button onClick={handleSubmit} disabled={saving} className="px-4 py-2 text-sm text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg transition flex items-center gap-2">
              {saving && <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              {mode === 'add' ? (tab === 'github' ? 'Clone & Add' : 'Add Service') : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      {showBrowser && (
        <div className="z-50">
          <FolderBrowser initialPath={form.folder} onSelect={p => { set('folder', p); setShowBrowser(false) }} onClose={() => setShowBrowser(false)} />
        </div>
      )}
    </>
  )
}
