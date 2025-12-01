# Claude Usage Monitor

A Windows 11 system tray application that monitors your Claude.ai usage limits and alerts you before hitting rate limits.

## Features

- **Live usage monitoring** - See your current 5-hour and weekly usage at a glance
- **Color-coded tray icon** - Green/Yellow/Orange/Red based on usage level
- **Toast notifications** - Get alerted at 50%, 75%, and 90% thresholds
- **Configurable** - Adjust polling interval and notification thresholds
- **Lightweight** - Runs quietly in the background

## Quick Start

### From Executable

1. Download `ClaudeMonitor.exe` from Releases
2. Run the application
3. On first run, a config file will be created and opened
4. Add your credentials (see below)
5. Run the application again

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-usage-monitor.git
cd claude-usage-monitor

# Install dependencies and run (using uv)
uv run python -m src.main

# Or install first, then run
uv sync
uv run claude-monitor
```

## Getting Your Credentials

You'll need two pieces of information from Claude.ai:

### Organization ID

1. Go to <https://claude.ai/settings/usage>
2. Look at the URL in your browser - it will look like:
   `https://claude.ai/settings/organizations/YOUR-ORG-ID/usage`
3. Copy the UUID portion (e.g., `86104bd5-8f36-4a85-ad31-131184094d75`)

### Session Cookie

1. Open <https://claude.ai> in Chrome or Edge
2. Press `F12` to open Developer Tools
3. Go to the **Application** tab
4. In the left sidebar, expand **Cookies** > **https://claude.ai**
5. Find `sessionKey` in the list
6. Double-click the **Value** column and copy the entire value

> **Note:** Session cookies expire periodically (typically after a few weeks). You'll need to update your cookie when the app shows an authentication error.

## Configuration

The config file is located at:
- `%LOCALAPPDATA%\ClaudeMonitor\config.json`

Or if running in portable mode, `config.json` next to the executable.

### Config Options

| Option | Description | Default |
|--------|-------------|---------|
| `organization_id` | Your Claude.ai organization ID | (required) |
| `session_cookie` | Your sessionKey cookie value | (required) |
| `poll_interval_seconds` | How often to check usage (in seconds) | 300 (5 min) |
| `notification_thresholds` | Usage percentages to alert at | [50, 75, 90] |
| `start_with_windows` | Auto-start on Windows login | false |
| `debug_mode` | Enable verbose logging | false |

### Example Config

```json
{
  "organization_id": "86104bd5-8f36-4a85-ad31-131184094d75",
  "session_cookie": "sk-ant-...",
  "poll_interval_seconds": 300,
  "notification_thresholds": [50, 75, 90],
  "start_with_windows": false,
  "debug_mode": false
}
```

## Tray Icon Guide

| Icon Color | Usage Level | Meaning |
|------------|-------------|---------|
| Green | 0-49% | Normal usage |
| Yellow | 50-74% | Moderate usage |
| Orange | 75-89% | High usage |
| Red | 90-100% | Critical - near limit |
| Blue (!) | - | Authentication error |
| Gray (?) | - | Connection error |

## Tray Menu Options

- **Refresh Now** - Immediately check usage
- **Open claude.ai** - Open Claude in your browser
- **Open Config** - Edit the configuration file
- **Exit** - Close the application

## Building from Source

### Requirements

- Python 3.11+
- Windows 10/11
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Build Steps

```bash
# Install dev dependencies and build
uv sync --all-extras
uv run python build.py

# Output will be in dist/ClaudeMonitor.exe
```

### Running Tests

```bash
uv run pytest tests/ -v
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## How It Works

The app periodically calls the Claude.ai usage API:
```
GET https://claude.ai/api/organizations/{org_id}/usage
```

This returns your current usage for:
- **5-hour rolling window** - Resets continuously
- **Weekly usage** - Resets at the start of each week

The app displays the higher of the two values on the icon, with both shown in the tooltip.

## Privacy

- Your credentials are stored locally in the config file
- The app only communicates with claude.ai
- No data is sent to any third parties
- No analytics or telemetry

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
