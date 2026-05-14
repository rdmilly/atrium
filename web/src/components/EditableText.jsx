import { useState, useEffect, useRef } from 'react'

export function EditableText({ value, onSave, multiline = false, className = '', placeholder = '' }) {
  const [draft, setDraft] = useState(value || '')
  const [saving, setSaving] = useState(false)
  const ref = useRef(null)

  useEffect(() => { setDraft(value || '') }, [value])

  async function commit() {
    if (draft === value) return
    setSaving(true)
    try { await onSave(draft) } catch (e) { console.error(e); setDraft(value || '') }
    setSaving(false)
  }

  if (multiline) {
    return (
      <textarea
        ref={ref}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        className={`editable resize-y ${className} ${saving ? 'opacity-60' : ''}`}
      />
    )
  }
  return (
    <input
      ref={ref}
      type="text"
      value={draft}
      placeholder={placeholder}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => { if (e.key === 'Enter') ref.current.blur() }}
      className={`editable ${className} ${saving ? 'opacity-60' : ''}`}
    />
  )
}

