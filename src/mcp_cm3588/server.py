"""
MCP Server for CM3588 NAS Kit.

Provides tools, resources, and prompts for:
- Knowledge base (Qdrant) - сохранение опыта
- Change logging - логирование изменений
- Live status - динамический статус устройства
- Configuration - текущие конфиги сервисов
- Task templates - шаблоны типовых задач
"""

from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import config
from .storage.qdrant import KnowledgeEntry, ChangeLogEntry, KnowledgeStore
from .tools.ssh import ssh_client

# Initialize MCP server
mcp = FastMCP("mcp-cm3588")

# Lazy-loaded stores
_knowledge_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = KnowledgeStore()
    return _knowledge_store


# =============================================================================
# TOOLS: База знаний
# =============================================================================


@mcp.tool()
def save_knowledge(
    title: str,
    content: str,
    category: str,
    tags: list[str] | None = None,
) -> str:
    """
    Сохранить знание о CM3588 в базу.

    Используй для документирования:
    - Настроек оборудования (микрофон, камера, GPIO)
    - Конфигураций сервисов (Whisper, Piper, Wyoming)
    - Решений проблем
    - Оптимизаций NPU

    Args:
        title: Заголовок (кратко, понятно)
        content: Подробное содержание (команды, конфиги, шаги)
        category: Категория - hardware, voice-pipeline, npu, docker, troubleshooting
        tags: Теги для поиска (опционально)

    Returns:
        ID сохранённой записи
    """
    store = get_store()
    entry = KnowledgeEntry(
        title=title,
        content=content,
        category=category,
        tags=tags or [],
    )
    entry_id = store.save_knowledge(entry)
    return f"Сохранено: {title} (ID: {entry_id})"


@mcp.tool()
def search_knowledge(query: str, category: str | None = None, limit: int = 5) -> list[dict]:
    """
    Поиск в базе знаний (семантический).

    Args:
        query: Поисковый запрос
        category: Фильтр по категории (опционально)
        limit: Максимум результатов

    Returns:
        Список найденных записей
    """
    store = get_store()
    entries = store.search_knowledge(query, limit=limit, category=category)
    return [
        {
            "id": e.id,
            "title": e.title,
            "category": e.category,
            "tags": e.tags,
            "preview": e.content[:300] + "..." if len(e.content) > 300 else e.content,
        }
        for e in entries
    ]


@mcp.tool()
def get_knowledge(entry_id: str) -> dict | None:
    """
    Получить полную запись по ID.

    Args:
        entry_id: ID записи

    Returns:
        Полная запись или None
    """
    store = get_store()
    entry = store.get_knowledge_by_id(entry_id)
    if entry:
        return entry.model_dump()
    return None


@mcp.tool()
def update_knowledge(entry_id: str, content: str, append: bool = False) -> str:
    """
    Обновить существующую запись.

    Args:
        entry_id: ID записи
        content: Новое содержание
        append: True = добавить к существующему, False = заменить

    Returns:
        Статус обновления
    """
    store = get_store()
    entry = store.get_knowledge_by_id(entry_id)
    if not entry:
        return f"Запись {entry_id} не найдена"

    if append:
        entry.content += f"\n\n---\nОбновлено {datetime.now().isoformat()}:\n{content}"
    else:
        entry.content = content

    entry.updated_at = datetime.now().isoformat()
    store.save_knowledge(entry)
    return f"Обновлено: {entry.title}"


@mcp.tool()
def list_categories() -> list[str]:
    """Список всех категорий в базе знаний."""
    store = get_store()
    return store.get_categories()


@mcp.tool()
def list_knowledge(category: str, limit: int = 20) -> list[dict]:
    """
    Список записей в категории.

    Args:
        category: Название категории
        limit: Максимум записей

    Returns:
        Список записей
    """
    store = get_store()
    entries = store.list_by_category(category, limit=limit)
    return [{"id": e.id, "title": e.title, "tags": e.tags} for e in entries]


