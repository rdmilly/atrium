import { useState } from 'react'
import { EditableText } from '../components/EditableText'

// Layer order from "surface" (user-facing) to "foundation" (storage/external)
const SOFTWARE_LAYERS = [
  { key: 'frontend',    label: 'Frontend · user surfaces' },
  { key: 'cli',         label: 'CLI · command-line entry' },
  { key: 'service',     label: 'Service · long-running processes' },
  { key: 'module',      label: 'Module · internal logic' },
  { key: 'library',     label: 'Library · shared code' },
  { key: 'datastore',   label: 'Datastore · state' },
  { key: 'integration', label: 'Integration · external systems' },
]

const STATUS_DOT = {
  live: 'bg-sage',
  partial: 'bg-amber',
  planned: 'bg-ink-4',
  deprecated: 'bg-ink-3',
}

export function ArchitectureTab({ project, components, onPatchComponent }) {
  if (project.template !== 'software') {
    return (
      <div className="py-12 text-center">
        <h3 className="font-display text-2xl text-ink-3 mb-2">Architecture view</h3>
        <p className="text-sm text-ink-4 italic max-w-md mx-auto">
          The architecture view is currently software-template specific. Other template visualizations
          (growth funnel diagram, services route map, investigation timeline) are coming.
        </p>
      </div>
    )
  }

  // Group components by layer (using kind)
  const byLayer = {}
  for (const c of components) {
    if (!byLayer[c.kind]) byLayer[c.kind] = []
    byLayer[c.kind].push(c)
  }

  const populatedLayers = SOFTWARE_LAYERS.filter(l => (byLayer[l.key] || []).length > 0)

  if (populatedLayers.length === 0) {
    return (
      <div className="py-12 text-center">
        <h3 className="font-display text-2xl text-ink-3 mb-2">Nothing to draw yet</h3>
        <p className="text-sm text-ink-4 italic max-w-md mx-auto">
          Add components on the Components tab to see them stack into a layered architecture view here.
        </p>
      </div>
    )
  }

  return (
    <div>
      <p className="font-mono text-[11px] uppercase tracking-wider text-ink-3 mb-6">
        Layers, surface to foundation. Component dot color = status.
      </p>
      <div className="space-y-3">
        {populatedLayers.map(layer => {
          const items = byLayer[layer.key]
          return (
            <div key={layer.key} className="border border-rule-soft rounded">
              <div className="px-4 py-2.5 bg-paper-deep/50 border-b border-rule-soft">
                <div className="font-mono text-[11px] uppercase tracking-wider text-ink-2">
                  {layer.label}
                  <span className="text-ink-4 ml-2">{items.length}</span>
                </div>
              </div>
              <div className="p-3 grid grid-cols-2 gap-2">
                {items.map(c => {
                  const dotClass = STATUS_DOT[c.status] || STATUS_DOT.planned
                  return (
                    <div key={c.id} className="flex items-baseline gap-2 px-3 py-2 bg-surface border border-rule-soft rounded">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClass}`} />
                      <span className="font-display text-sm font-medium flex-1 truncate" title={c.name}>{c.name}</span>
                      {c.public && <span className="font-mono text-[9px] uppercase tracking-wider text-terracotta-deep">pub</span>}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-8 pt-6 border-t border-rule-soft">
        <h4 className="font-mono text-[11px] uppercase tracking-wider text-ink-3 mb-3">Status legend</h4>
        <div className="flex gap-5 flex-wrap text-sm">
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-sage" /> live</span>
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber" /> partial</span>
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-ink-4" /> planned</span>
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-ink-3" /> deprecated</span>
        </div>
      </div>
    </div>
  )
}
