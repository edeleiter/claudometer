# Troubleshooting Guide

## Common Issues

### Authentication Error (Blue icon with "!")

**Symptoms:**
- Tray icon shows blue with "!" symbol
- Tooltip says "Auth Error: Cookie expired"
- You receive a notification about authentication failure

**Cause:** Your session cookie has expired or is invalid.

**Solution:**
1. Log in to <https://claude.ai> in your browser
2. Get a fresh session cookie (see README for instructions)
3. Open your config file (right-click tray icon > Open Config)
4. Update the `session_cookie` value
5. Save the file and restart the application

---

### Connection Error (Gray icon with "?")

**Symptoms:**
- Tray icon shows gray with "?" symbol
- Tooltip says "Connection Error"

**Cause:** Cannot reach claude.ai servers.

**Solution:**
1. Check your internet connection
2. Verify <https://claude.ai> is accessible in your browser
3. Check if a VPN or proxy might be blocking the connection
4. Check if your firewall is blocking the application

The app will automatically retry and recover when the connection is restored.

---

### Tray Icon Not Visible

**Symptoms:**
- App seems to be running but no icon in system tray
- Icon appears briefly then disappears

**Cause:** Windows hides overflow icons by default.

**Solution:**
1. Click the `^` arrow in the system tray to show hidden icons
2. Look for the Claude Monitor icon there
3. To make it always visible:
   - Right-click the taskbar > Taskbar settings
   - Click "Other system tray icons"
   - Find "ClaudeMonitor" and toggle it on

---

### Windows SmartScreen Warning

**Symptoms:**
- Windows shows "Windows protected your PC" warning
- App won't run without clicking through warning

**Cause:** The executable is not code-signed (this is normal for open-source/personal projects).

**Solution:**
1. Click "More info" on the SmartScreen dialog
2. Click "Run anyway"

This is a false positive - the app is safe. The source code is fully open for review.

---

### Notifications Not Appearing

**Symptoms:**
- Usage passes threshold but no notification appears
- Notifications worked before but stopped

**Cause:** Windows notification settings may be blocking them.

**Solution:**
1. Open Windows Settings
2. Go to System > Notifications
3. Ensure notifications are turned on
4. Scroll down and find "Claude Usage Monitor"
5. Make sure it's enabled

Also check:
- Focus Assist is not blocking notifications
- Do Not Disturb is not enabled

---

### High CPU or Memory Usage

**Symptoms:**
- App using more resources than expected
- System feels sluggish

**Cause:** This should not happen under normal operation.

**Solution:**
1. Check the log file for errors (see below)
2. Try restarting the application
3. If the issue persists, report it with your log file

---

### App Crashes on Startup

**Symptoms:**
- App window briefly appears then closes
- No tray icon appears

**Cause:** Could be missing dependencies or corrupted config.

**Solution:**
1. Try deleting the config file and letting it regenerate:
   - Delete `%LOCALAPPDATA%\ClaudeMonitor\config.json`
   - Run the app again
2. If running from source, ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
3. Check the log file for error details

---

## Log Files

Log files are stored at:
```
%LOCALAPPDATA%\ClaudeMonitor\logs\claude_monitor.log
```

To find this folder:
1. Press `Win + R`
2. Type `%LOCALAPPDATA%\ClaudeMonitor\logs`
3. Press Enter

### Enable Debug Logging

For more detailed logs:
1. Open your config file
2. Set `"debug_mode": true`
3. Restart the application

Debug logs will include detailed API responses and internal state.

---

## Config File Location

The config file is at:
```
%LOCALAPPDATA%\ClaudeMonitor\config.json
```

If running in portable mode (config.json next to the exe), that file is used instead.

---

## Getting Help

If you're still having issues:

1. Check existing [Issues](https://github.com/yourusername/claude-usage-monitor/issues)
2. Create a new issue with:
   - Windows version (e.g., Windows 11 23H2)
   - App version
   - Log file contents (remove your session cookie!)
   - Steps to reproduce the issue

---

## Resetting to Defaults

To completely reset the app:

1. Close the application
2. Delete the config folder:
   - Press `Win + R`
   - Type `%LOCALAPPDATA%\ClaudeMonitor`
   - Press Enter
   - Delete the entire folder
3. Run the application again (fresh setup)