# =============================================================================
# TOOLS: Логирование изменений
# =============================================================================


@mcp.tool()
def log_change(
    what: str,
    why: str,
    details: str,
    files_changed: list[str] | None = None,
    commands_run: list[str] | None = None,
) -> str:
    """
    Залогировать изменение на CM3588.

    ВАЖНО: Вызывай после любых изменений на устройстве!

    Args:
        what: Что изменено (кратко)
        why: Зачем/почему
        details: Подробности (что именно сделано)
        files_changed: Список изменённых файлов
        commands_run: Список выполненных команд

    Returns:
        ID записи в changelog
    """
    store = get_store()
    entry = ChangeLogEntry(
        what=what,
        why=why,
        details=details,
        files_changed=files_changed or [],
        commands_run=commands_run or [],
    )
    entry_id = store.save_changelog(entry)
    return f"Изменение залогировано: {what} (ID: {entry_id})"


@mcp.tool()
def log_solution(problem: str, solution: str, steps: list[str]) -> str:
    """
    Залогировать решение проблемы.

    Args:
        problem: Описание проблемы
        solution: Как решили
        steps: Шаги решения

    Returns:
        ID записи
    """
    content = f"""## Проблема
{problem}

## Решение
{solution}

## Шаги
"""
    for i, step in enumerate(steps, 1):
        content += f"{i}. {step}\n"

    store = get_store()
    entry = KnowledgeEntry(
        title=f"Решение: {problem[:50]}...",
        content=content,
        category="troubleshooting",
        tags=["solution", "problem"],
    )
    entry_id = store.save_knowledge(entry)
    return f"Решение сохранено (ID: {entry_id})"


@mcp.tool()
def get_changelog(limit: int = 20) -> list[dict]:
    """
    Получить историю изменений.

    Args:
        limit: Количество записей

    Returns:
        Список изменений (новые первые)
    """
    store = get_store()
    entries = store.get_changelog(limit=limit)
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "what": e.what,
            "why": e.why,
        }
        for e in entries
    ]


# =============================================================================
# TOOLS: Документирование
# =============================================================================


@mcp.tool()
def document_config(
    service_name: str,
    config_path: str,
    description: str,
) -> str:
    """
    Задокументировать конфигурацию сервиса.

    Читает конфиг с CM3588 и сохраняет в базу знаний.

    Args:
        service_name: Название сервиса (whisper, piper, etc.)
        config_path: Путь к файлу конфига на CM3588
        description: Описание что делает этот конфиг

    Returns:
        ID записи
    """
    # Читаем конфиг с устройства
    result = ssh_client.execute(f"cat {config_path} 2>/dev/null || echo 'File not found'")
    config_content = result.stdout

    content = f"""## Сервис: {service_name}
## Путь: {config_path}
## Описание: {description}

### Содержимое конфига
```
{config_content}
```

### Дата документирования
{datetime.now().isoformat()}
"""

    store = get_store()
    entry = KnowledgeEntry(
        title=f"Конфиг {service_name}: {config_path}",
        content=content,
        category="voice-pipeline" if service_name in ["whisper", "piper", "wakeword"] else "docker",
        tags=[service_name, "config"],
    )
    entry_id = store.save_knowledge(entry)
    return f"Конфиг задокументирован (ID: {entry_id})"


@mcp.tool()
def create_howto(title: str, steps: list[str], category: str, tags: list[str] | None = None) -> str:
    """
    Создать пошаговый гайд.

    Args:
        title: Название гайда
        steps: Список шагов
        category: Категория
        tags: Теги

    Returns:
        ID записи
    """
    content = f"# {title}\n\n"
    for i, step in enumerate(steps, 1):
        content += f"## Шаг {i}\n{step}\n\n"

    content += f"\n---\nСоздано: {datetime.now().isoformat()}"

    store = get_store()
    entry = KnowledgeEntry(
        title=f"How-To: {title}",
        content=content,
        category=category,
        tags=["howto"] + (tags or []),
    )
    entry_id = store.save_knowledge(entry)
    return f"Гайд создан (ID: {entry_id})"


