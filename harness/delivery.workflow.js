export const meta = {
  name: 'launch-agents-delivery',
  description: 'Supervisor plans (or revises) ADRs + tickets; deliver stage runs waves of parallel builders through review (max 3 rounds) and the merge gate',
  whenToUse: 'Drive the agent harness in this repo. Args come from: bash scripts/harness_args.sh plan|revise|deliver',
  phases: [
    { title: 'Plan', detail: 'Supervisor writes or revises architecture ADRs and the ticket backlog (docs/ + tickets/ only)' },
    { title: 'Wave 0', detail: 'Foundation ticket: build, review loop, gate' },
    { title: 'Wave 1', detail: 'Parallel builders in isolated worktrees: build, review loop, gate' },
    { title: 'Wave 2', detail: 'Parallel builders in isolated worktrees: build, review loop, gate' },
    { title: 'Close', detail: 'Supervisor updates the backlog and ADR index' },
  ],
}

// args (see scripts/harness_args.sh):
//   repo, mode: 'human'|'auto', stage: 'plan'|'ask'|'revise'|'deliver', waves: [0,1],
//   minParallel: 5, feedback: '<owner question (ask) or change request (revise)>',
//   question_answers: {"Q-001": "<chosen option>"} (revise), answers: {"T-005": "<owner answer to a needs_human ticket>"} (deliver)
const REPO = args.repo
const MODE = args.mode || 'human'
const STAGE = args.stage || 'plan'
const WAVES = args.waves || [0, 1]
const MIN_PARALLEL = args.minParallel || 5
const ANSWERS = args.answers || {}
const MAX_ROUNDS = 3          // ADR-0002; also enforced by scripts/merge_pr.sh
const MAX_UNBLOCKS = 2
const MAX_GATE_ATTEMPTS = 3

// Everything that commits to the main checkout (gate merges, Supervisor commits) is serialized.
let lock = Promise.resolve()
function onMain(fn) { const run = lock.then(fn, fn); lock = run.then(() => {}, () => {}); return run }

const TICKET = { type: 'object', properties: {
  id: { type: 'string' }, title: { type: 'string' }, wave: { type: 'integer' },
  depends_on: { type: 'array', items: { type: 'string' } },
  file: { type: 'string', description: 'ticket file path relative to repo root' },
  owns: { type: 'array', items: { type: 'string' }, description: 'owned paths exactly as listed under ## Owns' },
  status: { type: 'string', description: 'todo / in_progress / in_review / merged / escalated / blocked' } },
  required: ['id', 'title', 'wave', 'depends_on', 'file', 'owns', 'status'] }
const QUESTION = { type: 'object', properties: {
  id: { type: 'string', description: 'Q-NNN' }, ticket: { type: 'string', description: 'T-NNN or empty' },
  question: { type: 'string', description: 'Plain language, no jargon' }, why_it_matters: { type: 'string' },
  options: { type: 'array', minItems: 2, maxItems: 4, items: { type: 'object', properties: { label: { type: 'string', description: '1-5 words' }, description: { type: 'string', description: 'one-line consequence' } }, required: ['label', 'description'] } },
  recommended: { type: 'string', description: 'label of the recommended option' } },
  required: ['id', 'ticket', 'question', 'why_it_matters', 'options', 'recommended'] }
const PLAN_SCHEMA = { type: 'object', properties: {
  owner_brief: { type: 'string', description: 'Plain-language brief for the product owner (ADR-0006): what you decided, what they get after each wave, what you need from them' },
  adrs: { type: 'array', items: { type: 'object', properties: { number: { type: 'string' }, title: { type: 'string' } }, required: ['number', 'title'] } },
  tickets: { type: 'array', items: TICKET },
  open_questions: { type: 'array', items: QUESTION, description: 'Open product questions for the owner (human mode); empty in auto mode' },
  commit: { type: 'string' } }, required: ['owner_brief', 'adrs', 'tickets', 'open_questions', 'commit'] }
const BUILD_SCHEMA = { type: 'object', properties: {
  status: { type: 'string', enum: ['READY_FOR_REVIEW', 'BLOCKED'] },
  head_commit: { type: 'string' }, verify_passed: { type: 'boolean' },
  tests_summary: { type: 'string' }, question: { type: 'string', description: 'Exact question for the Supervisor if BLOCKED, else empty' },
  summary: { type: 'string' } }, required: ['status', 'head_commit', 'verify_passed', 'tests_summary', 'question', 'summary'] }
