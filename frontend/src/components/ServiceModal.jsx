import { useState } from 'react'
import FolderBrowser from './FolderBrowser'

const RESTART_OPTIONS = ['always', 'on-failure', 'no']
const DEFAULT = { name: '', description: '', folder: '', entrypoint: 'run.py', web_interface: false, port: '', url: '', auto_restart: 'always', enabled: true, github_url: '', auto_update: false }

export default function ServiceModal({ mode = 'add', service = null, onSave, onClose }) {
  const [form, setForm] = useState(() => {
    if (mode === 'edit' && service) {
      const c = service.config ?? service
      return { name: c.name ?? '', description: c.description ?? '', folder: c.folder ?? '', entrypoint: c.entrypoint ?? 'run.py', web_interface: c.web_interface ?? false, port: c.port ?? '', url: c.url ?? '', auto_restart: c.auto_restart ?? 'always', enabled: c.enabled ?? true, github_url: c.github_url ?? '', auto_update: c.auto_update ?? false }
    }
    return { ...DEFAULT }
  })
  const [showBrowser, setShowBrowser] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setSaving(true)
    try {
      const payload = { ...form, port: form.web_interface && form.port !== '' ? parseInt(form.port) : undefined, url: form.web_interface ? (form.url || undefined) : undefined, github_url: form.github_url || null }
      if (!form.web_interface) { delete payload.port; delete payload.url }
      await onSave(payload); onClose()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent placeholder-gray-600 transition"

  return (
    <>
      <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col" style={{ maxHeight: '90vh' }}>
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <h2 className="text-base font-semibold text-white">{mode === 'add' ? 'Add Service' : `Edit — ${service?.name}`}</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-200 transition">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto scrollbar-thin px-6 py-4 space-y-4">
            {error && <div className="bg-red-950 border border-red-800 text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Service name <span className="text-red-400">*</span></label>
              <input value={form.name} onChange={e => set('name', e.target.value)} disabled={mode === 'edit'} required pattern="^[a-z0-9-]+$" placeholder="my-flask-app" className={inp + (mode === 'edit' ? ' opacity-50 cursor-not-allowed' : '')} />
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
                <button type="button" onClick={() => setShowBrowser(true)} className="px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-400 hover:text-white transition" title="Browse">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" /></svg>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Entrypoint</label>
              <input value={form.entrypoint} onChange={e => set('entrypoint', e.target.value)} placeholder="run.py" className={inp} />
            </div>

            <div className="flex items-center justify-between py-1">
              <div><p className="text-sm font-medium text-gray-200">Web interface</p><p className="text-xs text-gray-500">Exposes a port and proxy URL</p></div>
              <button type="button" onClick={() => set('web_interface', !form.web_interface)} className={`relative w-10 h-6 rounded-full transition-colors ${form.web_interface ? 'bg-brand-600' : 'bg-gray-700'}`}>
                <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.web_interface ? 'translate-x-4' : ''}`} />
              </button>
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

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">GitHub URL <span className="text-gray-600">(optional)</span></label>
              <input value={form.github_url} onChange={e => set('github_url', e.target.value)} placeholder="https://github.com/user/repo" className={inp} />
            </div>

            {form.github_url && (
              <div className="flex items-center justify-between py-1">
                <div><p className="text-sm font-medium text-gray-200">Auto-update</p><p className="text-xs text-gray-500">Pull and restart on new commits</p></div>
                <button type="button" onClick={() => set('auto_update', !form.auto_update)} className={`relative w-10 h-6 rounded-full transition-colors ${form.auto_update ? 'bg-brand-600' : 'bg-gray-700'}`}>
                  <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.auto_update ? 'translate-x-4' : ''}`} />
                </button>
              </div>
            )}

            <div className="flex items-center justify-between py-1">
              <div><p className="text-sm font-medium text-gray-200">Enabled</p><p className="text-xs text-gray-500">Register with systemd on save</p></div>
              <button type="button" onClick={() => set('enabled', !form.enabled)} className={`relative w-10 h-6 rounded-full transition-colors ${form.enabled ? 'bg-brand-600' : 'bg-gray-700'}`}>
                <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.enabled ? 'translate-x-4' : ''}`} />
              </button>
            </div>
          </form>

          <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-800">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition">Cancel</button>
            <button onClick={handleSubmit} disabled={saving} className="px-4 py-2 text-sm text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg transition flex items-center gap-2">
              {saving && <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              {mode === 'add' ? 'Add Service' : 'Save Changes'}
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
