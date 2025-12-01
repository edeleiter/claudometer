# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-30

### Added

- Initial release
- System tray icon with color-coded usage display (green/yellow/orange/red)
- Toast notifications at configurable thresholds (default: 50%, 75%, 90%)
- Tooltip showing 5-hour and weekly usage with reset times
- Context menu with Refresh, Open Claude, Open Config, and Exit options
- Automatic polling with configurable interval (default: 5 minutes)
- First-run setup wizard
- Configuration via JSON file
- Comprehensive error handling for auth, network, and rate limit errors
- Logging with rotation
- PyInstaller build support for standalone executable
