import { useState } from 'react'
import { EditableText } from '../components/EditableText'

// Per-template kind definitions — mirrors public_pages.py COMPONENT_GROUPS
const KINDS_BY_TEMPLATE = {
  software: [
    { key: 'service', label: 'Services' },
    { key: 'module', label: 'Modules' },
    { key: 'datastore', label: 'Datastores' },
    { key: 'integration', label: 'Integrations' },
    { key: 'library', label: 'Libraries' },
    { key: 'frontend', label: 'Frontend' },
    { key: 'cli', label: 'CLI tools' },
  ],
  growth: [
    { key: 'persona', label: 'Personas' },
    { key: 'channel', label: 'Channels' },
    { key: 'funnel_stage', label: 'Funnel stages' },
    { key: 'content_type', label: 'Content types' },
    { key: 'metric', label: 'Metrics' },
  ],
  services: [
    { key: 'customer_segment', label: 'Customer segments' },
    { key: 'service_offering', label: 'Service offerings' },
    { key: 'tool', label: 'Tools' },
    { key: 'equipment', label: 'Equipment' },
    { key: 'territory', label: 'Territories' },
  ],
  investigation: [
    { key: 'source', label: 'Sources' },
    { key: 'location', label: 'Locations' },
    { key: 'witness', label: 'Witnesses' },
    { key: 'exhibit', label: 'Exhibits' },
    { key: 'theory', label: 'Theories' },
  ],
  portfolio: [
    { key: 'page', label: 'Pages' },
    { key: 'asset', label: 'Assets' },
    { key: 'story', label: 'Stories' },
    { key: 'skill', label: 'Skills' },
    { key: 'audience', label: 'Audience' },
  ],
}

const STATUSES = ['live', 'partial', 'planned', 'deprecated']

const LOCATION_LABEL = {
  channel: 'platform',
  persona: 'market',
  source: 'reliability',
  witness: 'role',
  customer_segment: 'size',
  service_offering: 'price',
  page: 'url',
  asset: 'format',
  metric: 'value',
  theory: 'confidence',
  territory: 'route',
}

function labelFor(kind) {
  return LOCATION_LABEL[kind] || 'location'
}

export function ComponentsTab({ project, components, onCreate, onPatch, onDelete }) {
  const kinds = KINDS_BY_TEMPLATE[project.template] || KINDS_BY_TEMPLATE.software
  const [adding, setAdding] = useState(null)
  const [newName, setNewName] = useState('')

  const byKind = {}
  for (const c of components) {
    if (!byKind[c.kind]) byKind[c.kind] = []
    byKind[c.kind].push(c)
  }

  async function quickAdd(kind) {
    if (!newName.trim()) {
      setAdding(null)
      return
    }
    await onCreate({
      project_id: project.id,
      name: newName.trim(),
      kind,
      status: 'planned',
      description: '',
      public: false,
      position: (byKind[kind] || []).length,
    })
    setNewName('')
    setAdding(null)
  }

  return (
    <div>
      {kinds.map(k => {
        const items = byKind[k.key] || []
        return (
          <div key={k.key} className="mb-9">
            <div className="flex items-baseline justify-between pb-2 mb-3 border-b border-rule-soft">
              <h3 className="font-display text-xl font-medium text-ink">{k.label}</h3>
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-[10px] uppercase tracking-wider text-ink-4">{items.length}</span>
                {adding === k.key ? (
                  <input
                    autoFocus
                    type="text"
                    value={newName}
                    placeholder={`new ${k.label.toLowerCase().replace(/s$/, '')}…`}
                    onChange={e => setNewName(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') quickAdd(k.key)
                      if (e.key === 'Escape') { setAdding(null); setNewName('') }
                    }}
                    onBlur={() => quickAdd(k.key)}
                    className="font-mono text-xs bg-paper-deep border-none focus:outline-none px-3 py-1 rounded w-48"
                  />
                ) : (
                  <button
                    onClick={() => setAdding(k.key)}
                    className="font-mono text-[10px] uppercase tracking-wider text-ink-3 hover:text-terracotta-deep"
                  >+ add</button>
                )}
              </div>
            </div>
            {items.length === 0 ? (
              <p className="text-sm text-ink-4 italic py-2">none yet</p>
            ) : (
              <div className="space-y-2">
                {items.map(c => (
                  <ComponentRow
                    key={c.id}
                    component={c}
                    locationLabel={labelFor(c.kind)}
                    onPatch={(patch) => onPatch(c.id, patch)}
                    onDelete={() => onDelete(c.id)}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function ComponentRow({ component, locationLabel, onPatch, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const dotColor = {
    live: '#5B7C45',
    partial: '#B07A2C',
    planned: '#A89F93',
    deprecated: '#7A726A',
  }[component.status] || '#A89F93'

  return (
    <div className="py-3 px-4 bg-paper-deep/40 border border-rule-soft rounded">
      <div className="flex items-baseline gap-3">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: dotColor }} />
        <EditableText
          value={component.name}
          onSave={(v) => onPatch({ name: v })}
          className="font-display text-base font-medium flex-1 block"
        />
        <select
          value={component.status}
          onChange={(e) => onPatch({ status: e.target.value })}
          className={`font-mono text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 cursor-pointer border-none focus:outline-none ${
            component.status === 'live' ? 'bg-sage-wash text-[#2F4824]' :
            component.status === 'partial' ? 'bg-amber-wash text-[#6E4D1A]' :
            component.status === 'deprecated' ? 'border border-rule text-ink-4' :
            'bg-paper-deep text-ink-3'
          }`}
        >
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          onClick={() => onPatch({ public: !component.public })}
          title={component.public ? 'public — click to make private' : 'private — click to publish'}
          className={`font-mono text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 transition-colors ${
            component.public
              ? 'bg-terracotta-wash text-terracotta-deep hover:bg-[#EAC9B0]'
              : 'border border-rule-soft text-ink-4 hover:text-terracotta-deep hover:border-terracotta'
          }`}
        >
          {component.public ? 'public' : 'private'}
        </button>
        <button
          onClick={() => setExpanded(!expanded)}
          className="font-mono text-[9px] uppercase tracking-wider text-ink-3 hover:text-ink"
        >
          {expanded ? '▴' : '▾'}
        </button>
      </div>
      {expanded && (
        <div className="mt-3 pl-5 space-y-2">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3 mb-1">Description</div>
            <EditableText
              multiline
              value={component.description}
              onSave={(v) => onPatch({ description: v })}
              placeholder="What is this and what does it do?"
              className="text-sm text-ink-2 leading-snug block w-full"
            />
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3 mb-1">{locationLabel}</div>
            <EditableText
              value={component.location || ''}
              onSave={(v) => onPatch({ location: v })}
              placeholder="file path, url, owner, etc."
              className="font-mono text-xs text-ink-2 block w-full"
            />
          </div>
          <button
            onClick={() => { if (confirm(`delete ${component.name}?`)) onDelete() }}
            className="font-mono text-[10px] uppercase tracking-wider text-ink-4 hover:text-terracotta-deep"
          >delete component</button>
        </div>
      )}
    </div>
  )
}
