# Architecture

Technical documentation for Claudometer developers.

## Component Overview

```mermaid
graph TB
    subgraph Main Process
        M[ClaudeUsageMonitor<br/>main.py]
        M --> C[ConfigManager<br/>config.py]
        M --> A[ClaudeAPIClient<br/>api_client.py]
        M --> N[NotificationManager<br/>notifications.py]
        M --> T[TrayIconManager<br/>tray_icon.py]
        T --> I[IconGenerator<br/>icon_generator.py]
        M --> S[Startup<br/>startup.py]
    end

    subgraph External
        API[Claude.ai API]
        REG[Windows Registry]
        TRAY[System Tray]
        TOAST[Windows Toast]
    end

    A <-->|HTTPS| API
    S <-->|Read/Write| REG
    T <-->|pystray| TRAY
    N <-->|winotify| TOAST
```

## Data Flow

```mermaid
sequenceDiagram
    participant Poll as Polling Thread
    participant API as ClaudeAPIClient
    participant Claude as claude.ai
    participant Notify as NotificationManager
    participant Tray as TrayIconManager
    participant Icon as IconGenerator

    Poll->>API: get_usage()
    API->>Claude: GET /api/organizations/{id}/usage
    Claude-->>API: JSON response
    API-->>Poll: UsageData

    Poll->>Notify: check_and_notify(usage)
    Notify-->>Notify: Compare against thresholds
    opt Threshold crossed
        Notify->>Notify: Send toast notification
    end

    Poll->>Tray: update_usage(usage)
    Tray->>Icon: create_icon(percentage, color)
    Icon-->>Tray: PIL Image
    Tray-->>Tray: Update icon + tooltip
```

## Threading Model

```mermaid
stateDiagram-v2
    [*] --> MainThread: Application Start

    state MainThread {
        [*] --> Init: Load config
        Init --> Setup: Check first run
        Setup --> StartPoll: Create components
        StartPoll --> TrayLoop: Start polling thread
        TrayLoop --> TrayLoop: pystray event loop (blocking)
        TrayLoop --> Shutdown: Exit clicked
    }

    state PollingThread {
        [*] --> InitialPoll
        InitialPoll --> Sleep
        Sleep --> Poll: Interval elapsed
        Poll --> Sleep: Success
        Poll --> Backoff: Error
        Backoff --> Sleep: Increased interval
        Sleep --> [*]: running=False
    }

    MainThread --> PollingThread: spawn daemon thread
    Shutdown --> [*]: Join threads
```

## Error Handling & Retry Logic

```mermaid
flowchart TD
    POLL[Poll API] --> CHECK{Response?}

    CHECK -->|200 OK| SUCCESS[Update display]
    SUCCESS --> RESET[Reset backoff]
    RESET --> SLEEP[Sleep base interval<br/>300s default]

    CHECK -->|401/403| AUTH[AuthenticationError]
    AUTH --> AUTH_STATE[Set auth_expired state]
    AUTH_STATE --> AUTH_SLEEP[Sleep 1 hour]

    CHECK -->|429| RATE[RateLimitError]
    RATE --> RATE_STATE[Set rate_limited state]
    RATE_STATE --> RATE_SLEEP[Sleep 2 minutes]

    CHECK -->|Network Error| NET[NetworkError]
    NET --> NET_STATE[Set network_error state]
    NET_STATE --> BACKOFF[Exponential backoff]
    BACKOFF --> BACKOFF_SLEEP[Sleep min(base × 2^n, 30min)]

    SLEEP --> POLL
    AUTH_SLEEP --> POLL
    RATE_SLEEP --> POLL
    BACKOFF_SLEEP --> POLL
```

### Backoff Strategy

| Error Type | Sleep Duration | Notes |
|------------|---------------|-------|
| Success | 300s (configurable) | Base polling interval |
| Auth Error (401/403) | 3600s (1 hour) | Cookie likely expired |
| Rate Limit (429) | 120s (2 min) | Respects Retry-After header |
| Network Error | 300s → 600s → 1200s → 1800s | Exponential, max 30 min |

## API Response Structure

```
GET https://claude.ai/api/organizations/{org_id}/usage
```

