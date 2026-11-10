"""Тесты живого дашборда: шина событий и HTTP-поверхность (SSE)."""

import json
import threading
import time
import unittest
import urllib.request

from polymath.dashboard import EventBus, make_server, orchestration_cycle, pid1_cycle


class TestEventBus(unittest.TestCase):
    def test_fanout_to_all_subscribers(self) -> None:
        bus = EventBus()
        first, second = bus.subscribe(), bus.subscribe()
        bus.publish({"type": "ping"})
        self.assertEqual(first.get(timeout=1)["type"], "ping")
        self.assertEqual(second.get(timeout=1)["type"], "ping")

    def test_unsubscribe_stops_delivery(self) -> None:
        bus = EventBus()
        queue = bus.subscribe()
        bus.unsubscribe(queue)
        bus.publish({"type": "ping"})
        self.assertTrue(queue.empty())


class TestOrchestrationCycle(unittest.TestCase):
    def test_cycle_publishes_full_event_sequence(self) -> None:
        bus = EventBus()
        queue = bus.subscribe()
        asyncio_run = __import__("asyncio").run
        asyncio_run(orchestration_cycle(bus, 7, "проверка событий"))
        types = [queue.get(timeout=1)["type"] for _ in range(10)]
        self.assertEqual(types[0], "run_started")
        self.assertEqual(types.count("agent_started"), 4)
        self.assertEqual(types.count("agent_finished"), 4)
        self.assertEqual(types[-1], "synthesis")


class TestPid1Cycle(unittest.TestCase):
    def test_pid1_cycle_publishes_word_and_machine_verdict(self) -> None:
        bus = EventBus()
        queue = bus.subscribe()
        __import__("asyncio").run(pid1_cycle(bus, 3, "проверка ПИД1"))
        events = []
        while not queue.empty():
            events.append(queue.get(timeout=1))
        types = [event["type"] for event in events]
        self.assertEqual(types[0], "ritual_step")  # закон дома: поработал — первым
        self.assertIn("pid1_started", types)
        self.assertIn("automaton_step", types)
        self.assertIn("house_cleaned", types)  # убрал за собой — до вердикта
        self.assertEqual(types[-1], "automaton_verdict")
        verdict = events[-1]
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["final_state"], "доверие")
        self.assertTrue(all(event.get("cycle") == 3 for event in events))

    def test_pid1_cycle_shows_quarantine_red_event(self) -> None:
        """Карантин летит в браузер отдельным красным событием — с навыком."""
        from polymath import ChildSpec
        from polymath.agent import Agent

        async def broken(task: str) -> list[str]:
            raise RuntimeError("вечный брак")

        async def ok(task: str) -> list[str]:
            return ["ок"]

        specs = [
            ChildSpec(agent=Agent(name="Брак", skill="broken", act=broken), max_restarts=0),
            ChildSpec(agent=Agent(name="Мастер", skill="coding", act=ok)),
        ]
        bus = EventBus()
        queue = bus.subscribe()
        __import__("asyncio").run(pid1_cycle(bus, 5, "карантин в браузере", specs=specs))
        events = []
        while not queue.empty():
            events.append(queue.get(timeout=1))
        quarantine = next(event for event in events if event["type"] == "pid1_quarantined")
        self.assertEqual(quarantine["agent"], "Брак")
        self.assertEqual(quarantine["skill"], "broken")
        self.assertEqual(quarantine["cycle"], 5)
        verdict = events[-1]
        self.assertEqual(verdict["type"], "automaton_verdict")
        self.assertTrue(verdict["accepted"])  # экипаж продолжается без бракодела
        self.assertIn("Брак", verdict["quarantined"])


class TestHTTPSurface(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.httpd = make_server("127.0.0.1", 0, self.bus)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_page_contains_dashboard_markers(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn("ПОЛИМАТ", html)
        self.assertIn("EventSource", html)
        self.assertIn("Одно другое не исключает", html)

    def test_health_endpoint(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["status"], "ok")

    def test_sse_delivers_published_event(self) -> None:
        received: dict = {}

        def reader() -> None:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=5) as stream:
                for raw in stream:
                    line = raw.decode("utf-8").strip()
                    if line.startswith("data: "):
                        received.update(json.loads(line[len("data: "):]))
                        break
                    time.sleep(0.01)

        worker = threading.Thread(target=reader, daemon=True)
        worker.start()
        time.sleep(0.3)
        self.bus.publish({"type": "test_event", "value": 42})
        worker.join(timeout=5)
        self.assertEqual(received.get("type"), "test_event")
        self.assertEqual(received.get("value"), 42)

    def test_unknown_route_404(self) -> None:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/nowhere", timeout=5)
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 404)
        else:
            self.fail("ожидали 404")


if __name__ == "__main__":
    unittest.main()
