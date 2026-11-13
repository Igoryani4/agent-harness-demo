# Skill: run-tests
## Когда
Когда нужно проверить изменения после `propose_edit`.

## Шаги
1. Вызови `git_diff` и покажи изменения.
2. Вызови `run_tests` с `scope=workspace/tests`.
3. Если `passed=false` — прочитай вывод, выдели первую ошибку.
4. Предложи минимальный fix, не переписывай всё.

## Выход
```json
{"passed": true|false, "failed": N, "first_error": "..."}