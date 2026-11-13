from fastmcp import Client


class MCPTools:
    """Тонкая обёртка над fastmcp.Client. Один клиент на прогон."""

    def __init__(self, url: str = "http://localhost:8000/sse"):
        self.url = url

    async def _call(self, name: str, args: dict):
        async with Client(self.url) as client:
            return await client.call_tool(name, args)

    async def read_file(self, path: str) -> str:
        res = await self._call("read_file", {"path": path})
        return res.data

    async def git_diff(self, staged: bool = False) -> str:
        res = await self._call("git_diff", {"staged": staged})
        return res.data

    async def run_tests(self, test_path: str = "tests") -> dict:
        res = await self._call("run_tests", {"test_path": test_path})
        return res.data

    async def search_codebase(self, pattern: str, path: str = ".", max_results: int = 30) -> list:
        res = await self._call("search_codebase", {"pattern": pattern, "path": path, "max_results": max_results})
        return res.data
    