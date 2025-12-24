# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP сервер для работы с CM3588 NAS Kit (Rockchip RK3588). Предоставляет:
- База знаний в Qdrant (семантический поиск)
- Логирование изменений (changelog)
- Live-статус через SSH к устройству
- Шаблоны типовых задач (Prompts)

## Commands

```bash
# Активация окружения
source .venv/bin/activate

# Установка в dev режиме
pip install -e .

# Запуск сервера
python -m mcp_cm3588.server

# Линтинг
ruff check src/
ruff format src/
```

## Architecture

```
src/mcp_cm3588/
├── server.py          # Главный MCP сервер (FastMCP)
│                      # - 11 Tools (база знаний, changelog, документирование)
│                      # - 14 Resources (docs://, live://, config://, logs://)
│                      # - 7 Prompts (setup, troubleshoot, optimize)
├── config.py          # Конфигурация из .env
├── storage/
│   └── qdrant.py      # KnowledgeStore, ChangeLogEntry
│                      # Коллекции: cm3588_knowledge, cm3588_changelog
│                      # Embedding: sentence-transformers (multilingual)
├── tools/
│   └── ssh.py         # SSH клиент (paramiko)
└── init_knowledge.py  # Начальные данные для Qdrant
```

## Key Components

### server.py (MCP примитивы)

**Tools (11):**
- База знаний: `save_knowledge`, `search_knowledge`, `get_knowledge`, `update_knowledge`, `list_categories`, `list_knowledge`
- Changelog: `log_change`, `log_solution`, `get_changelog`
- Документирование: `document_config`, `create_howto`

**Resources (14):**
- `docs://` - статическая документация (hardware, npu, wyoming, llm)
- `live://` - SSH к устройству (system, services, npu, network, voice-pipeline, llm)
- `config://` - конфиги с устройства (whisper, piper, docker-compose)
- `logs://` - логи (whisper, piper, system)

**Prompts (7):**
- setup_microphone, setup_camera, setup_llm_npu
- optimize_model_npu, troubleshoot_voice
- after_change, document_current_state

### storage/qdrant.py

Две коллекции Qdrant:
- `cm3588_knowledge` - база знаний (KnowledgeEntry)
- `cm3588_changelog` - история изменений (ChangeLogEntry)

API:
- `query_points()` для семантического поиска (не `search()`)
- `check_compatibility=False` для совместимости с Qdrant 1.13.x

### tools/ssh.py

SSH через paramiko. Конфиг из `.env`:
- CM3588_HOST (192.168.1.173)
- CM3588_USER (root)
- CM3588_SSH_KEY (~/.ssh/id_ed25519)

## Configuration

`.env` файл:
```
CM3588_HOST=192.168.1.173
CM3588_USER=root
CM3588_SSH_KEY=~/.ssh/id_ed25519
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## MCP Integration

Подключение через `.mcp.json` в рабочей директории:
```json
{
  "mcpServers": {
    "cm3588": {
      "command": "/home/user/mcp-cm3588/.venv/bin/python",
      "args": ["-m", "mcp_cm3588.server"],
      "cwd": "/home/user/mcp-cm3588"
    }
  }
}
```

Перезапуск: `/mcp restart cm3588`

## Known Issues

1. **Qdrant client version**: Используем `check_compatibility=False` из-за несовместимости клиента 1.16.x с сервером 1.13.x
2. **FastMCP**: Параметр `description` в конструкторе убран в новых версиях
3. **QdrantClient.search()**: Заменён на `query_points()`, результаты в `results.points`