const REVIEW_SCHEMA = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['APPROVED', 'CHANGES_REQUESTED'] },
  blocking: { type: 'array', items: { type: 'object', properties: { location: { type: 'string' }, problem: { type: 'string' }, expected: { type: 'string' } }, required: ['location', 'problem', 'expected'] } },
  non_blocking: { type: 'array', items: { type: 'string' } }, commit: { type: 'string' } },
  required: ['verdict', 'blocking', 'non_blocking', 'commit'] }
const UNBLOCK_SCHEMA = { type: 'object', properties: {
  needs_human: { type: 'boolean', description: 'true only in human mode, for a question about WHAT the product should do' },
  decision: { type: 'string', description: 'The decision (empty if needs_human)' },
  question_for_human: { anyOf: [QUESTION, { type: 'null' }], description: 'Structured question for the owner if needs_human, else null' },
  adr_path: { type: 'string' }, ticket_updated: { type: 'boolean' }, commit: { type: 'string' } },
  required: ['needs_human', 'decision', 'question_for_human', 'adr_path', 'ticket_updated', 'commit'] }
const ASK_SCHEMA = { type: 'object', properties: {
  answer: { type: 'string', description: 'Direct, plain-language answer' },
  references: { type: 'array', items: { type: 'string' }, description: 'ADR / ticket files that hold the detail' },
  suggested_change: { type: 'string', description: 'If the question implies a plan change, the revise feedback you would suggest; else empty' } },
  required: ['answer', 'references', 'suggested_change'] }
const GATE_SCHEMA = { type: 'object', properties: { exit_code: { type: 'integer' }, output_tail: { type: 'string' } }, required: ['exit_code', 'output_tail'] }

const PRE = (role) => `Repository: ${REPO} (the main checkout; it is your working directory). Shell: Git Bash on Windows (use the Bash tool for scripts).
Your role is ${role}. Read CLAUDE.md and .claude/agents/${role.toLowerCase()}.md first and follow them exactly.`
const MODE_NOTE = (MODE === 'human'
  ? 'SUPERVISOR_MODE=human: a human product owner reviews your plan before any builder starts. Where the brief leaves a real product choice open, make a sensible default decision in the ADR/ticket AND list it in open_questions (structured, with options and your recommendation) so the owner can confirm or change it in one click. Only ask what changes the product; decide technical matters yourself.'
  : 'SUPERVISOR_MODE=auto: nobody reviews your plan before builders start. Decide every open point yourself and record it in ADRs; return open_questions empty.')
  + ' Follow "Talking to the product owner" in your role file: write owner_brief in plain language and keep tickets/plan.json, tickets/BACKLOG.md and docs/product-decisions.md in sync with what you commit.'