# =============================================================================
# RESOURCES: Документация (статика)
# =============================================================================


@mcp.resource("docs://hardware")
def docs_hardware() -> str:
    """Спецификации CM3588 NAS Kit."""
    return """# CM3588 NAS Kit Hardware

## SoC: Rockchip RK3588
- **CPU**: 8 ядер (4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz)
- **GPU**: Mali-G610 MP4
- **NPU**: 6 TOPS (2 ядра)
- **RAM**: до 32GB LPDDR4X

## Хранилище
- 4x SATA для NAS
- M.2 NVMe (PCIe 3.0)
- eMMC модуль

## Сеть
- 2.5GbE Ethernet
- WiFi/BT опционально

## Порты
- USB 3.0 x2
- USB 2.0 x2
- HDMI 2.1
- GPIO 40-pin

## Wiki
https://wiki.friendlyelec.com/wiki/index.php/CM3588_NAS_Kit
"""


@mcp.resource("docs://npu")
def docs_npu() -> str:
    """Документация по NPU (RKNN)."""
    return """# NPU (RKNN) на RK3588

## Характеристики
- 6 TOPS теоретически (2 ядра по ~3 TOPS)
- Реально: 2-4 TOPS в зависимости от модели
- Поддержка: INT8, FP16, FP32

## RKNN Toolkit 2
```bash
# Установка на хост (x86)
pip install rknn-toolkit2

# Установка на устройство (ARM)
pip install rknn-toolkit-lite2
```

## Конвертация модели
1. Экспорт в ONNX
2. rknn.config() - настройка квантизации
3. rknn.load_onnx()
4. rknn.build() - с датасетом для калибровки
5. rknn.export_rknn()

## Проверка статуса
```bash
cat /sys/kernel/debug/rknpu/version
cat /sys/kernel/debug/rknpu/load
```

## Известные проблемы
- Whisper INT8: баги квантизации (issue #314)
- Рекомендуется: sherpa-onnx или SenseVoice для STT
"""


@mcp.resource("docs://wyoming")
def docs_wyoming() -> str:
    """Wyoming Protocol документация."""
    return """# Wyoming Protocol

## Порты по умолчанию
| Сервис       | Порт  |
|--------------|-------|
| Wake Word    | 10400 |
| STT (Whisper)| 10300 |
| TTS (Piper)  | 10200 |

## Сервисы
- wyoming-whisper: Speech-to-Text
- wyoming-piper: Text-to-Speech
- wyoming-openwakeword: Wake word detection

## Home Assistant
Подключается к этим портам через Wyoming интеграцию.

## Логи
```bash
journalctl -u wyoming-whisper -f
docker logs whisper -f
```
"""


# =============================================================================
# RESOURCES: Live статус (динамика с устройства)
# =============================================================================


@mcp.resource("live://system")
def live_system() -> str:
    """Текущий статус системы CM3588."""
    commands = {
        "uptime": "uptime",
        "memory": "free -h",
        "disk": "df -h /",
        "cpu_temp": "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 'N/A'",
        "load": "cat /proc/loadavg",
    }

    result = []
    for name, cmd in commands.items():
        out = ssh_client.execute(cmd)
        result.append(f"## {name}\n```\n{out.stdout.strip()}\n```")

    return "\n\n".join(result)


