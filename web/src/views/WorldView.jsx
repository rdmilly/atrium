import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { EditableText } from '../components/EditableText'

const TABS = [
  { key: 'pulse', label: 'Pulse' },
  { key: 'workbench', label: 'Workbench' },
  { key: 'patterns', label: 'Patterns' },
  { key: 'decisions', label: 'Decisions' },
]

export function WorldView({ projectMap }) {
  const [tab, setTab] = useState('pulse')
  const [events, setEvents] = useState([])
  const [workbench, setWorkbench] = useState([])
  const [patterns, setPatterns] = useState([])
  const [decisions, setDecisions] = useState([])

  const reloadWorkbench = () => api.listWorkbench().then(setWorkbench).catch(() => setWorkbench([]))
  const reloadPatterns = () => api.listPatterns().then(setPatterns).catch(() => setPatterns([]))
  const reloadDecisions = () => api.listDecisions().then(setDecisions).catch(() => setDecisions([]))

  useEffect(() => {
    if (tab === 'pulse') api.listEvents().then(setEvents).catch(() => setEvents([]))
    if (tab === 'workbench') reloadWorkbench()
    if (tab === 'patterns') reloadPatterns()
    if (tab === 'decisions') reloadDecisions()
  }, [tab])

  async function patchWorkbench(id, patch) {
    await api.patchWorkbench(id, patch)
    reloadWorkbench()
  }
  async function patchPattern(id, patch) {
    await api.patchPattern(id, patch)
    reloadPatterns()
  }
  async function patchDecision(id, patch) {
    await api.patchDecision(id, patch)
    reloadDecisions()
  }

  return (
    <div>
      <div className="flex gap-1 border-b border-rule mb-7 -mt-2">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-3 font-mono text-sm uppercase tracking-wider transition-colors ${
              tab === t.key
                ? 'text-terracotta-deep border-b-2 border-terracotta -mb-px'
                : 'text-ink-3 hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'pulse' && <PulseTab events={events} />}
      {tab === 'workbench' && <WorkbenchTab items={workbench} projectMap={projectMap} onPatch={patchWorkbench} />}
      {tab === 'patterns' && <PatternsTab patterns={patterns} onPatch={patchPattern} />}
      {tab === 'decisions' && <DecisionsTab decisions={decisions} projectMap={projectMap} onPatch={patchDecision} />}
    </div>
  )
}

function PulseTab({ events }) {
  if (events.length === 0) {
    return <p className="text-ink-3 italic font-display text-lg">No recent activity to show.</p>
  }
  const grouped = {}
  events.forEach(e => {
    const date = new Date(e.created_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    if (!grouped[date]) grouped[date] = []
    grouped[date].push(e)
  })
  return (
    <div>
      {Object.entries(grouped).map(([date, items]) => (
        <div key={date} className="mb-7">
          <h3 className="font-mono text-[11px] uppercase tracking-wider text-ink-3 pb-2 mb-3 border-b border-rule-soft">{date}</h3>
          {items.map(e => (
            <div key={e.id} className="grid grid-cols-[80px_1fr_60px] gap-4 py-2.5 border-b border-rule-soft last:border-b-0">
              <span className={`font-mono text-xs uppercase tracking-wider ${e.actor === 'claude' ? 'text-terracotta-deep' : e.actor === 'ryan' ? 'text-ink-2' : 'text-ink-4'}`}>{e.actor}</span>
              <div className="text-sm">
                <span className="text-ink-2">{e.action.replace(/_/g, ' ')}</span>
                {e.payload?.title && <span className="text-ink ml-1.5">· {e.payload.title}</span>}
                {e.payload?.question && <span className="text-ink ml-1.5">· {e.payload.question}</span>}
                {e.payload?.name && <span className="text-ink ml-1.5">· {e.payload.name}</span>}
                {e.payload?.tag && <span className="text-ink-3 font-mono text-[10px] ml-1.5">{e.payload.tag}</span>}
              </div>
              <span className="text-right font-mono text-[10px] text-ink-4">
                {new Date(e.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function WorkbenchTab({ items, projectMap, onPatch }) {
  const sections = ['hypothesis', 'question', 'plan', 'pattern', 'scratch']
  const grouped = Object.fromEntries(sections.map(s => [s, []]))
  items.forEach(i => { if (grouped[i.section]) grouped[i.section].push(i) })

  return (
    <div className="grid grid-cols-2 gap-x-9 gap-y-7">
      {sections.map(s => (
        <div key={s}>
          <h4 className="font-mono text-[11px] uppercase tracking-wider font-medium text-ink-3 pb-2.5 mb-3.5 border-b border-rule-soft flex items-baseline justify-between">
            <span>{s}</span>
            <span className="text-ink-4 font-normal">{grouped[s].length}</span>
          </h4>
          {grouped[s].length === 0 && <p className="text-sm text-ink-3 italic">no items</p>}
          {grouped[s].map(item => (
            <div key={item.id} className="py-3 border-b border-rule-soft last:border-b-0">
              <EditableText
                multiline
                value={item.body}
                onSave={(v) => onPatch(item.id, { body: v })}
                className="text-sm text-ink leading-snug block w-full"
              />
              {item.project_id && projectMap[item.project_id] && (
                <div className="flex items-baseline gap-1.5 mt-1.5">
                  <span className="w-1 h-1 rounded-sm flex-shrink-0" style={{ background: projectMap[item.project_id].glyph_color }} />
                  <span className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{projectMap[item.project_id].name}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function PatternsTab({ patterns, onPatch }) {
  const promoted = patterns.filter(p => p.status === 'promoted')
  const candidates = patterns.filter(p => p.status === 'candidate')

  const renderPattern = (p, dim) => (
    <div key={p.id} className="py-4 border-b border-rule-soft last:border-b-0">
      <div className="flex items-baseline gap-3 mb-1.5">
        <EditableText
          value={p.name}
          onSave={(v) => onPatch(p.id, { name: v })}
          className={`font-display text-lg font-medium ${dim ? 'text-ink-2' : ''} flex-1`}
        />
        <select
          value={p.status}
          onChange={(e) => onPatch(p.id, { status: e.target.value })}
          className="font-mono text-[10px] uppercase tracking-wider text-ink-4 bg-transparent border-none cursor-pointer focus:outline-none"
        >
          <option value="candidate">candidate</option>
          <option value="promoted">promoted</option>
          <option value="deprecated">deprecated</option>
        </select>
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-4">used {p.candidate_count}×</span>
      </div>
      <EditableText
        multiline
        value={p.description}
        onSave={(v) => onPatch(p.id, { description: v })}
        className={`text-sm ${dim ? 'text-ink-3' : 'text-ink-2'} leading-snug block w-full`}
      />
    </div>
  )

  return (
    <div>
      {promoted.length > 0 && (
        <div className="mb-9">
          <h3 className="font-mono text-[11px] uppercase tracking-wider text-ink-3 pb-2.5 mb-4 border-b border-rule-soft flex items-baseline justify-between">
            <span>Promoted patterns</span>
            <span className="text-ink-4 font-normal">{promoted.length}</span>
          </h3>
          {promoted.map(p => renderPattern(p, false))}
        </div>
      )}
      {candidates.length > 0 && (
        <div>
          <h3 className="font-mono text-[11px] uppercase tracking-wider text-ink-3 pb-2.5 mb-4 border-b border-rule-soft flex items-baseline justify-between">
            <span>Candidate patterns</span>
            <span className="text-ink-4 font-normal">{candidates.length}</span>
          </h3>
          {candidates.map(p => renderPattern(p, true))}
        </div>
      )}
      {patterns.length === 0 && <p className="text-ink-3 italic font-display text-lg">No patterns catalogued yet.</p>}
    </div>
  )
}

function DecisionsTab({ decisions, projectMap, onPatch }) {
  if (decisions.length === 0) {
    return <p className="text-ink-3 italic font-display text-lg">No decisions logged yet.</p>
  }
  return (
    <div>
      {decisions.map(d => {
        const project = projectMap[d.project_id]
        return (
          <div key={d.id} className="py-5 border-b border-rule-soft last:border-b-0">
            <div className="flex items-baseline gap-3 mb-2">
              {project && (
                <span className="flex items-baseline gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-sm" style={{ background: project.glyph_color }} />
                  <span className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{project.name}</span>
                </span>
              )}
              <select
                value={d.status}
                onChange={(e) => onPatch(d.id, { status: e.target.value })}
                className={`font-mono text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 cursor-pointer border-none focus:outline-none ${
                  d.status === 'resolved' ? 'bg-sage-wash text-[#2F4824]' :
                  d.status === 'revisit' ? 'bg-amber-wash text-[#6E4D1A]' :
                  'bg-paper-deep text-ink-2'
                }`}
              >
                <option value="open">open</option>
                <option value="resolved">resolved</option>
                <option value="revisit">revisit</option>
              </select>
            </div>
            <EditableText value={d.question} onSave={(v) => onPatch(d.id, { question: v })} className="font-display text-lg font-medium mb-2 leading-snug block w-full" />
            <EditableText value={d.choice || ''} onSave={(v) => onPatch(d.id, { choice: v })} placeholder="→ chosen path" className="text-sm text-ink mb-1.5 block w-full" />
            <EditableText multiline value={d.reasoning || ''} onSave={(v) => onPatch(d.id, { reasoning: v })} placeholder="why this choice" className="text-sm text-ink-2 italic leading-snug block w-full" />
          </div>
        )
      })}
    </div>
  )
}
