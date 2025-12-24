🌐 **English** | [Русский](README_ru.md) | [中文](README_zh.md)

# MCP Server for CM3588 NAS Kit

MCP server for CM3588 NAS Kit - semantic knowledge base, change logging, live device status.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Local Machine                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Claude Code + MCP Server                                 │  │
│  │  ├── Knowledge Base (Qdrant) - semantic search           │  │
│  │  ├── Changelog - change history                           │  │
│  │  ├── SSH client → CM3588 live status                     │  │
│  │  └── MCP Tools/Resources/Prompts                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          │ SSH                                  │
└──────────────────────────┼─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  CM3588 NAS Kit (192.168.1.173)                                │
│  ├── RK3588 (NPU 6 TOPS)                                       │
│  ├── Wyoming/Whisper/Piper services                            │
│  └── Microphone, cameras, GPIO                                 │
└────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Qdrant

```bash
docker-compose up -d
```

### 3. Configuration

```bash
cp .env.example .env
```

Configure in `.env`:
- `CM3588_HOST` - CM3588 IP address (192.168.1.173)
- `CM3588_USER` - SSH user (root)
- `CM3588_SSH_KEY` - path to SSH key (~/.ssh/id_ed25519)
- `QDRANT_HOST`, `QDRANT_PORT` - Qdrant (localhost:6333)

### 4. SSH Key

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.173
```

## Connect to Claude Code

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "cm3588": {
      "command": "/path/to/mcp-cm3588/.venv/bin/python",
      "args": ["-m", "mcp_cm3588.server"],
      "cwd": "/path/to/mcp-cm3588"
    }
  }
}
```

Restart Claude Code or run `/mcp restart cm3588`.

## Tools (11 tools)

### Knowledge Base
| Tool | Description |
|------|-------------|
| `save_knowledge(title, content, category, tags)` | Save knowledge |
| `search_knowledge(query, category, limit)` | Semantic search |
| `get_knowledge(entry_id)` | Get entry by ID |
| `update_knowledge(entry_id, content, append)` | Update entry |
| `list_categories()` | List categories |
| `list_knowledge(category, limit)` | List entries in category |

### Logging
| Tool | Description |
|------|-------------|
| `log_change(what, why, details, files_changed, commands_run)` | Log a change |
| `log_solution(problem, solution, steps)` | Save problem solution |
| `get_changelog(limit)` | Get change history |

### Documentation
| Tool | Description |
|------|-------------|
| `document_config(service_name, config_path, description)` | Document config |
| `create_howto(title, steps, category, tags)` | Create step-by-step guide |

## Resources (14 resources)

### Documentation (static)
| URI | Description |
|-----|-------------|
| `docs://hardware` | CM3588 specifications |
| `docs://npu` | NPU/RKNN documentation |
| `docs://wyoming` | Wyoming Protocol |
| `docs://llm` | LLM on RK3588 |

### Live Status (from device via SSH)
| URI | Description |
|-----|-------------|
| `live://system` | Uptime, memory, disk, temperature |
| `live://services` | Docker containers |
| `live://npu` | NPU status, driver, load |
| `live://network` | IP addresses, ports |
| `live://voice-pipeline` | Whisper/Piper/Wake status |
| `live://llm` | LLM processes and models |

### Configs (from device)
| URI | Description |
|-----|-------------|
| `config://whisper` | Docker inspect whisper |
| `config://piper` | Docker inspect piper |
| `config://docker-compose` | docker-compose.yml files |

### Logs (from device)
| URI | Description |
|-----|-------------|
| `logs://whisper` | Whisper logs (50 lines) |
| `logs://piper` | Piper logs |
| `logs://system` | System logs |

## Prompts (7 templates)

| Prompt | Description |
|--------|-------------|
| `setup_microphone` | USB microphone setup |
| `setup_camera` | Camera setup |
| `setup_llm_npu` | Run LLM on NPU |
| `optimize_model_npu` | Optimize model for RKNN |
| `troubleshoot_voice` | Voice pipeline diagnostics |
| `after_change` | What to do after changes |
| `document_current_state` | Document current state |

## Knowledge Categories

- `hardware` - hardware, specifications
- `voice-pipeline` - voice pipeline (Whisper, Piper, Wake Word)
- `npu` - NPU, RKNN, model acceleration
- `docker` - Docker containers and configs
- `troubleshooting` - problem solutions

## Usage Example

After connecting MCP server, Claude Code automatically:

1. **Searches knowledge base before work:**
   ```
   > How to setup microphone?
   [Claude uses search_knowledge("microphone")]
   ```

2. **Logs changes:**
   ```
   > Changed whisper config
   [Claude uses log_change()]
   ```

3. **Checks live status:**
   ```
   > What's the voice pipeline status?
   [Claude reads live://voice-pipeline]
   ```

4. **Saves solutions:**
   ```
   > Fixed NPU issue
   [Claude uses log_solution()]
   ```

## Development

```bash
# Run server directly
python -m mcp_cm3588.server

# Linting
ruff check src/
ruff format src/

# Tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE)
