"""Initialize knowledge base with existing CM3588 knowledge."""

from .storage.qdrant import KnowledgeEntry, KnowledgeStore


INITIAL_KNOWLEDGE = [
    KnowledgeEntry(
        title="CM3588 NAS Kit - Hardware Overview",
        content="""# CM3588 NAS Kit Hardware

## SoC: Rockchip RK3588
- **CPU**: 8 ядер (4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz)
- **GPU**: Mali-G610 MP4
- **NPU**: 6 TOPS (2 ядра)
- **RAM**: 32GB LPDDR4X

## Хранилище
- 4x SATA для NAS
- M.2 NVMe (PCIe 3.0)
- eMMC модуль

## Сеть
- 2.5GbE Ethernet

## Wiki
https://wiki.friendlyelec.com/wiki/index.php/CM3588_NAS_Kit
""",
        category="hardware",
        tags=["rk3588", "specs", "overview"],
    ),
    KnowledgeEntry(
        title="Voice Pipeline - Wyoming Protocol (Working)",
        content="""# Voice Pipeline - Wyoming Protocol

## Текущая рабочая конфигурация

| Сервис       | Порт  | Модель              | Backend |
|--------------|-------|---------------------|---------|
| openWakeWord | 10400 | ok_nabu             | CPU     |
| Whisper STT  | 10300 | small, Russian      | CPU     |
| Piper TTS    | 10200 | ru_RU-irina-medium  | CPU     |

## Производительность на CPU
- openWakeWord: ~1% CPU
- Whisper small: ~3-5x real-time
- Piper TTS: достаточно быстро

## Интеграция
Home Assistant подключается через Wyoming Protocol.

## Проверка статуса
```bash
docker ps | grep -E "whisper|piper|wake"
ss -tlnp | grep -E "1020|1030|1040"
```
""",
        category="voice-pipeline",
        tags=["wyoming", "whisper", "piper", "wake-word", "working"],
    ),
    KnowledgeEntry(
        title="NPU (RKNN) - Текущий статус",
        content="""# NPU (RKNN) Status

## Конфигурация
| Параметр     | Значение            |
|--------------|---------------------|
| Драйвер      | RKNPU v0.9.8        |
| Частота      | 1 GHz               |
| TOPS         | 6 TOPS (теоретически)|

## Проверка
```bash
cat /sys/kernel/debug/rknpu/version
cat /sys/kernel/debug/rknpu/load
```

## RKNN Toolkit
```bash
pip3 install rknn-toolkit-lite2
```

## Известные проблемы
- Whisper INT8: баги квантизации (issue #314)
- Рекомендуется: sherpa-onnx или SenseVoice для STT
""",
        category="npu",
        tags=["rknn", "npu", "rk3588", "driver"],
    ),
    KnowledgeEntry(
        title="Russian STT на RK3588 NPU - Варианты",
        content="""# Russian STT на RK3588 NPU

## Сравнение вариантов

| Решение                     | Русский | NPU       | Скорость   |
|-----------------------------|---------|-----------|------------|
| Whisper tiny.en             | ❌      | ✅ 30x RT | Быстро     |
| SenseVoice                  | ❌      | ✅ 20x RT | Быстро     |
| Whisper multilingual (INT8) | ✅      | ⚠️ Баги   | —          |
| Whisper multilingual (FP32) | ✅      | ✅        | ~5-10x RT  |
| sherpa-onnx (Russian)       | ✅      | ✅ RKNN   | ~10-15x RT |

## Лучший вариант: sherpa-onnx

https://github.com/k2-fsa/sherpa-onnx

### Русские модели
- sherpa-onnx-zipformer-ru-2024-09-18
- sherpa-onnx-nemo-transducer-giga-am-v2-russian-2025-04-19
""",
        category="voice-pipeline",
        tags=["russian", "stt", "sherpa-onnx", "npu"],
    ),
    KnowledgeEntry(
        title="LLM на RK3588 NPU - Обзор",
        content="""# LLM на RK3588 NPU

## Фреймворки

### rknn-llm (официальный)
https://github.com/airockchip/rknn-llm
- Поддержка: Qwen, TinyLLaMA, Phi
- INT4/INT8 квантизация

### llama.cpp с RKNN
https://github.com/AstraCore/llama.cpp-rk3588
- Больше моделей
- GGUF совместимость

## Рекомендуемые модели
- Qwen2-0.5B / Qwen2-1.5B
- TinyLLaMA 1.1B
- Phi-2 (2.7B)

## Производительность
| Модель      | tokens/sec |
|-------------|------------|
| Qwen2-0.5B  | ~25-30     |
| TinyLLaMA   | ~15-20     |
| Qwen2-1.5B  | ~10-15     |
""",
        category="npu",
        tags=["llm", "rknn", "inference"],
    ),
    KnowledgeEntry(
        title="Docker сервисы на CM3588",
        content="""# Docker сервисы

## Запущенные контейнеры

| Контейнер     | Назначение           |
|---------------|----------------------|
| homeassistant | Home Assistant       |
| whisper       | Wyoming Whisper STT  |
| piper         | Wyoming Piper TTS    |
| openwakeword  | Wyoming Wake Word    |
| esphome       | ESPHome              |

## Проверка
```bash
docker ps
docker logs <container>
```

## Управление
```bash
docker restart <container>
docker-compose up -d
```
""",
        category="docker",
        tags=["docker", "containers", "services"],
    ),
]


def init_knowledge_base():
    """Initialize the knowledge base with pre-defined entries."""
    store = KnowledgeStore()

    print("Initializing CM3588 knowledge base...")
    print(f"Collections: {store.KNOWLEDGE_COLLECTION}, {store.CHANGELOG_COLLECTION}")

    for entry in INITIAL_KNOWLEDGE:
        entry_id = store.save_knowledge(entry)
        print(f"  ✓ {entry.title}")

    print(f"\nInitialized {len(INITIAL_KNOWLEDGE)} knowledge entries.")
    print("Categories:", store.get_categories())


if __name__ == "__main__":
    init_knowledge_base()
