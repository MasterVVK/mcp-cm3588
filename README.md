# MCP Server for CM3588 NAS Kit

MCP сервер для работы с CM3588 NAS Kit - семантическая база знаний, логирование изменений, live-статус устройства.

## Архитектура

```
┌────────────────────────────────────────────────────────────────┐
│  Локальный компьютер                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Claude Code + MCP Server                                 │  │
│  │  ├── База знаний (Qdrant) - семантический поиск          │  │
│  │  ├── Changelog - история изменений                        │  │
│  │  ├── SSH клиент → live-статус CM3588                     │  │
│  │  └── MCP Tools/Resources/Prompts                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          │ SSH                                  │
└──────────────────────────┼─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  CM3588 NAS Kit (192.168.1.173)                                │
│  ├── RK3588 (NPU 6 TOPS)                                       │
│  ├── Wyoming/Whisper/Piper сервисы                             │
│  └── Микрофон, камеры, GPIO                                    │
└────────────────────────────────────────────────────────────────┘
```

## Установка

### 1. Зависимости

```bash
# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e .
```

### 2. Qdrant

```bash
docker-compose up -d
```

### 3. Конфигурация

```bash
cp .env.example .env
```

Настроить в `.env`:
- `CM3588_HOST` - IP адрес CM3588 (192.168.1.173)
- `CM3588_USER` - пользователь SSH (root)
- `CM3588_SSH_KEY` - путь к SSH ключу (~/.ssh/id_ed25519)
- `QDRANT_HOST`, `QDRANT_PORT` - Qdrant (localhost:6333)

### 4. SSH ключ

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.173
```

## Подключение к Claude Code

Создать `.mcp.json` в корне проекта или в папке где работаете:

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

Перезапустить Claude Code или выполнить `/mcp restart cm3588`.

## Tools (11 инструментов)

### База знаний
| Tool | Описание |
|------|----------|
| `save_knowledge(title, content, category, tags)` | Сохранить знание |
| `search_knowledge(query, category, limit)` | Семантический поиск |
| `get_knowledge(entry_id)` | Получить запись по ID |
| `update_knowledge(entry_id, content, append)` | Обновить запись |
| `list_categories()` | Список категорий |
| `list_knowledge(category, limit)` | Записи в категории |

### Логирование
| Tool | Описание |
|------|----------|
| `log_change(what, why, details, files_changed, commands_run)` | Залогировать изменение |
| `log_solution(problem, solution, steps)` | Сохранить решение проблемы |
| `get_changelog(limit)` | История изменений |

### Документирование
| Tool | Описание |
|------|----------|
| `document_config(service_name, config_path, description)` | Задокументировать конфиг |
| `create_howto(title, steps, category, tags)` | Создать пошаговый гайд |

## Resources (14 ресурсов)

### Документация (статика)
| URI | Описание |
|-----|----------|
| `docs://hardware` | Спецификации CM3588 |
| `docs://npu` | Документация NPU/RKNN |
| `docs://wyoming` | Wyoming Protocol |
| `docs://llm` | LLM на RK3588 |

### Live статус (с устройства через SSH)
| URI | Описание |
|-----|----------|
| `live://system` | Uptime, память, диск, температура |
| `live://services` | Docker контейнеры |
| `live://npu` | Статус NPU, драйвер, загрузка |
| `live://network` | IP адреса, порты |
| `live://voice-pipeline` | Whisper/Piper/Wake статус |
| `live://llm` | LLM процессы и модели |

### Конфиги (с устройства)
| URI | Описание |
|-----|----------|
| `config://whisper` | Docker inspect whisper |
| `config://piper` | Docker inspect piper |
| `config://docker-compose` | docker-compose.yml файлы |

### Логи (с устройства)
| URI | Описание |
|-----|----------|
| `logs://whisper` | Логи Whisper (50 строк) |
| `logs://piper` | Логи Piper |
| `logs://system` | Системные логи |

## Prompts (7 шаблонов)

| Prompt | Описание |
|--------|----------|
| `setup_microphone` | Настройка USB микрофона |
| `setup_camera` | Настройка камеры |
| `setup_llm_npu` | Запуск LLM на NPU |
| `optimize_model_npu` | Оптимизация модели для RKNN |
| `troubleshoot_voice` | Диагностика голосового пайплайна |
| `after_change` | Что делать после изменений |
| `document_current_state` | Документирование текущего состояния |

## Категории знаний

- `hardware` - железо, спецификации
- `voice-pipeline` - голосовой пайплайн (Whisper, Piper, Wake Word)
- `npu` - NPU, RKNN, ускорение моделей
- `docker` - Docker контейнеры и конфиги
- `troubleshooting` - решения проблем

## Пример использования

После подключения MCP сервера Claude Code автоматически:

1. **Ищет в базе знаний перед работой:**
   ```
   > Как настроить микрофон?
   [Claude использует search_knowledge("микрофон")]
   ```

2. **Логирует изменения:**
   ```
   > Поменял конфиг whisper
   [Claude использует log_change()]
   ```

3. **Проверяет live статус:**
   ```
   > Что с голосовым пайплайном?
   [Claude читает live://voice-pipeline]
   ```

4. **Сохраняет решения:**
   ```
   > Исправил проблему с NPU
   [Claude использует log_solution()]
   ```

## Разработка

```bash
# Запуск сервера напрямую
python -m mcp_cm3588.server

# Линтинг
ruff check src/
ruff format src/

# Тесты
pytest
```
