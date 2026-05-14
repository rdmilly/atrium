import { useEffect, useState, useCallback } from 'react'
import { api, connectWS } from './lib/api'
import { EditableText } from './components/EditableText'
import { WorldView } from './views/WorldView'
import { ProjectSheet } from './views/ProjectSheet'

const PHASE_GROUPS = [
  { key: 'active', label: 'Active', defaultOpen: true },
  { key: 'specced', label: 'Specced', defaultOpen: true },
  { key: 'stable', label: 'Stable', defaultOpen: false },
  { key: 'paused', label: 'Paused', defaultOpen: true },
  { key: 'shipped', label: 'Shipped', defaultOpen: false },
  { key: 'retired', label: 'Retired', defaultOpen: false },
]

export default function App() {
  const [view, setView] = useState('canvas')
  const [projects, setProjects] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [project, setProject] = useState(null)
  const [tasks, setTasks] = useState([])
  const [decisions, setDecisions] = useState([])
  const [notes, setNotes] = useState([])
  const [intel, setIntel] = useState([])
  const [components, setComponents] = useState([])
  const [allTasks, setAllTasks] = useState([])
  const [allIntel, setAllIntel] = useState([])
  const [openGroups, setOpenGroups] = useState(() => Object.fromEntries(PHASE_GROUPS.map(g => [g.key, g.defaultOpen])))

  const refresh = useCallback(async () => {
    const ps = await api.listProjects()
    setProjects(ps)
    if (!activeId && ps.length) setActiveId(ps.find(p => p.phase === 'active')?.id || ps[0].id)
  }, [activeId])

  useEffect(() => { refresh() }, [refresh])

  const loadCanvas = useCallback(async () => {
    if (!activeId) return
    const [p, ts, ds, ns, ins, cs] = await Promise.all([
      api.getProject(activeId),
      api.listTasks(activeId),
      api.listDecisions(activeId),
      api.listNotes({ target_type: 'project', target_id: activeId, status: 'open' }),
      api.listIntel('project', activeId),
      api.listComponents(activeId).catch(() => []),
    ])
    setProject(p); setTasks(ts); setDecisions(ds); setNotes(ns); setIntel(ins); setComponents(cs)
  }, [activeId])

  useEffect(() => { if (view === 'canvas') loadCanvas() }, [activeId, view, loadCanvas])

  useEffect(() => {
    if (view !== 'world') return
    api.listTasks().then(setAllTasks).catch(() => setAllTasks([]))
    api.listIntel().then(setAllIntel).catch(() => setAllIntel([]))
  }, [view])

  useEffect(() => {
    const ws = connectWS(() => {
      if (view === 'canvas') loadCanvas()
      if (view === 'world') {
        api.listTasks().then(setAllTasks)
        api.listIntel().then(setAllIntel)
      }
      api.listProjects().then(setProjects)
    })
    return () => ws.close()
  }, [view, loadCanvas])

  const grouped = PHASE_GROUPS.map(g => ({ ...g, items: projects.filter(p => p.phase === g.key) })).filter(g => g.items.length > 0)
  const projectMap = Object.fromEntries(projects.map(p => [p.id, p]))

  const upNextSrc = view === 'canvas' ? tasks : allTasks
  const upNext = upNextSrc
    .filter(t => ['today', 'next'].includes(t.status))
    .sort((a, b) => (a.status === 'today' ? -1 : 1) - (b.status === 'today' ? -1 : 1) || a.position - b.position)
    .slice(0, view === 'world' ? 8 : 20)
  const intelToShow = view === 'canvas' ? intel : allIntel

  async function patchProject(field, value) {
    if (!project) return
    const updated = await api.patchProject(project.id, { [field]: value })
    setProject(updated)
    api.listProjects().then(setProjects)
  }

  async function patchTask(id, patch) {
    await api.patchTask(id, patch)
    if (view === 'canvas') api.listTasks(activeId).then(setTasks)
    else api.listTasks().then(setAllTasks)
  }

  async function patchDecision(id, patch) {
    await api.patchDecision(id, patch)
    if (view === 'canvas') api.listDecisions(activeId).then(setDecisions)
  }

  async function patchNote(id, patch) {
    await api.patchNote(id, patch)
    if (activeId) api.listNotes({ target_type: 'project', target_id: activeId, status: 'open' }).then(setNotes)
  }

  async function createComponent(data) {
    await api.createComponent(data)
    if (activeId) api.listComponents(activeId).then(setComponents)
  }

  async function patchComponent(id, patch) {
    await api.patchComponent(id, patch)
    if (activeId) api.listComponents(activeId).then(setComponents)
  }

  async function deleteComponent(id) {
    await api.deleteComponent(id)
    if (activeId) api.listComponents(activeId).then(setComponents)
  }

  function selectChamber(id) { setActiveId(id); setView('canvas') }

  return (
    <div className="max-w-[1400px] mx-auto px-10 py-8 relative z-10">
      <header className="flex items-baseline gap-6 pb-5 border-b border-rule mb-6">
        <div>
          <h1 className="font-display text-3xl tracking-tight">Atrium</h1>
          <span className="font-mono text-xs text-ink-3 uppercase tracking-wider mt-2 block">Ryan's command center</span>
        </div>
        <div className="ml-4 flex bg-paper-deep rounded-full p-1 self-center">
          {['canvas', 'world'].map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-4 py-1.5 font-mono text-[11px] uppercase tracking-wider rounded-full transition-colors ${view === v ? 'bg-surface text-ink' : 'text-ink-3 hover:text-ink'}`}>
              {v}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-5 font-mono text-sm text-ink-2">
          <Status dotColor="#5B7C45" label="helix" />
          <Status dotColor="#5B7C45" label="vps2" />
          {view === 'canvas' && <NotesBadge count={notes.length} />}
        </div>
      </header>

      <div className="flex items-center gap-3 pb-4 font-mono text-sm text-ink-3">
        <span className="w-2 h-2 rounded-full bg-terracotta" />
        <span>Atrium is live · {projects.length} projects · {view === 'canvas' ? `viewing ${project?.name || '…'}` : 'world view'}</span>
      </div>

      <main className="grid grid-cols-[220px_1fr_240px] gap-10 items-start">
        <aside className="sticky top-8 max-h-[calc(100vh-4rem)] flex flex-col">
          <div className="font-mono text-xs uppercase tracking-wider text-ink-3 pb-3 border-b border-rule mb-1">
            Projects · {projects.length}
          </div>
          <div className="flex-1 overflow-y-auto pr-1">
            {grouped.map(g => (
              <div key={g.key}>
                <button
                  onClick={() => setOpenGroups(o => ({ ...o, [g.key]: !o[g.key] }))}
                  className="w-full flex items-baseline justify-between font-mono text-xs uppercase tracking-wider text-ink-3 py-3 border-t border-rule first:border-t-0 hover:text-ink"
                >
                  <span>{g.label} <span className="text-ink-4">{g.items.length}</span></span>
                  <span className={`text-[9px] transition-transform ${openGroups[g.key] ? '' : '-rotate-90'}`}>▾</span>
                </button>
                {openGroups[g.key] && g.items.map(p => (
                  <Chamber key={p.id} project={p} active={view === 'canvas' && p.id === activeId}
                    notesCount={view === 'canvas' && p.id === activeId ? notes.length : 0}
                    onClick={() => selectChamber(p.id)} />
                ))}
              </div>
            ))}
          </div>
        </aside>

        <section className="bg-surface border border-rule p-9 min-h-[720px]">
          {view === 'canvas' ? (
            project ? (
              <ProjectSheet
                project={project} tasks={tasks} decisions={decisions} notes={notes}
                components={components}
                onPatch={patchProject}
                onPatchTask={patchTask}
                onPatchDecision={patchDecision}
                onPatchNote={patchNote}
                onCreateComponent={createComponent}
                onPatchComponent={patchComponent}
                onDeleteComponent={deleteComponent}
              />
            ) : (
              <div className="text-ink-3 font-display italic text-lg">Click a project chamber to begin.</div>
            )
          ) : (
            <WorldView projectMap={projectMap} />
          )}
        </section>

        <aside className="sticky top-8 max-h-[calc(100vh-4rem)] flex flex-col gap-6">
          <div className="flex-1 min-h-[240px] flex flex-col">
            <div className="font-mono text-xs uppercase tracking-wider text-ink-3 pb-3 border-b border-rule mb-3">
              Up Next · {view === 'canvas' ? (project?.name || '') : 'all projects'} · {upNext.length}
            </div>
            <div className="flex-1 overflow-y-auto">
              {upNext.length === 0 && <p className="text-sm text-ink-3 italic">no tasks queued</p>}
              {upNext.map((t, i) => (
                <div key={t.id} className={`grid grid-cols-[24px_1fr] gap-2 py-2.5 border-b border-rule-soft ${i === 0 ? 'bg-terracotta-wash -mx-3 px-3' : ''}`}>
                  <span className={`font-mono text-xs text-right ${i === 0 ? 'text-terracotta-deep font-medium' : 'text-ink-4'}`}>{i + 1}</span>
                  <div>
                    <EditableText value={t.title} onSave={(v) => patchTask(t.id, { title: v })} className="text-sm leading-snug text-ink mb-1 block w-full" />
                    <div className="flex gap-3 items-baseline">
                      <select
                        value={t.status}
                        onChange={(e) => patchTask(t.id, { status: e.target.value })}
                        className="font-mono text-[10px] uppercase tracking-wider bg-transparent border-none text-ink-3 cursor-pointer focus:outline-none"
                      >
                        <option value="today">today</option>
                        <option value="next">next</option>
                        <option value="blocked">blocked</option>
                        <option value="later">later</option>
                        <option value="done">done</option>
                      </select>
                      {t.effort && <span className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{t.effort}</span>}
                      {view === 'world' && projectMap[t.project_id] && (
                        <span className="flex items-baseline gap-1">
                          <span className="w-1 h-1 rounded-sm" style={{ background: projectMap[t.project_id].glyph_color }} />
                          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{projectMap[t.project_id].name}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 min-h-[300px] flex flex-col">
            <div className="font-mono text-xs uppercase tracking-wider text-ink-3 pb-3 border-b border-rule mb-3">
              Intelligence · {view === 'world' ? 'global' : 'project'}
            </div>
            <div className="flex-1 overflow-y-auto">
              {intelToShow.length === 0 && <p className="text-sm text-ink-3 italic">no items right now</p>}
              {intelToShow.map(i => (
                <div key={i.id} className="py-3 border-b border-rule-soft">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3 mb-1">{i.source}</div>
                  <div className="text-sm leading-snug text-ink-2">{i.body}</div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

function Chamber({ project, active, notesCount, onClick }) {
  return (
    <div onClick={onClick}
      className={`py-4 border-b border-rule-soft cursor-pointer relative transition-transform hover:translate-x-0.5 ${active ? 'before:absolute before:-left-4 before:top-5 before:w-2 before:h-2 before:bg-terracotta before:rotate-45' : ''}`}>
      <div className="flex items-baseline gap-2">
        <span className="w-1.5 h-1.5 rounded-sm flex-shrink-0 -translate-y-0.5" style={{ background: project.glyph_color }} />
        <span className={`font-display text-lg leading-tight flex-1 ${active ? 'text-terracotta-deep' : ''}`}>{project.name}</span>
        {notesCount > 0 && <span className="font-hand text-base text-terracotta">{notesCount}</span>}
      </div>
      <div className="ml-4 mt-1.5 font-mono text-xs text-ink-3">{project.phase}</div>
      <div className="ml-4 mt-2 h-px bg-rule-soft relative">
        <div className="absolute inset-y-0 left-0" style={{ width: `${project.progress}%`, background: project.glyph_color }} />
      </div>
    </div>
  )
}

function Status({ dotColor, label }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: dotColor }} />
      {label}
    </span>
  )
}

function NotesBadge({ count }) {
  if (!count) return null
  return (
    <span className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-terracotta-wash text-terracotta-deep rounded-full font-hand text-lg font-medium">
      {count} note{count !== 1 ? 's' : ''}
    </span>
  )
}
