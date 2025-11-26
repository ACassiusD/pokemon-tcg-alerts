# pokemon-tcg-alerts
A collection of programs to alert the user about Pokemon TCG Deals

## Discord Channel Watcher

A script that monitors a specific Discord channel and sends Pushover notifications when new messages appear.

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. Edit `discord_watcher.py` and replace `DISCORD_CHANNEL_URL` with your target channel URL:
   ```python
   DISCORD_CHANNEL_URL = "https://discord.com/channels/YOUR_SERVER_ID/YOUR_CHANNEL_ID"
   ```

3. Run the script:
   ```bash
   python discord_watcher.py
   ```

4. Log in to Discord manually in the browser window that opens, then press ENTER in the terminal to continue.

5. The script will watch for new messages and send Pushover alerts automatically.

### Notes

- The script uses a persistent browser session stored in `./discord_profile`, so you only need to log in once.
- The browser runs in non-headless mode so you can see what's happening.
- Press Ctrl+C to stop the watcher.
