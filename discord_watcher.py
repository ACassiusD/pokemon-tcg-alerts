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
DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1373557386475733032"

# CSS selector to find message list items (entire message containers)
# Using the list item container ensures we capture ALL content including embeds, links, images
# This is more reliable than just messageContent which might miss embed content
MESSAGE_LIST_ITEM_SELECTOR = 'li[id^="chat-messages"]'

# Alternative: message content selector (fallback)
# This finds just the text content divs
MESSAGE_CONTENT_SELECTOR = '[class*="messageContent"]'

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

def get_message_text(elem):
    """
    Extract all text content from a message element, including embeds and links.
    
    For messages with embeds/links, Discord structures them differently:
    - Regular messages: text is in messageContent div
    - Bot messages with embeds: content might be in embed containers
    - We need to check both to capture everything
    
    Args:
        elem: Playwright element handle (should be a message list item)
    
    Returns:
        str: Full text content of the message, or None if empty/invalid
    """
    try:
        # Strategy: Get text from multiple sources and combine them
        
        # 1. Try to get text from messageContent div (regular message text)
        content_text = ""
        try:
            content_elem = elem.query_selector(MESSAGE_CONTENT_SELECTOR)
            if content_elem:
                content_text = content_elem.inner_text().strip()
        except:
            pass
        
        # 2. Try to get text from embed containers (bot messages, rich embeds)
        embed_texts = []
        try:
            # Discord embeds can have various class names, try common patterns
            embed_selectors = [
                '[class*="embed"]',
                '[class*="Embed"]',
                '[class*="embedInner"]',
                '[class*="embedDescription"]',
                '[class*="embedFields"]'
            ]
            for selector in embed_selectors:
                embed_elements = elem.query_selector_all(selector)
                for embed_elem in embed_elements:
                    embed_text = embed_elem.inner_text().strip()
                    if embed_text and embed_text not in embed_texts:
                        embed_texts.append(embed_text)
        except:
            pass
        
        # 3. If we found embed text but no content text, use the full element text
        # This handles cases where the message is entirely in an embed
        if embed_texts and not content_text:
            try:
                full_text = elem.inner_text().strip()
                # Filter out common Discord UI elements (timestamps, usernames, etc.)
                # These usually contain patterns like "Today at" or "Yesterday at"
                lines = full_text.split('\n')
                filtered_lines = []
                for line in lines:
                    line = line.strip()
                    # Skip lines that look like timestamps or metadata
                    if line and not any(skip in line.lower() for skip in ['today at', 'yesterday at', '—', 'edited']):
                        filtered_lines.append(line)
                if filtered_lines:
                    return '\n'.join(filtered_lines)
            except:
                pass
        
        # 4. Combine content text with embed text
        all_text_parts = [content_text] + embed_texts
        combined = '\n'.join([t for t in all_text_parts if t])
        
        return combined.strip() if combined.strip() else None
        
    except Exception:
        return None

def get_non_empty_messages(page):
    """
    Find all message elements on the page and filter out empty ones.
    
    Uses the full message list item container to capture ALL content including
    embeds, links, images, and rich content that might be missed by just
    looking at messageContent.
    
    Returns:
        list: List of tuples (element, text) for non-empty messages
    """
    # Try to find message list items first (full message containers)
    all_elements = page.query_selector_all(MESSAGE_LIST_ITEM_SELECTOR)
    
    # If we don't find any, fall back to message content selector
    if len(all_elements) == 0:
        all_elements = page.query_selector_all(MESSAGE_CONTENT_SELECTOR)
    
    # Filter out empty messages and extract full text including embeds
    non_empty_elements = []
    for elem in all_elements:
        text = get_message_text(elem)
        if text:  # Only include messages that have actual text content
            non_empty_elements.append((elem, text))
    
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
        # Try both selectors to be more robust
        try:
            page.wait_for_selector(MESSAGE_LIST_ITEM_SELECTOR, timeout=10000)
        except:
            try:
                page.wait_for_selector(MESSAGE_CONTENT_SELECTOR, timeout=5000)
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

