import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { EditableText } from '../components/EditableText'
import { ComponentsTab } from './ComponentsTab'
import { ArchitectureTab } from './ArchitectureTab'

// Tab definitions per template. The 'overview' tab is universal; everything else is template-specific.
const TEMPLATES = {
  software: {
    label: 'Software',
    tabs: ['overview', 'roadmap', 'architecture', 'decisions', 'components', 'questions', 'journal'],
  },
  growth: {
    label: 'Growth',
    tabs: ['overview', 'audience', 'channels', 'funnel', 'content', 'metrics', 'journal'],
  },
  services: {
    label: 'Services',
    tabs: ['overview', 'customers', 'schedule', 'pricing', 'journal'],
  },
  investigation: {
    label: 'Investigation',
    tabs: ['overview', 'sources', 'timeline', 'theories', 'evidence', 'journal'],
  },
  portfolio: {
    label: 'Portfolio',
    tabs: ['overview', 'pages', 'assets', 'audience', 'journal'],
  },
}

const TAB_LABELS = {
  overview: 'Overview',
  roadmap: 'Roadmap',
  decisions: 'Decisions',
  components: 'Components',
  architecture: 'Architecture',
  questions: 'Questions',
  journal: 'Journal',
  audience: 'Audience',
  channels: 'Channels',
  funnel: 'Funnel',
  content: 'Content',
  metrics: 'Metrics',
  customers: 'Customers',
  schedule: 'Schedule',
  pricing: 'Pricing',
  sources: 'Sources',
  timeline: 'Timeline',
  theories: 'Theories',
  evidence: 'Evidence',
  pages: 'Pages',
  assets: 'Assets',
}

