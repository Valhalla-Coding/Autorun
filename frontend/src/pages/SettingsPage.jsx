import { useState, useEffect } from 'react'
import { settings } from '../api'

export default function SettingsPage() {
  const [token, setToken] = useState('')
  const [hasToken, setHasToken] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    settings.get().then(d => {
      const t = d.data?.github_token
      setHasToken(!!t)
      // Don't pre-fill the masked value — show empty so user knows to re-enter
    }).catch(() => {})
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setError(''); setSaving(true); setSaved(false)
    try {
      await settings.update({ github_token: token || null })
      setHasToken(!!token)
      setToken('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleClear() {
    setError('')
    try {
      await settings.update({ github_token: null })
      setHasToken(false)
      setToken('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-white mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-8">Configure AutoRun integrations</p>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b border-gray-800">
          <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center justify-center">
            <svg className="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" /></svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">GitHub</p>
            <p className="text-xs text-gray-500">Personal access token for private repos and higher API rate limits</p>
          </div>
          {hasToken && (
            <span className="ml-auto flex items-center gap-1.5 text-xs text-green-400 bg-green-400/10 border border-green-400/20 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Token set
            </span>
          )}
        </div>

        {error && <div className="bg-red-950 border border-red-800 text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
        {saved && <div className="bg-green-950 border border-green-800 text-green-300 text-sm px-4 py-3 rounded-lg">Settings saved</div>}

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              Personal Access Token
              {hasToken && <span className="ml-2 text-gray-600">(leave blank to keep existing)</span>}
            </label>
            <input
              type="password"
              value={token}
              onChange={e => setToken(e.target.value)}
              placeholder={hasToken ? '••••••••••••••••' : 'ghp_xxxxxxxxxxxxxxxxxxxx'}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent placeholder-gray-600 transition"
            />
            <p className="text-xs text-gray-600 mt-1.5">
              Needs <span className="text-gray-500 font-mono">repo</span> scope for private repos.{' '}
              <a href="https://github.com/settings/tokens/new" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300 transition">Generate one on GitHub →</a>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg transition flex items-center gap-2">
              {saving && <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              Save Token
            </button>
            {hasToken && (
              <button type="button" onClick={handleClear}
                className="px-4 py-2 text-sm text-red-400 hover:text-red-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition">
                Clear Token
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