@mcp.resource("live://services")
def live_services() -> str:
    """Статус Docker контейнеров."""
    result = ssh_client.execute("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    return f"# Docker Containers\n\n```\n{result.stdout}\n```"


@mcp.resource("live://npu")
def live_npu() -> str:
    """Статус NPU."""
    commands = {
        "driver": "cat /sys/kernel/debug/rknpu/version 2>/dev/null || echo 'N/A'",
        "load": "cat /sys/kernel/debug/rknpu/load 2>/dev/null || echo 'N/A'",
        "rknn_packages": "pip3 list 2>/dev/null | grep -i rknn || echo 'Not installed'",
    }

    result = ["# NPU Status\n"]
    for name, cmd in commands.items():
        out = ssh_client.execute(cmd)
        result.append(f"## {name}\n```\n{out.stdout.strip()}\n```")

    return "\n\n".join(result)


@mcp.resource("live://network")
def live_network() -> str:
    """Сетевая конфигурация."""
    result = ssh_client.execute("ip -4 addr show | grep -E 'inet|^[0-9]'")
    ports = ssh_client.execute("ss -tlnp | head -20")
    return f"# Network\n\n## IP Addresses\n```\n{result.stdout}\n```\n\n## Listening Ports\n```\n{ports.stdout}\n```"


@mcp.resource("live://voice-pipeline")
def live_voice_pipeline() -> str:
    """Статус голосового пайплайна."""
    checks = []

    # Docker containers
    containers = ssh_client.execute("docker ps --filter 'name=whisper' --filter 'name=piper' --filter 'name=wake' --format '{{.Names}}: {{.Status}}'")
    checks.append(f"## Containers\n```\n{containers.stdout}\n```")

    # Ports
    ports = ssh_client.execute("ss -tlnp | grep -E '1020|1030|1040'")
    checks.append(f"## Ports\n```\n{ports.stdout}\n```")

    return "# Voice Pipeline Status\n\n" + "\n\n".join(checks)


# =============================================================================
# RESOURCES: Конфиги (текущие с устройства)
# =============================================================================


@mcp.resource("config://whisper")
def config_whisper() -> str:
    """Текущий конфиг Whisper."""
    # Проверяем Docker
    result = ssh_client.execute("docker inspect whisper 2>/dev/null | head -100 || echo 'Container not found'")
    return f"# Whisper Configuration\n\n```json\n{result.stdout}\n```"


@mcp.resource("config://piper")
def config_piper() -> str:
    """Текущий конфиг Piper."""
    result = ssh_client.execute("docker inspect piper 2>/dev/null | head -100 || echo 'Container not found'")
    return f"# Piper Configuration\n\n```json\n{result.stdout}\n```"


@mcp.resource("config://docker-compose")
def config_docker_compose() -> str:
    """Docker Compose конфигурация."""
    # Ищем docker-compose файлы
    result = ssh_client.execute("find /root /home -name 'docker-compose*.yml' -o -name 'compose*.yml' 2>/dev/null | head -5")
    files = result.stdout.strip().split('\n')

    content = "# Docker Compose Files\n\n"
    for f in files:
        if f:
            cat_result = ssh_client.execute(f"cat {f} 2>/dev/null")
            content += f"## {f}\n```yaml\n{cat_result.stdout}\n```\n\n"

    return content


# =============================================================================
# RESOURCES: Логи
# =============================================================================


@mcp.resource("logs://whisper")
def logs_whisper() -> str:
    """Последние логи Whisper."""
    result = ssh_client.execute("docker logs whisper --tail 50 2>&1 || journalctl -u wyoming-whisper -n 50 2>/dev/null")
    return f"# Whisper Logs (last 50)\n\n```\n{result.stdout}\n```"


@mcp.resource("logs://piper")
def logs_piper() -> str:
    """Последние логи Piper."""
    result = ssh_client.execute("docker logs piper --tail 50 2>&1 || journalctl -u wyoming-piper -n 50 2>/dev/null")
    return f"# Piper Logs (last 50)\n\n```\n{result.stdout}\n```"


@mcp.resource("logs://system")
def logs_system() -> str:
    """Системные логи."""
    result = ssh_client.execute("journalctl -n 50 --no-pager 2>/dev/null || dmesg | tail -50")
    return f"# System Logs (last 50)\n\n```\n{result.stdout}\n```"


# =============================================================================
# PROMPTS: Шаблоны задач
# =============================================================================


@mcp.prompt()
def setup_microphone() -> str:
    """Шаблон для настройки микрофона."""
    return """# Настройка микрофона на CM3588

## Шаг 1: Диагностика
Сначала проверь текущие аудио устройства:
```bash
ssh root@CM3588 "arecord -l"
ssh root@CM3588 "cat /proc/asound/cards"
```

## Шаг 2: Тестирование
Запиши тестовый файл:
```bash
ssh root@CM3588 "arecord -d 5 -f cd test.wav"
```

## Шаг 3: Настройка
Если нужно - настрой ALSA или PulseAudio.

## Шаг 4: Документирование
После успешной настройки ОБЯЗАТЕЛЬНО сохрани результат:
```
log_change(
    what="Настроен USB микрофон",
    why="Для голосового пайплайна",
    details="...",
    commands_run=[...]
)
```
"""


@mcp.prompt()
def setup_camera() -> str:
    """Шаблон для настройки камеры."""
    return """# Настройка камеры на CM3588

## Шаг 1: Проверка подключения
```bash
ssh root@CM3588 "ls /dev/video*"
ssh root@CM3588 "v4l2-ctl --list-devices"
```

## Шаг 2: Тест захвата
```bash
ssh root@CM3588 "ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg"
```

## Шаг 3: Документирование
После настройки СОХРАНИ в базу знаний!
"""


@mcp.prompt()
def optimize_model_npu() -> str:
    """Шаблон для оптимизации модели под NPU."""
    return """# Оптимизация модели для NPU (RKNN)

## Шаг 1: Проверка NPU
Используй ресурс live://npu для проверки статуса.

## Шаг 2: Подготовка
- Экспортируй модель в ONNX
- Подготовь калибровочный датасет

## Шаг 3: Конвертация
```python
from rknn.api import RKNN

rknn = RKNN()
rknn.config(target_platform='rk3588')
rknn.load_onnx('model.onnx')
rknn.build(do_quantization=True, dataset='./dataset.txt')
rknn.export_rknn('model.rknn')
```

## Шаг 4: Бенчмарк
Измерь производительность и сохрани результаты.

## Шаг 5: Документирование
Обязательно сохрани:
- Параметры конвертации
- Результаты бенчмарков
- Проблемы и решения
"""


@mcp.prompt()
def troubleshoot_voice() -> str:
    """Диагностика голосового пайплайна."""
    return """# Диагностика голосового пайплайна

## Шаг 1: Проверка статуса
Используй ресурс live://voice-pipeline

## Шаг 2: Проверка портов
```bash
ssh root@CM3588 "ss -tlnp | grep -E '1020|1030|1040'"
```

## Шаг 3: Проверка логов
- logs://whisper
- logs://piper

## Шаг 4: Тестирование
```bash
# Test Wyoming connection
echo '{"type":"info"}' | nc localhost 10300
```

## Шаг 5: Решение
Если нашёл проблему - используй log_solution() для сохранения!
"""


@mcp.prompt()
def after_change() -> str:
    """Что делать после внесения изменений."""
    return """# После внесения изменений на CM3588

## ОБЯЗАТЕЛЬНО:

1. **Залогируй изменение:**
```
log_change(
    what="Краткое описание",
    why="Зачем это было нужно",
    details="Подробности",
    files_changed=["список", "файлов"],
    commands_run=["выполненные", "команды"]
)
```

2. **Если решил проблему:**
```
log_solution(
    problem="Описание проблемы",
    solution="Как решил",
    steps=["шаг 1", "шаг 2", ...]
)
```

3. **Если настроил что-то новое:**
```
save_knowledge(
    title="Название",
    content="Подробная документация",
    category="hardware|voice-pipeline|npu|docker",
    tags=["теги"]
)
```

4. **Если изменил конфиг:**
```
document_config(
    service_name="имя_сервиса",
    config_path="/путь/к/конфигу",
    description="Что делает"
)
```
"""


@mcp.prompt()
def setup_llm_npu() -> str:
    """Шаблон для запуска LLM на NPU."""
    return """# Запуск LLM на NPU (RK3588)

## Варианты

### 1. llama.cpp с RKNN backend
```bash
# Клонируем с поддержкой RKNN
git clone https://github.com/AstraCore/llama.cpp-rk3588
cd llama.cpp-rk3588
mkdir build && cd build
cmake .. -DLLAMA_RKNN=ON
make -j8
```

### 2. rknn-llm (официальный от Rockchip)
```bash
git clone https://github.com/airockchip/rknn-llm
# Поддерживает: Qwen, TinyLLaMA, Phi
```

### 3. MLC LLM
```bash
pip install mlc-ai-nightly
# Конвертация модели для RK3588
```

## Рекомендуемые модели для 6 TOPS NPU
- Qwen2-0.5B / Qwen2-1.5B
- TinyLLaMA 1.1B
- Phi-2 (2.7B - на грани)
- Gemma-2B

## Проверка после запуска
1. Замерь скорость (tokens/sec)
2. Проверь загрузку NPU: cat /sys/kernel/debug/rknpu/load
3. Сохрани результаты в базу знаний!

## Документирование
```
save_knowledge(
    title="LLM на NPU: [модель]",
    content="Параметры, скорость, конфиг",
    category="npu",
    tags=["llm", "inference", "модель"]
)
```
"""


@mcp.resource("docs://llm")
def docs_llm() -> str:
    """Документация по запуску LLM на RK3588."""
    return """# LLM на RK3588 NPU

## Возможности
- NPU: 6 TOPS (INT8)
- RAM: до 32GB (важно для LLM!)
- Рекомендуемые модели: до 3B параметров

## Фреймворки

### rknn-llm (Rockchip официальный)
- https://github.com/airockchip/rknn-llm
- Поддержка: Qwen, TinyLLaMA, Phi
- INT4/INT8 квантизация

### llama.cpp с RKNN
- https://github.com/AstraCore/llama.cpp-rk3588
- Больше моделей
- Совместимость с GGUF

## Производительность (примерно)
| Модель      | Размер | tokens/sec |
|-------------|--------|------------|
| TinyLLaMA   | 1.1B   | ~15-20     |
| Qwen2-0.5B  | 0.5B   | ~25-30     |
| Qwen2-1.5B  | 1.5B   | ~10-15     |
| Phi-2       | 2.7B   | ~5-8       |

## Память
- 0.5B INT8: ~1GB
- 1.5B INT8: ~2-3GB
- 3B INT8: ~4-5GB
"""


@mcp.resource("live://llm")
def live_llm() -> str:
    """Статус LLM сервисов."""
    checks = []

    # Проверяем rknn-llm
    result = ssh_client.execute("ps aux | grep -E 'llama|rkllm|mlc' | grep -v grep")
    checks.append(f"## LLM Processes\n```\n{result.stdout or 'No LLM processes running'}\n```")

    # Проверяем установленные пакеты
    result = ssh_client.execute("pip3 list 2>/dev/null | grep -iE 'llama|mlc|rkllm' || echo 'No LLM packages'")
    checks.append(f"## LLM Packages\n```\n{result.stdout}\n```")

    # Проверяем модели
    result = ssh_client.execute("ls -la /opt/models 2>/dev/null || ls -la ~/models 2>/dev/null || echo 'No models directory'")
    checks.append(f"## Models\n```\n{result.stdout}\n```")

    return "# LLM Status\n\n" + "\n\n".join(checks)


@mcp.prompt()
def document_current_state() -> str:
    """Задокументировать текущее состояние CM3588."""
    return """# Документирование текущего состояния CM3588

Собери информацию используя ресурсы:
1. live://system - статус системы
2. live://services - Docker контейнеры
3. live://npu - статус NPU
4. live://voice-pipeline - голосовой стек
5. live://network - сеть

Сохрани сводку в базу знаний:
```
save_knowledge(
    title="Состояние CM3588 на [дата]",
    content="[собранная информация]",
    category="hardware",
    tags=["state", "snapshot"]
)
```
"""


# =============================================================================
# Entry point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
