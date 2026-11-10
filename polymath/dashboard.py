"""Живой веб-дашборд оркестрации: stdlib-only, SSE, ноль зависимостей.

Запуск: ``polymath dashboard`` (или ``python -m polymath.dashboard``),
затем открыть http://127.0.0.1:8765. Демо-экипаж живёт в фоне: циклы
оркестрации идут бесконечно, события агентом-за-агентом прилетают
в браузер по Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Full, Queue

from .agent import Agent
from .automaton import AutomatonPid1
from .crews import demo_agents, pid1_demo_specs
from .orchestrator import PolymathOrchestrator
from .supervisor import LIMITS, AuditViolation, audit

DEMO_TASKS = (
    "построить уникальный проект",
    "объять необъятное за вечер",
    "выковать флагман из чистого stdlib",
    "подружить четырёх гениев за одним столом",
    "проверить, что одно другое не исключает",
)

CYCLE_PAUSE_SECONDS = 3.0


class EventBus:
    """Fan-out шина: оркестратор публикует, SSE-подписчики читают."""

    def __init__(self) -> None:
        self._subscribers: set[Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> Queue:
        queue: Queue = Queue(maxsize=512)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: Queue) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except Full:  # очередь подписчика переполнена — пропускаем
                continue


def _live(bus: EventBus, agent: Agent) -> Agent:
    """Обёртка агента: публикует started/finished вокруг настоящей работы."""

    async def act(task: str) -> list[str]:
        bus.publish({"type": "agent_started", "agent": agent.name, "skill": agent.skill})
        findings = list(await agent.act(task))
        bus.publish(
            {
                "type": "agent_finished",
                "agent": agent.name,
                "skill": agent.skill,
                "findings": findings,
            }
        )
        return findings

    return Agent(name=agent.name, skill=agent.skill, act=act)


async def orchestration_cycle(bus: EventBus, cycle: int, task: str) -> None:
    """Один цикл: run_started → agent_started/finished → synthesis → verdict."""
    crew = demo_agents()
    bus.publish(
        {
            "type": "run_started",
            "cycle": cycle,
            "task": task,
            "agents": [{"name": a.name, "skill": a.skill} for a in crew],
        }
    )
    live_crew = [_live(bus, agent) for agent in crew]
    orchestrator = PolymathOrchestrator(live_crew)
    synthesis = await orchestrator.solve(task)
    bus.publish(
        {
            "type": "synthesis",
            "task": synthesis.task,
            "agents": synthesis.agents_count,
            "parallel_seconds": round(synthesis.seconds, 2),
            "sequential_seconds": round(sum(r.seconds for r in synthesis.reports), 2),
            "findings": list(synthesis.findings),
            "motto": PolymathOrchestrator.motto,
        }
    )
    try:
        verdicts = audit(synthesis)
    except AuditViolation as exc:  # инвариант нарушен — браузер узнает красным
        bus.publish({"type": "violation", "cycle": cycle, "message": str(exc)})
    else:
        bus.publish(
            {
                "type": "verdict",
                "cycle": cycle,
                "verdicts": verdicts,
                "limits": list(LIMITS),
                "motto": PolymathOrchestrator.motto,
            }
        )


async def pid1_cycle(
    bus: EventBus,
    cycle: int,
    task: str,
    specs: list | None = None,
) -> None:
    """Цикл ПИД1 под автоматом: слово символов летит в браузер, карантин — красным.

    Каждый новый вызов — новый экипаж (:func:`pid1_demo_specs` выдаёт свежий):
    Кузнец снова бракует два удара, ПИД1 снова учит. Отклонённое слово
    не убивает цикл — машина просит новый мандат прямо в браузере.
    """

    def sink(event: dict) -> None:
        payload = dict(event)
        payload["cycle"] = cycle
        bus.publish(payload)

    crew = pid1_demo_specs() if specs is None else specs
    pid1 = AutomatonPid1(crew, on_event=sink)
    report = await pid1.drive(task)
    bus.publish(
        {
            "type": "automaton_verdict",
            "cycle": cycle,
            "accepted": report.accepted,
            "final_state": report.final_state,
            "steps": report.steps,
            "quarantined": list(report.quarantined),
            "attempts": report.attempts,
            "completions": report.completions,
            "restarts": report.restarts,
        }
    )


async def _orchestrate_forever(bus: EventBus, stop: threading.Event) -> None:
    cycle = 0
    while not stop.is_set():
        task = DEMO_TASKS[cycle % len(DEMO_TASKS)]
        try:
            if cycle % 2 == 0:
                await orchestration_cycle(bus, cycle, task)
            else:  # нечётные циклы — экипаж под ПИД1 и автоматом
                await pid1_cycle(bus, cycle, task)
        except Exception as exc:  # noqa: BLE001 — цикл не должен умирать
            bus.publish({"type": "error", "message": repr(exc)})
        cycle += 1
        for _ in range(int(CYCLE_PAUSE_SECONDS * 10)):
            if stop.is_set():
                return
            await asyncio.sleep(0.1)


PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>ПОЛИМАТ = МУЛЬТИАГЕНТ — живая оркестрация</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --bg:#0b0912; --panel:#151221; --line:#2a2340; --gold:#d9a441; --ember:#ff7a45; --text:#efe9dd; --dim:#8f86a8; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:"Segoe UI",system-ui,sans-serif; padding:24px; }
  header h1 { font-size:26px; letter-spacing:.06em; color:var(--gold); }
  header .motto { color:var(--dim); margin-top:4px; font-style:italic; }
  #task { margin:14px 0 18px; font-size:15px; }
  #task b { color:var(--ember); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; min-height:150px; }
  .card h3 { font-size:15px; display:flex; align-items:center; gap:8px; }
  .chip { font-size:11px; color:var(--gold); border:1px solid var(--gold); border-radius:20px; padding:1px 8px; }
  .dot { width:9px; height:9px; border-radius:50%; background:#4a4364; flex:none; }
  .run .dot { background:var(--ember); animation:pulse .8s infinite alternate; }
  .done .dot { background:#7ec96f; }
  @keyframes pulse { from { transform:scale(.8); opacity:.6; } to { transform:scale(1.3); opacity:1; } }
  .time { color:var(--dim); font-size:12px; margin:6px 0; min-height:15px; }
  ul { list-style:none; font-size:13px; line-height:1.45; color:#cfc7e2; }
  li::before { content:"+ "; color:var(--gold); }
  .synth { margin-top:16px; background:linear-gradient(135deg,#1a1530,#151221); border:1px solid var(--gold); border-radius:10px; padding:14px; }
  .stats { display:flex; flex-wrap:wrap; gap:22px; margin:10px 0; }
  .stat b { display:block; font-size:24px; color:var(--gold); }
  .stat span { font-size:12px; color:var(--dim); }
  #log { margin-top:16px; background:#08070e; border:1px solid var(--line); border-radius:10px; padding:12px; font-family:ui-monospace,Consolas,monospace; font-size:12px; color:var(--dim); height:150px; overflow:auto; }
  #log .g { color:var(--gold); } #log .e { color:var(--ember); }
  .verdict { margin-top:12px; border:1px solid var(--line); border-radius:8px; padding:10px 12px; font-size:13px; color:var(--dim); white-space:pre-line; }
  .verdict b { color:inherit; }
  .verdict.ok { border-color:#7ec96f; color:#a5e79a; background:rgba(126,201,111,.08); }
  .verdict.bad { border-color:var(--ember); color:var(--ember); background:rgba(255,122,69,.08); animation:pulse 1s infinite alternate; }
  .card.quarantine { border-color:#ff4545; background:rgba(255,69,69,.10); }
  .card.quarantine .dot { background:#ff4545; animation:pulse .6s infinite alternate; }
  .card.quarantine .time { color:#ff8a8a; }
</style>
</head>
<body>
<header>
  <h1>🧠 ПОЛИМАТ = МУЛЬТИАГЕНТ</h1>
  <div class="motto">«Одно другое не исключает.» — живая оркестрация, stdlib-only, SSE</div>
</header>
<div id="task">Задача: <b>ждём первый цикл оркестрации…</b></div>
<div class="grid" id="crew"></div>
<div class="synth">
  <b style="color:var(--gold)">СИНТЕЗ</b>
  <div class="stats">
    <div class="stat"><b id="s-agents">—</b><span>агентов</span></div>
    <div class="stat"><b id="s-par">—</b><span>параллельно, с</span></div>
    <div class="stat"><b id="s-seq">—</b><span>было бы, с</span></div>
    <div class="stat"><b id="s-save">—</b><span>экономия, с</span></div>
  </div>
  <ul id="s-findings"></ul>
  <div id="verdict" class="verdict">👀 Надзиратель ждёт первого прогона… 🤖 автомат ведёт нечётные циклы сам</div>
</div>
<div id="log"></div>
<script>
const crew = {};
const grid = document.getElementById('crew');
const log = document.getElementById('log');
const stamp = () => new Date().toLocaleTimeString('ru-RU');
function logLine(type, text) {
  const gold = ['synthesis', 'verdict', 'automaton_verdict', 'house_cleaned'].includes(type);
  const red = ['error', 'violation', 'pid1_quarantined', 'pid1_child_down'].includes(type);
  const cls = gold ? 'g' : (red ? 'e' : '');
  const div = document.createElement('div');
  div.innerHTML = `<span class="${cls}">[${stamp()}] ${type}</span> ${text}`;
  log.prepend(div);
  while (log.childNodes.length > 60) log.lastChild.remove();
}
function ensureCard(agent) {
  if (crew[agent.skill]) return crew[agent.skill];
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `<h3><span class="dot"></span>${agent.name} <span class="chip">${agent.skill}</span></h3>
    <div class="time"></div><ul></ul>`;
  grid.appendChild(card);
  crew[agent.skill] = { el: card, ul: card.querySelector('ul'), time: card.querySelector('.time') };
  return crew[agent.skill];
}
const es = new EventSource('/events');
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.type === 'run_started') {
    document.getElementById('task').innerHTML = `Задача: <b>${ev.task}</b> · цикл #${ev.cycle}`;
    ev.agents.forEach(a => {
      const c = ensureCard(a);
      c.el.className = 'card';
      c.ul.innerHTML = ''; c.time.textContent = 'работает…';
    });
    logLine(ev.type, `экипаж из ${ev.agents.length} агентов стартовал параллельно`);
  }
  if (ev.type === 'agent_started') {
    const c = ensureCard(ev);
    c.el.className = 'card run';
    logLine(ev.type, `${ev.agent} (${ev.skill}) работает`);
  }
  if (ev.type === 'agent_finished') {
    const c = ensureCard(ev);
    c.el.className = 'card done';
    c.ul.innerHTML = ev.findings.map(f => `<li>${f}</li>`).join('');
    logLine(ev.type, `${ev.agent} завершил: ${ev.findings.length} находок`);
  }
  if (ev.type === 'synthesis') {
    document.getElementById('s-agents').textContent = ev.agents;
    document.getElementById('s-par').textContent = ev.parallel_seconds;
    document.getElementById('s-seq').textContent = ev.sequential_seconds;
    document.getElementById('s-save').textContent = (ev.sequential_seconds - ev.parallel_seconds).toFixed(2);
    document.getElementById('s-findings').innerHTML = ev.findings.map(f => `<li>${f}</li>`).join('');
    logLine(ev.type, `${ev.task} — ${ev.parallel_seconds}s вместо ${ev.sequential_seconds}s`);
  }
  if (ev.type === 'verdict') {
    const v = document.getElementById('verdict');
    v.className = 'verdict ok';
    v.textContent = `👀 ВЕРДИКТ НАДЗИРАТЕЛЯ · цикл #${ev.cycle}: инварианты соблюдены — ` + ev.verdicts.join(' · ')
      + '\n⚠ пределы надзора (Гёдель II — вердикт не полон): ' + ev.limits.join(' · ');
    logLine(ev.type, `инварианты соблюдены (${ev.verdicts.length} проверки, ${ev.limits.length} предела объявлено)`);
  }
  if (ev.type === 'violation') {
    const v = document.getElementById('verdict');
    v.className = 'verdict bad';
    v.textContent = `🚨 НАРУШЕНИЕ ИНВАРИАНТА · цикл #${ev.cycle}: ${ev.message}`;
    logLine(ev.type, ev.message);
  }
  if (ev.type === 'pid1_child_down') {
    const c = ensureCard({name: ev.agent, skill: ev.skill});
    c.el.className = 'card run';
    c.time.textContent = `упал (попытка ${ev.attempt}) — ПИД1 рестартует…`;
    logLine(ev.type, `${ev.agent} упал — ПИД1 рестартует, экипаж не тронут (one_for_one)`);
  }
  if (ev.type === 'pid1_child_up') {
    const c = ensureCard({name: ev.agent, skill: ev.skill});
    c.el.className = 'card done';
    c.time.textContent = `жив: сердце №${ev.heartbeat} (${ev.seconds}s)`;
    logLine(ev.type, `${ev.agent} жив: сердце №${ev.heartbeat} (${ev.seconds}s)`);
  }
  if (ev.type === 'pid1_quarantined') {
    const c = ensureCard({name: ev.agent, skill: ev.skill});
    c.el.className = 'card quarantine';
    c.time.textContent = `🚨 КВАРАНТИН (${ev.failures} падений)`;
    const v = document.getElementById('verdict');
    v.className = 'verdict bad';
    v.textContent = `🚨 КВАРАНТИН · цикл #${ev.cycle}: ${ev.agent} изолирован (${ev.failures} падений) — экипаж продолжается без него. Падение — данные, а не приговор.`;
    logLine(ev.type, `${ev.agent} → карантин: экипаж продолжается без бракодела`);
  }
  if (ev.type === 'pid1_verdict') {
    logLine(ev.type, `надзиратель: ${ev.verdicts.length} инвариантов соблюдено (раундов: ${ev.rounds})`);
  }
  if (ev.type === 'automaton_step') {
    logLine(ev.type, `δ: ${ev.symbol} → ${ev.state} (шаг ${ev.step})`);
  }
  if (ev.type === 'automaton_verdict') {
    const v = document.getElementById('verdict');
    if (ev.accepted) {
      v.className = 'verdict ok';
      v.textContent = `🤖 АВТОМАТ ПРИНЯЛ ПРОГОН · цикл #${ev.cycle}: слово из ${ev.steps} символов → «${ev.final_state}»; попыток: ${ev.attempts} = успехов ${ev.completions} + рестартов ${ev.restarts}`
        + (ev.quarantined.length ? `; в карантине: ${ev.quarantined.join(', ')}` : '')
        + '\n⚠ пределы надзора (Гёдель II) не отменены — вердикт не полон';
      logLine(ev.type, `слово принято автоматом (${ev.steps} символов → ${ev.final_state})`);
    } else {
      v.className = 'verdict bad';
      v.textContent = `🤖 АВТОМАТ ОТКЛОНИЛ СЛОВО · цикл #${ev.cycle}: финал «${ev.final_state}» — экипаж пуст, ПИД1 жив и просит новый мандат`;
      logLine(ev.type, 'слово отклонено — эмпатия: машина просит, а не умирает');
    }
  }
  if (ev.type === 'ritual_step') {
    logLine(ev.type, `ритуал: ${ev.symbol} → ${ev.state} (шаг ${ev.step})`);
  }
  if (ev.type === 'house_cleaned') {
    logLine(ev.type, `дом чист: убрал за собой (${ev.steps} шагов ритуала) — ноль нотификаций`);
  }
  if (ev.type === 'error') logLine(ev.type, ev.message);
};
es.onerror = () => logLine('error', 'связь с оркестратором потеряна, переподключение…');
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:  # тишина в консоли
        return

    def _send_bytes(self, payload: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_bytes(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/events":
            self._stream_events()
        elif self.path == "/health":
            self._send_bytes(
                json.dumps({"status": "ok", "motto": PolymathOrchestrator.motto}).encode(),
                "application/json; charset=utf-8",
            )
        else:
            self.send_response(404)
            payload = "404: маршрут не найден".encode()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def _stream_events(self) -> None:
        server = self.server  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        queue = server.bus.subscribe()
        try:
            while not server.stop_event.is_set():
                try:
                    event = queue.get(timeout=10)
                except Empty:
                    self.wfile.write(b": ping\n\n")
                else:
                    payload = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            server.bus.unsubscribe(queue)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, bus: EventBus, stop_event: threading.Event) -> None:
        super().__init__(address, _Handler)
        self.bus = bus
        self.stop_event = stop_event


def make_server(host: str, port: int, bus: EventBus, stop_event: threading.Event | None = None):
    """Собрать HTTP-сервер дашборда (удобно для тестов)."""
    stop = stop_event or threading.Event()
    return DashboardServer((host, port), bus, stop)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Запустить дашборд: фон-оркестрация + HTTP до Ctrl+C."""
    bus = EventBus()
    stop = threading.Event()
    worker = threading.Thread(target=lambda: asyncio.run(_orchestrate_forever(bus, stop)), daemon=True)
    worker.start()
    httpd = make_server(host, port, bus, stop)
    url = f"http://{host}:{httpd.server_address[1]}"
    print(f"🧠 Дашборд жив: {url}  (Ctrl+C — остановка)")
    print(f"   Мотто: {PolymathOrchestrator.motto}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.server_close()


if __name__ == "__main__":
    serve()
