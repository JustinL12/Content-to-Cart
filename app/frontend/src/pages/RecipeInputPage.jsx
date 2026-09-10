import { useState } from 'react'
import { useGrocery } from '../context/GroceryContext'
import NavButton from '../components/NavButton'

const API_BASE = ''

export default function RecipeInputPage() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { addRecipe } = useGrocery()

  async function handleAdd() {
    setError(null)
    if (!url.trim()) {
      setError('Please paste a recipe or video URL.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || res.statusText)
      }
      const data = await res.json()
      addRecipe(url.trim(), data)
      setUrl('')
    } catch (e) {
      setError(e.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page recipe-input-page">
      <NavButton />

      <div className="recipe-input-card card">
        <h1 className="page-title">Recipe Input</h1>
        <p className="page-subtitle">
          Paste a cooking video or recipe URL to add ingredients to your grocery list.
        </p>

        <div className="form-group">
          <input
            type="url"
            className="input-box url-input"
            placeholder="https://..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
            aria-label="Recipe or video URL"
          />
        </div>

        <button
          type="button"
          className="btn-primary extract-btn"
          onClick={handleAdd}
          disabled={loading}
        >
          {loading ? 'Adding to Grocery List...' : 'Add to Grocery List'}
        </button>

        {error && <div className="error" role="alert">{error}</div>}
      </div>
    </div>
  )
}
