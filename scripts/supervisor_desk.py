"""Render the Supervisor Desk (ADR-0006): harness/desk.html, a self-contained status page.

    bash scripts/py.sh scripts/supervisor_desk.py

Reads tickets/plan.json (written by the Supervisor) and the live git state (branches,
merge commits, PR records, recorded runs, screenshots) and writes one HTML file.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


ROOT = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")).parent
OUT = ROOT / "harness" / "desk.html"
e = html.escape


def setting(name: str, default: str) -> str:
    env = ROOT / "harness" / "harness.env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip() or default
    return default


def ref_exists(ref: str) -> bool:
    return bool(git("rev-parse", "--verify", "--quiet", ref))


def show(ref: str, path: str) -> str:
    return git("show", f"{ref}:{path}")


def ticket_state(t: dict) -> dict:
    tid = t["id"]
    branch = f"ticket/{tid}"
    merge = git("log", "main", "--merges", "--first-parent", f"--grep=^Merge PR {tid}:", "--format=%h|%cs", "-1")
    ref = "main" if merge else (branch if ref_exists(branch) else None)
    st = {"merged": bool(merge), "merge": merge.split("|") if merge else None, "branch": ref_exists(branch),
          "rounds": 0, "verdict": None, "run_exit": None, "shots": []}
    if ref:
        pr = show(ref, f"prs/{tid}.md")
        st["rounds"] = len(re.findall(r"^### Round \d+", pr, re.M))
        verdicts = re.findall(r"^Verdict:\s*(\S+)", pr, re.M)
        st["verdict"] = verdicts[-1] if verdicts else None
        m = re.search(r"^exit_code:\s*(\d+)", show(ref, f"evidence/{tid}/run.log"), re.M)
        st["run_exit"] = int(m.group(1)) if m else None
        base = ROOT if ref == "main" else ROOT / ".worktrees" / tid
        for name in git("ls-tree", "--name-only", ref, f"evidence/{tid}/").splitlines():
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                p = base / name
                st["shots"].append(p.as_uri() if p.exists() else None)
        st["shots"] = [s for s in st["shots"] if s]
    if st["merged"]:
        st["status"] = "merged"
    elif t.get("status") in {"escalated", "blocked", "needs_human"}:
        st["status"] = t["status"]
    elif st["rounds"]:
        st["status"] = "in review"
    elif st["branch"]:
        st["status"] = "building"
    else:
        st["status"] = t.get("status") or "todo"
    return st


def adrs() -> list[dict]:
    out = []
    for f in sorted((ROOT / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")):
        if f.name.startswith("0000"):
            continue
        text = f.read_text(encoding="utf-8")
        title = re.sub(r"^#\s*ADR-\d+:\s*", "", text.splitlines()[0]) if text else f.stem
        m = re.search(r"\*\*Status\*\*\s*\|\s*([^|\n]+)", text)
        out.append({"num": f.name[:4], "title": title, "status": (m.group(1).strip() if m else "?"), "uri": f.as_uri()})
    return out


def activity() -> list[list[str]]:
    rows = git("log", "--all", "-14", "--format=%an|%ar|%s").splitlines()
    return [r.split("|", 2) for r in rows if r.count("|") >= 2]


def paras(text: str) -> str:
    return "".join(f"<p>{e(p.strip())}</p>" for p in re.split(r"\n\s*\n", text or "") if p.strip())


REC_TAG = ' <span class="tag">recommended</span>'
ROLE_CLASS = {"Supervisor": "sup", "Reviewer": "rev", "Gate": "gate"}
STATUS_LABEL = {"needs_human": "needs you", "escalated": "escalated to Supervisor", "todo": "not started"}
STATUS_CLASS = {"merged": "ok", "in review": "info", "building": "info", "needs_human": "warn",
                "blocked": "warn", "escalated": "bad", "todo": "muted"}


def render(plan: dict | None) -> str:
    mode = setting("SUPERVISOR_MODE", "human")
    now = datetime.now().strftime("%b %d, %Y %H:%M")
    mode_class = "info" if mode == "human" else "ok"
    if not plan:
        body = '<section class="card empty"><h2>No plan yet</h2><p>Run the planning stage: the Supervisor writes <code>tickets/plan.json</code>, and this desk fills in.</p></section>'
        return PAGE.format(title="Supervisor Desk", product="Supervisor Desk", mode=e(mode), mode_class=mode_class, now=now, body=body)

    tickets = plan.get("tickets", [])
    states = {t["id"]: ticket_state(t) for t in tickets}
    open_q = [q for q in plan.get("open_questions", []) if q.get("status", "open") == "open"]
    needs = [t for t in tickets if states[t["id"]]["status"] in {"needs_human", "blocked", "escalated"}]
    merged = sum(s["merged"] for s in states.values())
    in_flight = sum(s["status"] in {"building", "in review"} for s in states.values())
    adr_list = adrs()

    stats = f"""
    <section class="stats">
      <div class="stat"><span class="n">{merged}<small>/{len(tickets)}</small></span><span class="l">tickets merged</span>
        <div class="bar"><i style="width:{(100 * merged // max(len(tickets), 1))}%"></i></div></div>
      <div class="stat"><span class="n">{in_flight}</span><span class="l">being built or reviewed</span></div>
      <div class="stat {'attn' if open_q or needs else ''}"><span class="n">{len(open_q) + len(needs)}</span><span class="l">waiting on you</span></div>
      <div class="stat"><span class="n">{len(adr_list)}</span><span class="l">decisions recorded (ADRs)</span></div>
    </section>"""

    brief = f'<section class="card brief"><h2>From the Supervisor</h2>{paras(plan.get("owner_brief", ""))}</section>'

    qhtml = ""
    if open_q or needs:
        cards = []
        for q in open_q:
            def opt(o: dict, q: dict = q) -> str:
                rec = o.get("label") == q.get("recommended")
                return (f'<li class="{"rec" if rec else ""}"><b>{e(o.get("label", ""))}{REC_TAG if rec else ""}</b>'
                        f'<span>{e(o.get("description", ""))}</span></li>')
            opts = "".join(opt(o) for o in q.get("options", []))
            tk = f'<span class="chip">{e(q["ticket"])}</span>' if q.get("ticket") else ""
            cards.append(f'<article class="q"><header><span class="qid">{e(q.get("id", ""))}</span>{tk}</header>'
                         f'<h3>{e(q.get("question", ""))}</h3><p class="why">{e(q.get("why_it_matters", ""))}</p><ul>{opts}</ul></article>')
        for t in needs:
            cards.append(f'<article class="q"><header><span class="qid">{e(t["id"])}</span><span class="pill warn">{e(STATUS_LABEL.get(states[t["id"]]["status"], states[t["id"]]["status"]))}</span></header>'
                         f'<h3>{e(t["title"])}</h3><p class="why">This ticket is paused until you or the Supervisor decide how to continue.</p></article>')
        qhtml = f'<section><h2 class="sec">Needs your decision</h2><p class="hint">Answer in the chat: pick an option or say what you want instead.</p><div class="qgrid">{"".join(cards)}</div></section>'

    goals = {w.get("wave"): w.get("goal", "") for w in plan.get("waves", [])}
    waves_html = []
    for w in sorted({t["wave"] for t in tickets}):
        cards = []
        for t in [t for t in tickets if t["wave"] == w]:
            s = states[t["id"]]
            dots = "".join(f'<i class="{"on" if i < s["rounds"] else ""}"></i>' for i in range(3))
            checks = []
            if s["verdict"]:
                checks.append(f'<span class="ck {"ok" if s["verdict"] == "APPROVED" else "warn"}">review: {e(s["verdict"].replace("_", " ").lower())}</span>')
            if s["run_exit"] is not None:
                checks.append(f'<span class="ck {"ok" if s["run_exit"] == 0 else "bad"}">recorded run: {"pass" if s["run_exit"] == 0 else "fail"}</span>')
            if s["merge"]:
                checks.append(f'<span class="ck ok">merged {e(s["merge"][1])} · {e(s["merge"][0])}</span>')
            shots = "".join(f'<a href="{e(u)}" target="_blank"><img src="{e(u)}" alt="screenshot for {e(t["id"])}" loading="lazy"></a>' for u in s["shots"][:4])
            deps = f'<span class="deps">after {", ".join(map(e, t.get("depends_on", [])))}</span>' if t.get("depends_on") else ""
            cards.append(f"""<article class="ticket">
              <header><span class="tid">{e(t['id'])}</span><span class="pill {STATUS_CLASS.get(s['status'], 'muted')}">{e(STATUS_LABEL.get(s['status'], s['status']))}</span></header>
              <h3>{e(t['title'])}</h3><p>{e(t.get('summary_for_owner', ''))}</p>
              <footer><span class="rounds" title="review rounds used (max 3)">{dots}</span>{deps}</footer>
              {f'<div class="checks">{"".join(checks)}</div>' if checks else ''}
              {f'<div class="shots">{shots}</div>' if shots else ''}
            </article>""")
        waves_html.append(f'<section class="wave"><h2 class="sec">Wave {w}<span>{e(goals.get(w, ""))}</span></h2><div class="tgrid">{"".join(cards)}</div></section>')

    def adr_badge(status: str) -> tuple[str, str]:
        short = status.split("(")[0].strip() or status
        if "superseded" in status.lower() and short.lower().startswith("accepted"):
            short = "Partly superseded"
        return short, "ok" if short.startswith("Accepted") else "muted"
    adr_rows = "".join(f'<li title="{e(a["status"])}"><a href="{e(a["uri"])}"><span class="num">ADR-{e(a["num"])}</span>{e(a["title"])}</a>'
                       f'<span class="pill {adr_badge(a["status"])[1]}">{e(adr_badge(a["status"])[0])}</span></li>' for a in adr_list)
    act_rows = "".join(f'<li><span class="who {ROLE_CLASS.get(r[0].split()[0], "bld" if r[0].startswith("Builder") else "op")}">{e(r[0])}</span><span class="what">{e(r[2])}</span><span class="when">{e(r[1])}</span></li>' for r in activity())
    side = f'<aside><section class="card"><h2>Decisions (ADRs)</h2><ul class="adrs">{adr_rows}</ul></section><section class="card"><h2>Recent activity</h2><ul class="act">{act_rows}</ul></section></aside>'

    body = f'{stats}<div class="layout"><main>{brief}{qhtml}{"".join(waves_html)}</main>{side}</div>'
    return PAGE.format(title="Supervisor Desk", product=e(plan.get("product", "Supervisor Desk")), mode=e(mode), mode_class=mode_class, now=now, body=body)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#14171f;--sub:#5b6472;--line:#e3e6eb;--accent:#4f46e5;--accent-soft:#eef0ff;
--ok:#0f8a5f;--ok-soft:#e3f5ee;--info:#2563eb;--info-soft:#e7efff;--warn:#b45309;--warn-soft:#fdf1e2;--bad:#c0262d;--bad-soft:#fde8e8;--muted:#6b7280;--muted-soft:#f0f1f3;
--r:14px;--sh:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(16,24,40,.06)}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1016;--card:#151a23;--ink:#e8ebf1;--sub:#9aa3b2;--line:#252c38;--accent:#8b85ff;--accent-soft:#1f2140;
--ok:#3ccf91;--ok-soft:#10291f;--info:#6ea2ff;--info-soft:#132140;--warn:#f0a542;--warn-soft:#2c1f0d;--bad:#ff6b70;--bad-soft:#2e1214;--muted:#9aa3b2;--muted-soft:#1c222c;--sh:none}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
a{{color:inherit}}.top{{position:sticky;top:0;z-index:2;background:color-mix(in srgb,var(--bg) 85%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
.top .in{{max-width:1240px;margin:auto;padding:14px 20px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.logo{{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--accent),#22c1c3);display:grid;place-items:center;color:#fff;font-weight:700}}
.top h1{{font-size:17px;margin:0}}.top .sub{{color:var(--sub);font-size:13px}}.top .right{{margin-left:auto;display:flex;gap:8px;align-items:center;color:var(--sub);font-size:13px}}
.wrap{{max-width:1240px;margin:auto;padding:20px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh)}}
.stat .n{{display:block;font-size:28px;font-weight:700;letter-spacing:-.02em}}.stat small{{font-size:15px;color:var(--sub);font-weight:500}}.stat .l{{color:var(--sub);font-size:13px}}
.stat.attn{{border-color:var(--warn);background:var(--warn-soft)}}.bar{{height:6px;background:var(--muted-soft);border-radius:9px;margin-top:8px;overflow:hidden}}.bar i{{display:block;height:100%;background:var(--ok);border-radius:9px}}
.layout{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,360px);gap:18px;align-items:start}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;box-shadow:var(--sh);margin-bottom:18px}}
.card h2,.sec{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--sub);margin:0 0 10px}}
.sec{{margin:22px 0 10px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}.sec span{{text-transform:none;letter-spacing:0;font-size:14px;color:var(--ink);font-weight:500}}
.brief{{border-left:4px solid var(--accent)}}.brief p{{margin:.4em 0}}.hint{{color:var(--sub);margin:-4px 0 10px;font-size:13px}}
.qgrid,.tgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}}
.q,.ticket{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px;box-shadow:var(--sh);display:flex;flex-direction:column;gap:6px}}
.q{{border-color:color-mix(in srgb,var(--warn) 45%,var(--line))}}.q h3,.ticket h3{{font-size:15px;margin:0;line-height:1.35}}.q .why,.ticket p{{margin:0;color:var(--sub);font-size:13.5px}}
.q ul{{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:6px}}.q li{{border:1px solid var(--line);border-radius:10px;padding:8px 10px;display:flex;flex-direction:column;font-size:13.5px}}
.q li span{{color:var(--sub)}}.q li.rec{{border-color:var(--accent);background:var(--accent-soft)}}.tag{{display:inline-block;font-size:11px;font-weight:600;color:var(--accent);margin-left:6px}}
header{{display:flex;justify-content:space-between;align-items:center;gap:8px}}.tid,.qid{{font:600 12px ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--sub)}}
.chip{{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;color:var(--sub)}}
.pill{{font-size:12px;font-weight:600;border-radius:99px;padding:2px 9px;white-space:nowrap}}
.ok{{color:var(--ok);background:var(--ok-soft)}}.info{{color:var(--info);background:var(--info-soft)}}.warn{{color:var(--warn);background:var(--warn-soft)}}.bad{{color:var(--bad);background:var(--bad-soft)}}.muted{{color:var(--muted);background:var(--muted-soft)}}
footer{{display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:4px}}.rounds{{display:flex;gap:4px}}.rounds i{{width:8px;height:8px;border-radius:50%;background:var(--muted-soft);border:1px solid var(--line)}}.rounds i.on{{background:var(--accent);border-color:var(--accent)}}
.deps{{font-size:12px;color:var(--sub)}}.checks{{display:flex;flex-wrap:wrap;gap:6px}}.ck{{font-size:12px;border-radius:8px;padding:2px 8px}}
.shots{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}.shots img{{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:8px;border:1px solid var(--line)}}
.adrs,.act{{list-style:none;margin:0;padding:0;display:grid;gap:2px}}.adrs li{{display:flex;justify-content:space-between;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid var(--line);font-size:13.5px}}
.adrs a{{text-decoration:none;flex:1;min-width:0}}.adrs .pill{{flex:none;max-width:150px;overflow:hidden;text-overflow:ellipsis}}.adrs a:hover{{color:var(--accent)}}.num{{font:600 12px ui-monospace,Consolas,monospace;color:var(--sub);margin-right:8px}}
.act li{{display:grid;grid-template-columns:auto 1fr;gap:2px 8px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13px}}.act .what{{grid-column:1/-1;color:var(--ink)}}.act .when{{grid-row:1;grid-column:2;color:var(--sub);text-align:right}}
.who{{font-size:12px;font-weight:600;border-radius:6px;padding:1px 7px;width:max-content}}.who.sup{{color:var(--accent);background:var(--accent-soft)}}.who.rev{{color:var(--warn);background:var(--warn-soft)}}.who.gate{{color:var(--ok);background:var(--ok-soft)}}.who.bld{{color:var(--info);background:var(--info-soft)}}.who.op{{color:var(--muted);background:var(--muted-soft)}}
.empty{{text-align:center;padding:48px}}code{{font:13px ui-monospace,Consolas,monospace;background:var(--muted-soft);padding:1px 5px;border-radius:5px}}
:focus-visible{{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}}
@media (max-width:980px){{.layout{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
@media (max-width:520px){{.wrap{{padding:14px 16px}}.stats{{grid-template-columns:1fr 1fr}}.stat .n{{font-size:22px}}}}
</style></head><body>
<div class="top"><div class="in"><div class="logo">S</div><div><h1>{product}</h1><div class="sub">Supervisor Desk</div></div>
<div class="right"><span class="pill {mode_class}">mode: {mode}</span><span>updated {now}</span></div></div></div>
<div class="wrap">{body}</div></body></html>"""


def main() -> int:
    plan_file = ROOT / "tickets" / "plan.json"
    plan = None
    if plan_file.exists():
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"tickets/plan.json is not valid JSON: {exc}", file=sys.stderr)
            return 1
    page = render(plan)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(OUT.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