export function ProjectSheet({ project, tasks, decisions, notes, components, onPatch, onPatchTask, onPatchDecision, onPatchNote, onCreateComponent, onPatchComponent, onDeleteComponent, onReloadTasks }) {
  const [tab, setTab] = useState('overview')
  const tmpl = TEMPLATES[project.template] || TEMPLATES.software
  const tabs = tmpl.tabs

  // reset tab when project changes
  useEffect(() => { setTab('overview') }, [project.id])

  return (
    <div>
      {/* Project header — always shown */}
      <div className="flex items-baseline gap-3 pb-6 border-b border-rule mb-6">
        <span className="w-3 h-3 rounded-sm flex-shrink-0 translate-y-0.5" style={{ background: project.glyph_color }} />
        <EditableText
          value={project.name}
          onSave={(v) => onPatch('name', v)}
          className="font-display text-4xl tracking-tight leading-none flex-1"
        />
        {project.public && project.slug && (
          <a
            href={`/p/${project.slug}`}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-[10px] uppercase tracking-widest text-terracotta-deep hover:underline"
            title="open the public page in a new tab"
          >
            view public ↗
          </a>
        )}
        <button
          onClick={() => onPatch('public', !project.public)}
          title={project.public ? 'public — click to make private' : 'private — click to publish'}
          className={`font-mono text-[10px] uppercase tracking-widest rounded-full py-1.5 px-3 transition-colors ${
            project.public
              ? 'bg-terracotta-wash text-terracotta-deep hover:bg-[#EAC9B0]'
              : 'border border-rule text-ink-3 hover:border-terracotta hover:text-terracotta-deep'
          }`}
        >
          {project.public ? 'public' : 'private'}
        </button>
        <select
          value={project.template}
          onChange={(e) => onPatch('template', e.target.value)}
          className="font-mono text-[10px] uppercase tracking-widest border border-rule bg-transparent text-ink-3 rounded-full py-1.5 px-3 hover:border-ink-3 focus:outline-none focus:border-terracotta cursor-pointer"
        >
          {Object.entries(TEMPLATES).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <span className="font-mono text-xs uppercase tracking-widest border border-current text-sage rounded-full py-1.5 px-3">
          {project.phase}
        </span>
      </div>

      {/* Open notes banner — always shown above tabs */}
      {notes.length > 0 && (
        <div className="bg-terracotta-wash p-5 mb-6 border-l-2 border-terracotta">
          <h3 className="font-mono text-[11px] uppercase tracking-wider text-terracotta-deep font-medium mb-3">
            Your notes on this project · {notes.length} open
          </h3>
          {notes.map(n => (
            <div key={n.id} className="flex items-baseline gap-3 my-2">
              <span className="font-mono text-[10px] uppercase tracking-wider font-medium text-terracotta-deep bg-surface px-2 py-0.5 rounded-sm flex-shrink-0">{n.tag}</span>
              <span className="font-hand text-xl leading-snug text-ink">{n.body}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tab strip */}
      <div className="flex gap-1 border-b border-rule mb-7 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-3 font-mono text-xs uppercase tracking-wider transition-colors whitespace-nowrap ${
              tab === t
                ? 'text-terracotta-deep border-b-2 border-terracotta -mb-px'
                : 'text-ink-3 hover:text-ink'
            }`}
          >
            {TAB_LABELS[t] || t}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab project={project} tasks={tasks} decisions={decisions} onPatch={onPatch} />}
      {tab === 'roadmap' && <RoadmapTab project={project} tasks={tasks} onPatchTask={onPatchTask} />}
      {tab === 'decisions' && <DecisionsTab decisions={decisions} onPatchDecision={onPatchDecision} />}
      {tab === 'components' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'architecture' && <ArchitectureTab project={project} components={components || []} onPatchComponent={onPatchComponent} />}
      {tab === 'questions' && <QuestionsTab notes={notes} onPatchNote={onPatchNote} />}
      {tab === 'journal' && <JournalTab project={project} onPatch={onPatch} />}
      {tab === 'audience' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'channels' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'funnel' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'content' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'metrics' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'customers' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'schedule' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'pricing' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'sources' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'timeline' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'theories' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'evidence' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'pages' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
      {tab === 'assets' && <ComponentsTab project={project} components={components || []} onCreate={onCreateComponent} onPatch={onPatchComponent} onDelete={onDeleteComponent} />}
    </div>
  )
}

function OverviewTab({ project, tasks, decisions, onPatch }) {
  const todayCount = tasks.filter(t => t.status === 'today').length
  const blockedCount = tasks.filter(t => t.status === 'blocked').length
  const openDecisions = decisions.filter(d => d.status === 'open').length

  return (
    <div className="grid grid-cols-2 gap-x-9 gap-y-7">
      <div className="col-span-2">
        <h4 className="font-mono text-[11px] uppercase tracking-wider font-medium text-ink-3 pb-2.5 mb-3.5 border-b border-rule-soft">Vision <span className="text-ink-4 font-normal">· internal</span></h4>
        <EditableText
          multiline
          value={project.vision}
          onSave={(v) => onPatch('vision', v)}
          placeholder="What is this project for?"
          className="font-display text-lg leading-snug min-h-[48px]"
        />
      </div>

      {project.public && (
        <div className="col-span-2">
          <h4 className="font-mono text-[11px] uppercase tracking-wider font-medium text-terracotta-deep pb-2.5 mb-3.5 border-b border-rule-soft">Public summary <span className="text-ink-4 font-normal">· shown on /p/{project.slug}</span></h4>
          <EditableText
            multiline
            value={project.public_summary}
            onSave={(v) => onPatch('public_summary', v)}
            placeholder="What you want the world to see. Two or three sentences."
            className="font-display italic text-lg leading-snug min-h-[60px]"
          />
        </div>
      )}

      <div className="col-span-2 grid grid-cols-4 gap-6 py-4 px-6 bg-paper-deep rounded">
        <Stat label="Progress" value={`${project.progress}%`} />
        <Stat label="Today" value={todayCount} />
        <Stat label="Blocked" value={blockedCount} accent={blockedCount > 0 ? 'terracotta' : null} />
        <Stat label="Open decisions" value={openDecisions} />
      </div>

      <div className="col-span-2">
        <h4 className="font-mono text-[11px] uppercase tracking-wider font-medium text-ink-3 pb-2.5 mb-3.5 border-b border-rule-soft">Journal</h4>
        <EditableText
          multiline
          value={project.journal}
          onSave={(v) => onPatch('journal', v)}
          placeholder="What's the narrative on this project right now?"
          className="font-display italic text-lg leading-relaxed min-h-[80px]"
        />
      </div>
    </div>
  )
}

function RoadmapTab({ project, tasks, onPatchTask }) {
  const buckets = ['today', 'next', 'blocked', 'later', 'done']
  const grouped = Object.fromEntries(buckets.map(b => [b, tasks.filter(t => t.status === b)]))

  return (
    <div className="grid grid-cols-2 gap-x-9 gap-y-7">
      {buckets.map(b => (
        <div key={b} className={b === 'done' ? 'col-span-2' : ''}>
          <h4 className="font-mono text-[11px] uppercase tracking-wider font-medium text-ink-3 pb-2.5 mb-3.5 border-b border-rule-soft flex items-baseline justify-between">
            <span>{b}</span>
            <span className="text-ink-4 font-normal">{grouped[b].length}</span>
          </h4>
          {grouped[b].length === 0 && <p className="text-sm text-ink-3 italic">no tasks here</p>}
          {grouped[b].map(t => (
            <div key={t.id} className="py-2.5 border-b border-rule-soft last:border-b-0">
              <EditableText value={t.title} onSave={(v) => onPatchTask(t.id, { title: v })} className="text-sm leading-snug text-ink block w-full" />
              <div className="flex gap-3 items-baseline mt-1">
                <select
                  value={t.status}
                  onChange={(e) => onPatchTask(t.id, { status: e.target.value })}
                  className="font-mono text-[10px] uppercase tracking-wider bg-transparent border-none text-ink-3 cursor-pointer focus:outline-none"
                >
                  {buckets.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                {t.effort && <span className="font-mono text-[10px] uppercase tracking-wider text-ink-4">· {t.effort}</span>}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function DecisionsTab({ decisions, onPatchDecision }) {
  if (decisions.length === 0) return <EmptyTab title="No decisions yet" hint="Log decisions as they get made so future-you knows why." />
  return (
    <div>
      {decisions.map(d => (
        <div key={d.id} className="py-5 border-b border-rule-soft last:border-b-0">
          <div className="flex items-baseline gap-3 mb-2">
            <select
              value={d.status}
              onChange={(e) => onPatchDecision(d.id, { status: e.target.value })}
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
            <button
              onClick={() => onPatchDecision(d.id, { public: !d.public })}
              title={d.public ? 'public — click to make private' : 'private — click to publish on the project page'}
              className={`font-mono text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 transition-colors ${
                d.public
                  ? 'bg-terracotta-wash text-terracotta-deep hover:bg-[#EAC9B0]'
                  : 'border border-rule-soft text-ink-4 hover:text-terracotta-deep hover:border-terracotta'
              }`}
            >
              {d.public ? 'public' : 'private'}
            </button>
          </div>
          <EditableText value={d.question} onSave={(v) => onPatchDecision(d.id, { question: v })} className="font-display text-lg font-medium mb-2 leading-snug block w-full" />
          <EditableText value={d.choice || ''} onSave={(v) => onPatchDecision(d.id, { choice: v })} placeholder="→ chosen path" className="text-sm text-ink mb-1.5 block w-full" />
          <EditableText multiline value={d.reasoning || ''} onSave={(v) => onPatchDecision(d.id, { reasoning: v })} placeholder="why this choice" className="text-sm text-ink-2 italic leading-snug block w-full" />
        </div>
      ))}
    </div>
  )
}

function JournalTab({ project, onPatch }) {
  return (
    <div>
      <EditableText
        multiline
        value={project.journal}
        onSave={(v) => onPatch('journal', v)}
        placeholder="What's the narrative on this project right now? What's been happening, what's been figured out, what's next?"
        className="font-display italic text-lg leading-relaxed min-h-[400px] block w-full"
      />
    </div>
  )
}


function QuestionsTab({ notes, onPatchNote }) {
  const questions = (notes || []).filter(n => n.tag === '?question' || n.tag === '!blocked')
  if (questions.length === 0) {
    return <EmptyTab title="No questions yet" hint="Add a note tagged ?question or !blocked from any project sheet to surface it here." />
  }
  return (
    <div>
      {questions.map(q => (
        <div key={q.id} className="flex items-baseline gap-3 py-3 border-b border-rule-soft last:border-b-0">
          <span className={`font-display text-2xl leading-none w-8 h-8 rounded-full inline-flex items-center justify-center font-medium flex-shrink-0 ${
            q.tag === '!blocked' ? 'bg-terracotta-wash text-terracotta-deep' : 'bg-paper-deep text-ink-3'
          }`}>
            {q.tag === '!blocked' ? '!' : '?'}
          </span>
          <span className="flex-1 font-display text-lg leading-snug text-ink">{q.body}</span>
          {onPatchNote && (
            <button
              onClick={() => onPatchNote(q.id, { public: !q.public })}
              title={q.public ? 'public — click to hide from page' : 'private — click to publish on page'}
              className={`font-mono text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 transition-colors ${
                q.public
                  ? 'bg-terracotta-wash text-terracotta-deep hover:bg-[#EAC9B0]'
                  : 'border border-rule-soft text-ink-4 hover:text-terracotta-deep hover:border-terracotta'
              }`}
            >
              {q.public ? 'public' : 'private'}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

function EmptyTab({ title, hint }) {
  return (
    <div className="py-12 text-center">
      <h3 className="font-display text-2xl text-ink-3 mb-2">{title}</h3>
      <p className="text-sm text-ink-4 italic max-w-md mx-auto">{hint}</p>
      <p className="text-xs text-ink-4 mt-6 font-mono uppercase tracking-wider">surface coming soon</p>
    </div>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div>
      <div className={`font-display text-3xl ${accent === 'terracotta' ? 'text-terracotta-deep' : 'text-ink'}`}>{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3 mt-1">{label}</div>
    </div>
  )
}
