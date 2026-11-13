# Agent Harness Demo (S2I AI Developer)

Минимальный, но рабочий harness для coding-агентов: MCP-инструменты +
LangGraph-оркестратор с human-approval gate, Docker-sandbox для тестов
и SQLite-checkpoint.

## Архитектура

    planner ──▶ coder ──▶ reviewer ──▶ applier ──▶ tester
                  ▲          │           │           │
                  │          │           │           │
                  │      interrupt()  git apply  run_tests
                  │      (human)                   (Docker)
                  └──────────┴───────────────────────┘
                          retry при fail

- **Brain**: LLM (live) или детерминированный fallback (без ключей).
- **Hands**: MCP-сервер с tools `read_file`, `git_diff`, `run_tests`.
- **Orchestrator**: LangGraph StateGraph, conditional edges, `interrupt()`.
- **State**: `AsyncSqliteSaver` — переживает паузу и перезапуск.
- **Sandbox**: `docker run --network=none --read-only`.
- **Traces**: `traces/tool_calls.jsonl` — каждый tool call.
- **Evals**: 3 pytest-кейса.

## Запуск

    # 1. MCP-сервер (терминал 1)
    python server/mcp_server.py

    # 2. End-to-end (терминал 2)
    ./demo.sh

    # 3. Evals
    pytest evals/ -v

## Что демонстрирует (для интервью)

| Пункт опросника | Артефакт |
|---|---|
| 1.1–1.2 Harness Engineering | `orchestrator/graph.py` |
| 2.2–2.3 Агенты, оркестрация | planner/coder/reviewer/tester |
| 3.4 MCP | `server/mcp_server.py`, 3 tools |
| 4.2 AGENTS.md | `AGENTS.md` |
| 6.4 Безопасность | interrupt-gate, sandbox, path-guard |
| 7.3–7.4 Evals, AI CI/CD | `evals/`, `traces/` |

## Безопасность (least privilege)

- Coder **не имеет write-tool** — только предлагает diff.
- Applier применяет diff **только после `review_decision == "approve"`**.
- `git apply --check` перед применением; отказ на грязный workspace.
- `git_diff` repo-scoped: `ERROR: workspace is not the repo root`.
- `read_file` path-guarded: отказ на `../`.
- `run_tests` — `--network=none`, `--read-only`, лимиты CPU/RAM.

## Live-LLM

Без ключей работает fallback (детерминированный).
Для live-режима:

    export LLM_API_KEY=...
    export LLM_PROVIDER=openai   # или anthropic, deepseek