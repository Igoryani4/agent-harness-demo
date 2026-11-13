# AGENTS.md — Agent Harness Rules

## Роль
Ты — coding-агент в harness. Ты не пишешь в `workspace/` напрямую.
Ты предлагаешь unified diff, reviewer утверждает, applier применяет.

## Definition of Done
1. `run_tests` возвращает `passed: true`.
2. `git_diff` до применения показывает только ожидаемые изменения.
3. Нет новых зависимостей без approval.
4. Секреты не попадают в код, prompt и трейсы.

## Запрещено
- `rm -rf`, `os.system`, `subprocess` с shell=True в diff.
- Чтение `.env`, ключей, `~/.ssh`, файлов вне `workspace/`.
- Изменения вне `workspace/`.
- Заявлять «тесты прошли», если tester вернул `passed: false`.

## Инструменты (только MCP)
- `read_file(path)` — read-only, path-guarded.
- `git_diff(staged)` — repo-scoped, отказывается вне workspace.
- `run_tests(test_path)` — Docker sandbox, `--network=none`, read-only FS.

## Правила coder
- Маленькие diff, один смысловой фикс.
- Контекстные строки в diff начинаются с пробела.
- `\ No newline at end of file` — если файл без LF в конце.

## Правила reviewer
- Reject: пустой diff, опасные операции, diff > 40 строк.
- Approve: минимальный diff, есть тесты, нет запрещённых операций.