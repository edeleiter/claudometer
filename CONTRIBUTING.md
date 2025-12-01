# Contributing

Thanks for your interest in contributing to Claude Usage Monitor!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/claude-usage-monitor.git
   cd claude-usage-monitor
   ```

2. Install dependencies with uv:
   ```bash
   uv sync --all-extras
   ```

3. Run the app in development:
   ```bash
   uv run python -m src.main
   ```

## Running Tests

```bash
uv run pytest tests/ -v
```

With coverage:
```bash
uv run pytest tests/ --cov=src --cov-report=html
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to public functions and classes

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests to ensure they pass
5. Commit your changes (`git commit -am 'Add new feature'`)
6. Push to the branch (`git push origin feature/my-feature`)
7. Create a Pull Request

## Reporting Bugs

Please open an issue with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Windows version
- Log file contents (remove sensitive data like cookies)

## Feature Requests

Open an issue describing:
- The feature you'd like
- Why it would be useful
- Any implementation ideas you have
