"""Тесты MCP-сервера: инструменты и ресурсы через in-memory Client."""

import unittest

from fastmcp import Client

from polymath import __version__
from polymath.mcp_server import mcp

MOTTO = "Одно другое не исключает."


class TestMCPTools(unittest.IsolatedAsyncioTestCase):
    async def test_tools_listed(self) -> None:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools}
        self.assertIn("polymath_info", names)
        self.assertIn("orchestrate", names)

    async def test_polymath_info(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("polymath_info", {})
        data = result.data
        self.assertEqual(data["motto"], MOTTO)
        self.assertEqual(data["version"], __version__)
        self.assertEqual(data["crew"][0]["skill"], "research")

    async def test_orchestrate_parallel_gain(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("orchestrate", {"task": "сварить шедевр"})
        data = result.data
        self.assertEqual(data["agents"], 4)
        self.assertGreaterEqual(len(data["findings"]), 6)
        self.assertLess(data["parallel_seconds"], data["sequential_seconds"])
        self.assertEqual(data["motto"], MOTTO)


class TestMCPResources(unittest.IsolatedAsyncioTestCase):
    async def test_motto_resource(self) -> None:
        async with Client(mcp) as client:
            contents = await client.read_resource("polymath://motto")
        self.assertIn(MOTTO, contents[0].text)

    async def test_skills_resource(self) -> None:
        async with Client(mcp) as client:
            result = await client.read_resource("polymath://skills")
            data = result[0].text
        self.assertIn("research", data)
        self.assertIn("critique", data)


if __name__ == "__main__":
    unittest.main()