// ---------------- Plan helpers ----------------
const norm = p => p.replace(/^\.\//, '')
const shared = p => /^evidence\//.test(p) || /^prs\//.test(p)
function overlap(a, b) { a = norm(a); b = norm(b); return a === b || (a.endsWith('/') && b.startsWith(a)) || (b.endsWith('/') && a.startsWith(b)) }
function planProblems(p) {
  const probs = [], waves = {}
  p.tickets.forEach(t => { (waves[t.wave] = waves[t.wave] || []).push(t) })
  if (!(waves[0] && waves[0].length === 1)) probs.push(`wave 0 must contain exactly one ticket (has ${(waves[0] || []).length})`)
  if (!(waves[1] && waves[1].length >= MIN_PARALLEL)) probs.push(`wave 1 must contain at least ${MIN_PARALLEL} parallel tickets (has ${(waves[1] || []).length})`)
  for (const w of Object.keys(waves)) {
    const ts = waves[w]
    for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++)
      for (const a of ts[i].owns.filter(x => !shared(x))) for (const b of ts[j].owns.filter(x => !shared(x)))
        if (overlap(a, b)) probs.push(`wave ${w}: ${ts[i].id} owns \`${a}\` which overlaps ${ts[j].id}'s \`${b}\``)
  }
  const ids = new Set(p.tickets.map(t => t.id))
  for (const t of p.tickets) {
    if (!/^T-\d{3}$/.test(t.id)) probs.push(`bad ticket id ${t.id}`)
    if (!t.owns.some(x => norm(x) === `evidence/${t.id}/`)) probs.push(`${t.id} does not own evidence/${t.id}/`)
    if (!t.owns.some(x => norm(x) === `prs/${t.id}.md`)) probs.push(`${t.id} does not own prs/${t.id}.md`)
    if (t.owns.some(x => /^(scripts|\.claude|harness)\//.test(norm(x)) || ['CLAUDE.md', 'README.md', 'requirements.txt'].includes(norm(x)))) probs.push(`${t.id} owns a harness file`)
    for (const d of t.depends_on) {
      const dt = p.tickets.find(x => x.id === d)
      if (!ids.has(d)) probs.push(`${t.id} depends on unknown ${d}`)
      else if (dt.wave >= t.wave) probs.push(`${t.id} (wave ${t.wave}) depends on ${d} (wave ${dt.wave}); dependencies must be in earlier waves`)
    }
  }
  return probs
}
async function checkedPlan(plan) {
  let probs = planProblems(plan)
  if (!probs.length) return plan
  log(`Plan check found ${probs.length} problem(s); sending back to Supervisor`)
  const fixed = await onMain(() => agent(`${PRE('Supervisor')}

Your plan (commit ${plan.commit}) failed the harness's deterministic plan check:
${probs.map(x => '- ' + x).join('\n')}

Fix the ticket files (and tickets/BACKLOG.md / ADRs if needed) so every problem is resolved, commit as Supervisor ("plan: fix plan check findings"), and return the full corrected plan. ${MODE_NOTE}`, { label: 'supervisor:plan-fix', phase: 'Plan', schema: PLAN_SCHEMA }))
  if (!fixed) throw new Error('Supervisor plan fix failed')
  probs = planProblems(fixed)
  if (probs.length) throw new Error('Plan still fails checks: ' + probs.join('; '))
  return fixed
}

const planPrompt = `${PRE('Supervisor')}

TASK: plan the from-scratch build of the product in docs/product-brief.md. Follow "When planning" in your role file. ${MODE_NOTE}

Constraints you must respect:
- Read docs/adr/0001..0003 (process ADRs) first. Your architecture ADRs start at the next free number.
- requirements.txt is fixed and pre-installed (read it); design within it. Network calls (RDAP, hosting provider) use what is already installed (httpx/requests).
- Frontend: React + TypeScript + Vite + Tailwind in frontend/ (see the brief's quality bar and docs/adr/0005). Decide the exact npm package set (component primitives, icons, charts, test runner) in an ADR. Plan a design-system ticket (tokens, light/dark theme, shared components, app shell with agent-aware chat layout) before feature screens, and make each UI ticket's acceptance criteria include the quality bar (responsive, dark mode, accessible, loading/empty/error states) and Playwright screenshots. Only one ticket per wave may own frontend/package.json and frontend config files.
- Harness files are owned by no ticket: scripts/, harness/, .claude/, CLAUDE.md, README.md, requirements.txt, .gitignore, .gitattributes, docs/adr/0001-0006.
- Ticket files follow tickets/TEMPLATE.md exactly. "## Owns" is machine-parsed by scripts/verify.sh: one bullet per path, each path in backticks, directories end with "/". Every ticket also lists \`evidence/T-NNN/\` and \`prs/T-NNN.md\` (its own id). Tickets in the same wave own disjoint paths (no path may be a prefix of another same-wave ticket's path). Tests live in files the ticket owns (e.g. tests/test_<area>.py); shared test config (conftest.py, pytest config) is owned by the wave 0 ticket only.
- Wave 0 = exactly ONE foundation ticket (T-001): package skeleton, pytest config, shared domain types and constants, the agent message/handoff contract (how the Manager routes to specialists and how each message records which agent spoke), the LLM provider abstraction (DeepSeek/Groq via config + a deterministic fake), interfaces + fakes for external services (RDAP domain lookup, website hosting/deploy), and typed stubs (exact signatures + docstrings, raising NotImplementedError) for every function one ticket calls in another, so every wave-1 ticket can be built and tested independently in parallel.
- Wave 1 must contain AT LEAST ${MIN_PARALLEL} tickets that depend only on T-001 and run fully in parallel (each specialist agent or deterministic engine is a natural ticket). Plan later waves too (Manager orchestration graph wiring, API, UI, end-to-end recorded demo) so the backlog covers the whole brief.
- Each ticket is one PR for one builder session, with concrete acceptance criteria and a concrete description of what evidence/T-NNN/feature_run.py must demonstrate (using fakes, no network).
- Write the ADRs before the tickets and link the relevant ADRs from every ticket. Put contracts (signatures, types, table schemas, state transitions, agent handoff protocol) in ADRs so builders and reviewers share one source of truth.
- Write tickets/BACKLOG.md, tickets/plan.json (shape in your role file) and docs/product-decisions.md. Commit once as Supervisor, message "plan: architecture ADRs and ticket backlog", with the Co-Authored-By trailer from CLAUDE.md.

Return owner_brief, the ADRs you wrote, every ticket (status todo), open_questions (same as in plan.json), and the commit sha.`

// ---------------- Delivery per ticket ----------------
const builderStart = (t, others, merged) => `${PRE('Builder')}

You are Builder ${t.id}. Your ticket: ${t.file} ("${t.title}").
Your owned paths: ${t.owns.join(', ')}.
Builders working IN PARALLEL right now (never touch their paths): ${others}.
Already merged on main: ${merged.length ? merged.join(', ') : 'nothing yet'}.
${ANSWERS[t.id] ? `The human product owner answered an earlier question for this ticket: ${ANSWERS[t.id]}\nYour worktree may already contain earlier work: continue from it.` : ''}
Do the whole job described in your role file: bash scripts/start_ticket.sh ${t.id}; work only in that worktree; implement the ticket to every acceptance criterion and the linked ADRs; pytest tests; evidence/${t.id}/feature_run.py recorded with scripts/record_run.sh; PR record prs/${t.id}.md from prs/TEMPLATE.md; bash scripts/verify.sh ${t.id} must print "VERIFY ${t.id}: PASS"; commit everything as Builder ${t.id} so the worktree is clean.
If you are blocked by something outside your ticket (contract unclear or contradictory, ADR conflict, need a dependency or a file you don't own, or a product decision the ticket doesn't settle), stop and return status BLOCKED with one precise question and what you tried.`

const builderResume = (t, q, decision, commit) => `${PRE('Builder')}

You are Builder ${t.id} (ticket ${t.file}), resuming in your existing worktree (bash scripts/start_ticket.sh ${t.id} prints its path; it reuses it).
You were BLOCKED and asked: ${q}
Decision: ${decision}
${commit ? `ADR/ticket updates were committed on main (${commit}). Run "git merge main" in your worktree to pick them up.` : ''}
Continue the job to completion as your role file describes (verify.sh must PASS, worktree clean), or return BLOCKED again only if truly necessary.`

const builderFix = (t, round, rv) => `${PRE('Builder')}

You are Builder ${t.id} (ticket ${t.file}), in your existing worktree (bash scripts/start_ticket.sh ${t.id} prints the path).
The Reviewer requested changes in round ${round} of at most ${MAX_ROUNDS} (full text in prs/${t.id}.md):
${rv.blocking.map((b, i) => `${i + 1}. ${b.location}: ${b.problem} -> expected: ${b.expected}`).join('\n')}
Follow "When fixing review findings" in your role file. Fix every finding (or answer it under "Builder response" if it is not a defect), re-run tests, re-record, verify.sh must PASS, commit "${t.id}: address review round ${round}". ${round === MAX_ROUNDS - 1 ? 'The next review is the LAST allowed round: be thorough.' : ''}`

const builderGateFix = (t, g) => `${PRE('Builder')}

You are Builder ${t.id} (ticket ${t.file}), in your existing worktree (bash scripts/start_ticket.sh ${t.id} prints the path).
The merge gate (scripts/merge_pr.sh ${t.id}) refused your PR. Exit code ${g ? g.exit_code : '?'}. Output tail:
${g ? g.output_tail : '(gate agent failed)'}
Usually main moved (other tickets merged) and your branch conflicts or breaks tests on the merged code. Run "git merge main" in your worktree, resolve conflicts (code on main in paths you don't own is authoritative; adapt yours), make bash scripts/verify.sh ${t.id} PASS, add a short "Builder response" note in prs/${t.id}.md explaining what changed after approval, and commit. The Reviewer will re-check.`

const reviewerPrompt = (t, round) => `${PRE('Reviewer')}

Review PR ${t.id} ("${t.title}"), round ${round} of at most ${MAX_ROUNDS}. Ticket: ${t.file}. Worktree: .worktrees/${t.id} (branch ticket/${t.id}); run all git/verify commands there.
${round === 1 ? 'This is round 1: report EVERY blocking issue you can find now.' : `Earlier rounds are recorded in prs/${t.id}.md. Per round discipline: check that every earlier blocking finding is fixed, and raise new issues only in code changed since your last round.`}
${round === MAX_ROUNDS ? 'This is the FINAL round. If any blocking issue remains, CHANGES_REQUESTED escalates the ticket to the Supervisor.' : ''}
Append "### Round ${round}" with "Verdict: ..." to the Review section of prs/${t.id}.md, flip any ADR this PR proposes to Accepted if you approve, commit as Reviewer, and return the verdict and findings.`

const gatePrompt = t => `Repository: ${REPO}. Run exactly this one command from the repository root with the Bash tool and nothing else:
bash scripts/merge_pr.sh ${t.id}
Do not edit, fix, retry or commit anything. Return its exit code and the last 40 lines of its output verbatim.`

const build = (t, prompt, ph, kind) => agent(prompt, { label: `builder:${t.id}${kind ? ' ' + kind : ''}`, phase: ph, schema: BUILD_SCHEMA })

// Returns {rep} when resolved or not blocked, or {human: question} when the human must answer.
async function handleBlocked(t, rep, ph, counter) {
  while (rep && rep.status === 'BLOCKED' && counter.n < MAX_UNBLOCKS) {
    counter.n++
    const q = rep.question || rep.summary
    log(`${t.id} BLOCKED: ${q.slice(0, 160)}`)
    const ans = await onMain(() => agent(`${PRE('Supervisor')}

Builder ${t.id} (ticket ${t.file}) is BLOCKED and asks:
${q}
Builder's context: ${rep.summary}
Follow "When unblocking" in your role file. ${MODE === 'human'
  ? 'SUPERVISOR_MODE=human: if this is a question about WHAT the product should do (a product/business choice the brief and ADRs do not settle), do NOT decide: set needs_human=true, write question_for_human in plain language with 2-4 options and your recommendation (ADR-0006), add it to open_questions in tickets/plan.json with this ticket id, and commit. Technical questions you decide yourself.'
  : 'SUPERVISOR_MODE=auto: decide everything yourself; needs_human is always false.'}
Write/commit an ADR or ticket update on main only if needed (docs/ and tickets/ only; never code).`, { label: `supervisor:unblock ${t.id}`, phase: ph, schema: UNBLOCK_SCHEMA }))
    if (!ans) return { rep }
    if (ans.needs_human && MODE === 'human') return { rep, human: ans.question_for_human || { id: '', ticket: t.id, question: q, why_it_matters: '', options: [], recommended: '' } }
    rep = await build(t, builderResume(t, q, ans.decision, ans.commit), ph, 'resume')
  }
  return { rep }
}

async function escalate(t, rv, ph) {
  return onMain(() => agent(`${PRE('Supervisor')}

Ticket ${t.id} (${t.file}) failed review after ${MAX_ROUNDS} rounds. Remaining blocking findings:
${(rv ? rv.blocking : []).map((b, i) => `${i + 1}. ${b.location}: ${b.problem}`).join('\n')}
Follow "When escalated" in your role file (read prs/${t.id}.md in .worktrees/${t.id}). Re-scope, split or re-plan in tickets/ and tickets/BACKLOG.md, commit as Supervisor. Do not write code. Return a one-paragraph decision.`, { label: `supervisor:escalation ${t.id}`, phase: ph }))
}

async function deliver(t, waveTickets, ph, merged) {
  const others = waveTickets.filter(o => o.id !== t.id).map(o => `${o.id} owns ${o.owns.filter(x => !shared(x)).join(', ')}`).join('; ') || 'none'
  const counter = { n: 0 }
  const done = (outcome, extra) => ({ id: t.id, title: t.title, wave: t.wave, outcome, unblocks: counter.n, ...extra })
  const settle = async (p, rounds) => {
    const r = await handleBlocked(t, await p, ph, counter)
    if (r.human) return { stop: done('needs_human', { rounds, question: r.human }) }
    if (!r.rep) return { stop: done('builder_failed', { rounds }) }
    if (r.rep.status === 'BLOCKED') return { stop: done('blocked', { rounds, question: r.rep.question }) }
    return { rep: r.rep }
  }

  let s = await settle(build(t, builderStart(t, others, merged), ph, ''), 0)
  if (s.stop) return s.stop

  let rounds = 0, approved = false, gateAttempts = 0, lastReview = null
  while (true) {
    if (!approved) {
      if (rounds >= MAX_ROUNDS) { const d = await escalate(t, lastReview, ph); return done('escalated', { rounds, supervisor: d }) }
      rounds++
      lastReview = await agent(reviewerPrompt(t, rounds), { label: `review:${t.id} r${rounds}`, phase: ph, schema: REVIEW_SCHEMA })
      if (!lastReview) return done('reviewer_failed', { rounds })
      log(`${t.id} review round ${rounds}: ${lastReview.verdict}${lastReview.blocking.length ? ` (${lastReview.blocking.length} blocking)` : ''}`)
      if (lastReview.verdict !== 'APPROVED') {
        if (rounds >= MAX_ROUNDS) { const d = await escalate(t, lastReview, ph); return done('escalated', { rounds, supervisor: d }) }
        s = await settle(build(t, builderFix(t, rounds, lastReview), ph, `fix r${rounds}`), rounds)
        if (s.stop) return s.stop
        continue
      }
      approved = true
    }
    gateAttempts++
    const g = await onMain(() => agent(gatePrompt(t), { label: `gate:${t.id}`, phase: ph, schema: GATE_SCHEMA, effort: 'low' }))
    if (g && g.exit_code === 0) { log(`${t.id} MERGED after ${rounds} review round(s)`); return done('merged', { rounds, gate_attempts: gateAttempts }) }
    log(`${t.id} gate refused (exit ${g ? g.exit_code : '?'})`)
    if (gateAttempts >= MAX_GATE_ATTEMPTS) return done('gate_failed', { rounds, gate_tail: g && g.output_tail })
    s = await settle(build(t, builderGateFix(t, g), ph, 'gate-fix'), rounds)
    if (s.stop) return s.stop
    approved = false // code changed after approval: re-review (counts toward the 3 rounds)
  }
}

// ---------------- Stages ----------------
const qText = q => (q && typeof q === 'object') ? q.question : q

// ask: the owner asks the Supervisor anything; read-only.
if (STAGE === 'ask') {
  phase('Plan')
  const a = await agent(`${PRE('Supervisor')}

The product owner asks you: ${args.feedback}

Follow "When asked a question" in your role file: answer directly in plain language from the plan (tickets/plan.json, tickets/, docs/adr/, docs/product-decisions.md) and the repo state (git log, prs/, evidence/). Change NOTHING and commit nothing. If the question implies the plan should change, put the revise feedback you'd suggest in suggested_change.`, { label: 'supervisor:ask', phase: 'Plan', schema: ASK_SCHEMA })
  return { stage: STAGE, mode: MODE, question: args.feedback, ...a }
}

let plan = null
if (STAGE === 'plan' || STAGE === 'revise') {
  phase('Plan')
  if (STAGE === 'plan') {
    plan = await onMain(() => agent(planPrompt, { label: 'supervisor:plan', phase: 'Plan', schema: PLAN_SCHEMA }))
  } else {
    const answered = Object.entries(args.question_answers || {})
    plan = await onMain(() => agent(`${PRE('Supervisor')}

The product owner reviewed your plan.
${answered.length ? `Answers to your open questions:\n${answered.map(([id, a]) => `- ${id}: ${a}`).join('\n')}\n` : ''}${args.feedback ? `Requested changes, in their words:\n${args.feedback}\n` : ''}
Apply them: log each decision in docs/product-decisions.md and mark answered questions in tickets/plan.json; revise ADRs (supersede accepted ADRs with new ones rather than editing them, per ADR-0001), tickets, BACKLOG.md and plan.json accordingly, keeping every planning constraint (wave 0 = one foundation ticket, wave 1 >= ${MIN_PARALLEL} parallel tickets with disjoint Owns). Commit as Supervisor ("plan: revise per product owner feedback"). In owner_brief, say briefly what you changed. Return the full current plan with only the questions still open. ${MODE_NOTE}`, { label: 'supervisor:revise', phase: 'Plan', schema: PLAN_SCHEMA }))
  }
  if (!plan) throw new Error('Supervisor planning failed')
  plan = await checkedPlan(plan)
  log(`Plan: ${plan.adrs.length} ADRs, ${plan.tickets.length} tickets; wave 1 has ${plan.tickets.filter(t => t.wave === 1).length} parallel tickets; ${plan.open_questions.length} open question(s)`)
  if (MODE === 'human') {
    return { stage: STAGE, mode: MODE, awaiting: 'product owner approval', owner_brief: plan.owner_brief, adrs: plan.adrs, tickets: plan.tickets, open_questions: plan.open_questions, commit: plan.commit }
  }
}

if (!plan) {
  phase('Plan')
  plan = await agent(`${PRE('Supervisor')}
Read-only task: read tickets/plan.json (and tickets/BACKLOG.md if they disagree, plan.json wins) and return the current plan exactly as written (ids, titles, waves, depends_on, ticket file paths, owned paths, statuses, still-open questions, owner_brief). Do not change or commit anything. commit: current main HEAD sha.`, { label: 'supervisor:read-plan', phase: 'Plan', schema: PLAN_SCHEMA, effort: 'low' })
  if (!plan) throw new Error('Could not read the plan')
  const probs = planProblems(plan)
  if (probs.length) throw new Error('Plan on main fails checks: ' + probs.join('; '))
}

const results = []
const mergedBefore = plan.tickets.filter(t => t.status === 'merged').map(t => t.id)
for (const w of WAVES) {
  const ts = plan.tickets.filter(t => t.wave === w && t.status !== 'merged')
  if (!ts.length) continue
  const ph = `Wave ${w}`
  phase(ph)
  const merged = mergedBefore.concat(results.filter(r => r.outcome === 'merged').map(r => r.id))
  const ready = ts.filter(t => t.depends_on.every(d => merged.includes(d)))
  ts.filter(t => !ready.includes(t)).forEach(t => results.push({ id: t.id, title: t.title, wave: w, outcome: 'skipped_dependency_not_merged' }))
  log(`${ph}: launching ${ready.length} builder(s) in parallel: ${ready.map(t => t.id).join(', ')}`)
  const rs = await parallel(ready.map(t => () => deliver(t, ready, ph, merged)))
  rs.forEach((r, i) => results.push(r || { id: ready[i].id, title: ready[i].title, wave: w, outcome: 'error' }))
  if (w === 0 && !results.some(r => r.id === ready[0]?.id && r.outcome === 'merged') && ready.length) { log('Wave 0 foundation did not merge; stopping'); break }
}

phase('Close')
const closing = await onMain(() => agent(`${PRE('Supervisor')}

Delivery run finished (waves ${WAVES.join(',')}, mode ${MODE}). Outcomes per ticket:
${results.map(r => `- ${r.id} ${r.title}: ${r.outcome}${r.rounds != null ? `, ${r.rounds} review round(s)` : ''}${r.unblocks ? `, ${r.unblocks} unblock(s)` : ''}${r.question ? ` — waiting on: ${qText(r.question)}` : ''}`).join('\n')}
Update tickets/BACKLOG.md and tickets/plan.json statuses (merged / escalated / blocked / needs_human / todo) and each executed ticket file's Status row, make sure docs/adr/README.md and plan.json list every ADR now on main (including ones builders proposed and reviewers accepted), and note what the next wave is. Rewrite owner_brief in plan.json for the owner: what they can now see or use, what is waiting on them, what comes next. Commit as Supervisor ("plan: close delivery run"). Docs/tickets only. Return that owner brief as your answer.`, { label: 'supervisor:close', phase: 'Close' }))

return { stage: STAGE, mode: MODE, results, needs_human: results.filter(r => r.outcome === 'needs_human').map(r => ({ id: r.id, question: r.question })), owner_brief: closing }
