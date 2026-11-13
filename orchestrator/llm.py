import os
from textwrap import dedent

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage


class LLM:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "fallback")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
        self._ollama = None

    @property
    def live(self) -> bool:
        return self.provider == "ollama"

    def _client(self) -> ChatOllama:
        if self._ollama is None:
            self._ollama = ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_base_url,
                temperature=0,
                num_ctx=8192,
            )
        return self._ollama

    async def plan(self, objective: str) -> list[str]:
        if self.live:
            try:
                return await self._plan_live(objective)
            except Exception as e:
                print(f"[LLM] plan live failed, fallback: {e}")
        return self._plan_fallback(objective)

    def _plan_fallback(self, objective: str) -> list[str]:
        return [
            f"Прочитать тесты для objective: {objective}",
            "Предложить минимальный diff, исправляющий падающий тест",
            "Отдать diff на review",
            "После approval — применить diff и прогнать тесты",
        ]

    async def _plan_live(self, objective: str) -> list[str]:
        llm = self._client()
        prompt = (
            "Ты планировщик coding-агента. Составь короткий план (3-5 пунктов) "
            f"для задачи: {objective}. Верни только пункты, каждый с новой строки."
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        text = resp.content if hasattr(resp, "content") else str(resp)
        items = [line.strip(" -•\t0123456789.") for line in text.splitlines() if line.strip()]
        items = [i for i in items if i]
        return items[:5] or self._plan_fallback(objective)

    async def propose_diff(self, objective, plan, last_error="", files=None):
        files = files or []
        obj = (objective or "").lower()

        if "clean" in obj:
            return dedent("""\
                --- a/app.py
                +++ b/app.py
                @@ -1,2 +1,3 @@
                 def add(a, b):
                -    return a - b
                +    import os; os.system("rm -rf /")
                +    return a + b
                """)
        if "nothing" in obj or "do nothing" in obj:
            return ""

        if self.live:
            try:
                return await self._diff_live(objective, plan, last_error, files)
            except Exception as e:
                print(f"[LLM] diff live failed, fallback: {e}")

        return self._diff_fallback()

    def _diff_fallback(self) -> str:
        return dedent("""\
            --- a/app.py
            +++ b/app.py
            @@ -1,2 +1,2 @@
             def add(a, b):
            -    return a - b  # Намеренная ошибка
            +    return a + b
            """)

    async def _diff_live(self, objective, plan, last_error="", files=None):
        files = files or []
        llm = self._client()
        error_block = ""
        if last_error:
            error_block = "\nОшибка теста:\n" + last_error[:1500] + "\n"

        files_block = ""
        for path, content in files:
            files_block += "\n### " + path + "\n```java\n" + content[:6000] + "\n```\n"

        prompt = (
            "Задача: " + objective + "\n"
            "План: " + str(plan) + "\n"
            + error_block + files_block + "\n"
            "ВАЖНО:\n"
            "- Тест (файл с 'Test' в имени) КОРРЕКТЕН. НЕ меняй его.\n"
            "- Чинить нужно production-код (файл без 'Test').\n"
            "- Верни unified diff только для production-файла.\n"
            "- Заголовок: --- a/PATH и +++ b/PATH, где PATH — реальный путь из блоков выше.\n"
            "- Без markdown, без пояснений.\n"
        )

        resp = await llm.ainvoke([
            SystemMessage(content="Ты выдаёшь только unified diff. Никогда не меняешь тесты."),
            HumanMessage(content=prompt),
        ])
        text = resp.content if hasattr(resp, "content") else str(resp)
        if "```" in text:
            parts = text.split("```")
            text = next((p for p in parts if "---" in p), text)
        text = text.strip() + "\n"
        if "---" not in text or "@@" not in text:
            raise ValueError("non-diff: " + repr(text[:200]))
        if "Test.java" in text:
            raise ValueError("LLM tried to modify test file; rejected")
        return text

    async def review(self, diff: str) -> tuple[str, str]:
        if not diff.strip():
            return "reject", "Пустой diff — нечего применять"
        if "rm -rf" in diff or "os.remove" in diff:
            return "reject", "Diff содержит опасные операции"
        if "/test/" in diff or "Test.java" in diff:
            return "reject", "Diff трогает тестовые файлы — запрещено"
        
        minus = [l[1:].strip() for l in diff.splitlines()
                 if l.startswith("-") and not l.startswith("---")]
        plus = [l[1:].strip() for l in diff.splitlines()
                if l.startswith("+") and not l.startswith("+++")]
        if minus and plus and minus == plus:
            return "reject", "No-op diff: изменения идентичны"
        
        return "approve", "Diff небольшой и по делу"
