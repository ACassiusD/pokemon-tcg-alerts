"""
Discord Channel Watcher
Monitors a specific Discord channel for new messages and sends Pushover notifications.

SETUP INSTRUCTIONS:
1. Install dependencies: pip install playwright && playwright install
2. Update DISCORD_CHANNEL_URL below with your target channel URL
3. Run the script: python discord_watcher.py
4. Log in to Discord in the browser window that opens
5. Press ENTER in the terminal to start monitoring

The script saves your login session in ./discord_profile so you only need to log in once.
"""

import subprocess
import time
import json
from playwright.sync_api import sync_playwright

# ============================================================================
# CONFIGURATION - Update these values as needed
# ============================================================================

# Discord channel URL to monitor
# Format: https://discord.com/channels/SERVER_ID/CHANNEL_ID
# To get this: Right-click the channel in Discord > Copy Channel Link
DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1373557386475733032/1443044457590296688"

# CSS selector to find message content elements
# This selector finds all message content divs, including replies
# We use the LAST element found (newest message) to detect new messages
LAST_MESSAGE_SELECTOR = '[class*="messageContent"]'

# Pushover API credentials (keep these private!)
PUSHOVER_TOKEN = "a79nbse49c1qhzi3be8wuay79ma8u7"
PUSHOVER_USER = "uhk4gq35qtas36ynab7exwx119ekup"

# ============================================================================
# FUNCTIONS
# ============================================================================

def send_pushover_alert(message):
    """
    Send a Pushover notification with the detected message.
    
    Args:
        message (str): The message text to send in the notification
    
    The notification uses:
    - Priority 2: High priority (bypasses quiet hours)
    - Sound: "persistent" (repeating sound until acknowledged)
    - Retry: 30 seconds (retry every 30 seconds if not acknowledged)
    - Expire: 1800 seconds (30 minutes - stop retrying after this time)
    """
    curl_cmd = [
        "curl", "--location", "https://api.pushover.net/1/messages.json",
        "--header", "Content-Type: application/json",
        "--data", json.dumps({
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "message": message,
            "priority": 2,          # High priority (bypasses quiet hours)
            "sound": "persistent",   # Repeating sound until acknowledged
            "retry": 30,             # Retry every 30 seconds
            "expire": 1800            # Stop retrying after 30 minutes
        })
    ]
    
    # Execute the curl command and capture the result
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Pushover notification sent successfully")
    else:
        print(f"✗ Failed to send notification: {result.stderr}")

def get_non_empty_messages(page):
    """
    Find all message elements on the page and filter out empty ones.
    
    Returns:
        list: List of tuples (element, text) for non-empty messages
    """
    # Find all message content elements using our selector
    all_elements = page.query_selector_all(LAST_MESSAGE_SELECTOR)
    
    # Filter out empty messages (some elements might be empty divs or placeholders)
    non_empty_elements = []
    for elem in all_elements:
        try:
            text = elem.inner_text().strip()
            if text:  # Only include messages that have actual text content
                non_empty_elements.append((elem, text))
        except Exception:
            # If we can't read the element, skip it
            pass
    
    return non_empty_elements

def main():
    """
    Main function that sets up the browser, monitors the Discord channel,
    and sends notifications when new messages are detected.
    """
    # Launch browser with persistent context (saves login session)
    # headless=False means you can see the browser window
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./discord_profile",  # Saves login session here
            headless=False  # Set to True to hide browser window (not recommended for first login)
        )
        page = browser.new_page()
        
        # Step 1: Navigate to Discord login page
        print("Opening Discord login page...")
        page.goto("https://discord.com/login")
        
        # Step 2: Wait for user to log in manually
        # The browser window will stay open so you can log in
        print("\n" + "="*60)
        print("ACTION REQUIRED: Log in to Discord in the browser window")
        print("After logging in, come back here and press ENTER to continue")
        print("="*60)
        input()
        
        # Step 3: Navigate to the target channel
        print(f"\nNavigating to channel: {DISCORD_CHANNEL_URL}")
        page.goto(DISCORD_CHANNEL_URL)
        
        # Wait for page to fully load (Discord is a single-page app, needs time to render)
        print("Waiting for channel to load...")
        time.sleep(3)
        
        # Step 4: Wait for messages to appear on the page
        # This ensures the channel has loaded and messages are visible
        try:
            page.wait_for_selector(LAST_MESSAGE_SELECTOR, timeout=10000)
        except Exception as e:
            print(f"✗ Error: Could not find messages on the page. {e}")
            print("Make sure you're logged in and have access to this channel.")
            return
        
        # Step 5: Get the initial (current) newest message
        # We'll compare against this to detect when a NEW message appears
        try:
            non_empty_elements = get_non_empty_messages(page)
            
            if len(non_empty_elements) == 0:
                print("ERROR: No messages found in the channel")
                return
            
            # Get the LAST element (newest message) - this is what we'll watch
            # Discord messages are ordered oldest to newest, so [-1] is the newest
            last_seen_elem, last_seen = non_empty_elements[-1]
            
            print(f"\n✓ Connected successfully!")
            print(f"  Monitoring {len(non_empty_elements)} messages in channel")
            print(f"  Latest message: {last_seen[:80]}...")
            print("\n" + "="*60)
            print("WATCHING FOR NEW MESSAGES...")
            print("(Press Ctrl+C to stop)")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"ERROR: Failed to get initial message. {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 6: Main monitoring loop
        # Continuously check for new messages every 2 seconds
        while True:
            try:
                # Get all current messages from the page
                non_empty_elements = get_non_empty_messages(page)
                
                if len(non_empty_elements) == 0:
                    print("⚠ WARNING: No messages found (channel might have changed)")
                    time.sleep(2)
                    continue
                
                # Get the newest message (last element in the list)
                current = non_empty_elements[-1][1]  # [1] gets the text from (elem, text) tuple
                
                # Compare with the last message we saw
                # If they're different, a new message has appeared!
                if current != last_seen:
                    print(f"\n{'='*60}")
                    print(f"🔔 NEW MESSAGE DETECTED!")
                    print(f"Message: {current}")
                    print(f"{'='*60}")
                    
                    # Send the notification
                    send_pushover_alert(current)
                    
                    # Update our "last seen" message so we don't alert on it again
                    last_seen = current
                
                # Wait 2 seconds before checking again
                # Too frequent = more CPU usage, too slow = delayed notifications
                time.sleep(2)
                
            except KeyboardInterrupt:
                # User pressed Ctrl+C to stop
                print("\n✓ Stopping watcher...")
                break
            except Exception as e:
                # Handle any unexpected errors gracefully
                print(f"✗ Error in monitoring loop: {e}")
                print("Continuing to monitor...")
                time.sleep(5)  # Wait a bit longer before retrying after an error

if __name__ == "__main__":
    main()