```json
{
  "five_hour": {
    "utilization": 47.0,
    "resets_at": "2025-12-01T07:00:00.171939+00:00"
  },
  "seven_day": {
    "utilization": 25.0,
    "resets_at": "2025-12-02T00:00:00.171962+00:00"
  },
  "seven_day_oauth_apps": {
    "utilization": 0.0,
    "resets_at": null
  },
  "seven_day_opus": null,
  "seven_day_sonnet": {
    "utilization": 1.0,
    "resets_at": "2025-12-02T04:00:00+00:00"
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `five_hour.utilization` | Current 5-hour rolling window usage (0-100%) |
| `five_hour.resets_at` | When the 5-hour window resets (ISO 8601) |
| `seven_day.utilization` | Current weekly usage (0-100%) |
| `seven_day.resets_at` | When the weekly window resets |

The tray icon displays **whichever is higher** (5-hour or weekly). Both values are shown in the tooltip.

## Icon Color States

```mermaid
stateDiagram-v2
    [*] --> Gray: Loading

    Gray --> Green: 0-49%
    Gray --> Yellow: 50-74%
    Gray --> Orange: 75-89%
    Gray --> Red: 90-100%

    Green --> Yellow: Usage increased
    Yellow --> Orange: Usage increased
    Orange --> Red: Usage increased

    Red --> Orange: Usage decreased
    Orange --> Yellow: Usage decreased
    Yellow --> Green: Usage decreased

    Green --> Blue: Auth error
    Yellow --> Blue: Auth error
    Orange --> Blue: Auth error
    Red --> Blue: Auth error

    Green --> GrayError: Network error
    Yellow --> GrayError: Network error
    Orange --> GrayError: Network error
    Red --> GrayError: Network error

    Blue --> Green: Recovered
    GrayError --> Green: Recovered

    state GrayError <<choice>>
```

| Color | Icon | Meaning |
|-------|------|---------|
| Green | Gauge | 0-49% usage |
| Yellow | Gauge | 50-74% usage |
| Orange | Gauge | 75-89% usage |
| Red | Gauge | 90-100% usage |
| Blue | `!` | Authentication error |
| Gray | `?` | Network/connection error |
| Gray | `...` | Loading/initializing |

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Config | `%LOCALAPPDATA%\ClaudeMonitor\config.json` | User settings |
| Logs | `%LOCALAPPDATA%\ClaudeMonitor\logs\claude_monitor.log` | Application logs |
| Portable | `./config.json` (next to exe) | Optional portable mode |

Log files rotate at 5MB with 3 backups retained.

## Configuration

```json
{
  "organization_id": "uuid",
  "session_cookie": "sk-ant-...",
  "poll_interval_seconds": 300,
  "notification_thresholds": [50, 75, 90],
  "start_with_windows": false,
  "debug_mode": false
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `poll_interval_seconds` | 300 | How often to check usage (5 min) |
| `notification_thresholds` | [50, 75, 90] | Usage % levels that trigger notifications |
| `start_with_windows` | false | Add to Windows startup registry |
| `debug_mode` | false | Enable verbose console logging |

---

## Development

### Prerequisites

- Python 3.11+
- Windows 10/11
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/claudometer.git
cd claudometer

# Install dependencies
uv sync
```

### Running Locally

```bash
# Run from source
uv run python -m src.main

# Or use the installed command
uv run claudometer
```

### Building

```bash
# Build standalone exe
uv run python build.py
```

Output: `dist/ClaudeMonitor.exe` (~15MB standalone executable)

### Deploying

```bash
# Build, install, and run in one command
uv run python deploy.py
```

This will:

1. Build the exe via PyInstaller
2. Kill any running instance
3. Copy exe to `%LOCALAPPDATA%\Claudometer\`
4. Add to Windows startup registry
5. Launch the app detached

Use this for quick iteration during development.

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_api_client.py -v
```

### Project Structure

```
claudometer/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point, orchestration
│   ├── api_client.py     # Claude API communication
│   ├── config.py         # Configuration management
│   ├── notifications.py  # Windows toast notifications
│   ├── tray_icon.py      # System tray integration
│   ├── icon_generator.py # Dynamic icon creation
│   ├── startup.py        # Windows startup registry
│   └── utils.py          # Logging, helpers
├── tests/
│   ├── conftest.py       # Shared fixtures
│   ├── test_api_client.py
│   ├── test_config.py
│   └── test_notifications.py
├── docs/
│   └── ARCHITECTURE.md   # This file
├── build.py              # PyInstaller build script
├── build.spec            # PyInstaller configuration
├── deploy.py             # Build + install + run
├── pyproject.toml        # Project metadata
└── config.example.json   # Example configuration
```
