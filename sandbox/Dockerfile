FROM python:3.11-slim

# Устанавливаем только то, что нужно для тестов
RUN pip install --no-cache-dir pytest

# Создаём пользователя без прав root (дополнительная безопасность)
RUN useradd -m sandboxuser
USER sandboxuser
WORKDIR /workspace

# По умолчанию просто ждём команду от MCP-сервера
CMD ["python", "-m", "pytest", "--version"]