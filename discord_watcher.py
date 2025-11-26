import subprocess
import time
import json
import threading
import sys
from playwright.sync_api import sync_playwright
from discord_utils import MESSAGE_SELECTOR, clean_discord_text, get_message_info, get_last_message_info

#DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1360311340429742271" # Product-Links
#DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1368083628935876709" # Charmeleon-General
#DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1373557451466604624" # Amazon-CA
DISCORD_CHANNEL_URL = "https://discord.com/channels/1359582105591353376/1360311340429742271" # Product-Links 

# Extract channel name from URL (fallback if we can't get it from page)
def get_channel_name_from_url(url):
    """Extract channel name from Discord URL or use a default."""
    # Try to get from comment in URL
    if "Amazon-CA" in url or "1373557451466604624" in url:
        return "Amazon-CA"
    elif "Product-Links" in url or "1360311340429742271" in url:
        return "Product-Links"
    elif "Charmeleon-General" in url or "1368083628935876709" in url:
        return "Charmeleon-General"
    return "Discord"

def get_server_name(page):
    """Extract Discord server/guild name from the page title."""
    try:
        # Discord page title format: "Discord | #channel-name | Server Name"
        # or "(unread) Discord | #channel-name | Server Name"
        title = page.title()
        if title and "Discord" in title:
            # Split by "|" and get the last part (server name)
            parts = title.split("|")
            if len(parts) >= 3:
                # Format: "Discord | #channel | Server Name"
                server_name = parts[-1].strip()
                if server_name and len(server_name) < 100:
                    return server_name
            elif len(parts) == 2:
                # Format: "Discord | #channel" (no server name in title)
                pass
    except:
        pass
    
    return None


def format_pushover_message(msg_info, server_name, channel_name):
    """Format message for Pushover with nice formatting."""
    embed_title = clean_discord_text(msg_info.get("embed_text", ""))
    url = msg_info.get("url", "").strip()
    message_text = clean_discord_text(msg_info.get("text", ""))
    
    # Build formatted message
    lines = []
    
    # Header - use server name if available, otherwise "Discord"
    server_display = server_name if server_name else "Discord"
    lines.append(f"Alert from {server_display} in {channel_name}")
    lines.append("")  # Empty line
    
    # Link title (if exists)
    if embed_title:
        lines.append(embed_title)
        lines.append("")  # Empty line
    
    # Link (if exists)
    if url:
        lines.append(f"Link: {url}")
        lines.append("")  # Empty line
    
    # Message text (if exists)
    if message_text:
        lines.append(f"Message: {message_text}")
    
    # Discord message link (if message ID exists)
    message_id = msg_info.get("id", "")
    if message_id:
        # Extract channel ID and message ID from the message ID format
        # Format: "chat-messages-{channel_id}-{message_id}"
        try:
            # Extract channel ID from DISCORD_CHANNEL_URL
            # URL format: https://discord.com/channels/{server_id}/{channel_id}
            url_parts = DISCORD_CHANNEL_URL.split("/")
            if len(url_parts) >= 6:
                server_id = url_parts[4]
                channel_id = url_parts[5]
                
                # Extract actual message ID from message_id string
                # Format: "chat-messages-{channel_id}-{actual_message_id}"
                msg_id_parts = message_id.split("-")
                if len(msg_id_parts) >= 4:
                    actual_message_id = "-".join(msg_id_parts[3:])  # Get everything after "chat-messages-{channel_id}-"
                    discord_message_url = f"https://discord.com/channels/{server_id}/{channel_id}/{actual_message_id}"
                    lines.append("")  # Empty line
                    lines.append(f"Discord Message: {discord_message_url}")
        except:
            pass
    
    return "\n".join(lines)

def send_pushover_alert(message):
    """Send a Pushover notification via curl."""
    print(f"📱 [API CALL] Would send: {message}")
    
    curl_cmd = [
        "curl", "--location", "https://api.pushover.net/1/messages.json",
        "--header", "Content-Type: application/json",
        "--data", json.dumps({
            "token": "a79nbse49c1qhzi3be8wuay79ma8u7",
            "user": "uhk4gq35qtas36ynab7exwx119ekup",
            "message": message,
            "priority": 2,
            "sound": "persistent",
            "retry": 30,
            "expire": 1800
        })
    ]
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Pushover notification sent successfully")
    else:
        print(f"✗ Failed to send notification: {result.stderr}")

def reset_monitoring(page):
    """Reset monitoring by reloading page and showing last 5 messages again."""
    print("\n" + "=" * 60)
    print("🔄 Resetting monitoring...")
    print("=" * 60)
    
    # Reload the page
    page.reload()
    time.sleep(3)
    
    # Wait for messages to load
    try:
        page.wait_for_selector(MESSAGE_SELECTOR, timeout=15000)
    except Exception as e:
        print(f"✗ Error: Could not find messages. {e}")
        return None
    
    # Get all messages and display last 5
    all_msgs = page.query_selector_all(MESSAGE_SELECTOR)
    if not all_msgs:
        print("ERROR: No messages found")
        return None
    
    print(f"\n==={'='*60}===")
    print(f"📋 Last 5 messages in channel:")
    print(f"{'='*60}\n")
    
    # Get last 5 messages (oldest first, newest last)
    last_5_msgs = all_msgs[-5:] if len(all_msgs) >= 5 else all_msgs
    
    for i, msg_elem in enumerate(last_5_msgs, 1):
        try:
            msg_info = get_message_info(msg_elem)
            
            # Clean the text to remove Discord UI elements
            cleaned_text = clean_discord_text(msg_info["text"])
            cleaned_embed = clean_discord_text(msg_info.get("embed_text", ""))
            
            # Debug: print what we extracted
            if msg_info["has_embed"]:
                print(f"DEBUG msg #{len(last_5_msgs) - i + 1}: has_embed=True, embed_text='{msg_info.get('embed_text', '')[:50]}', cleaned_embed='{cleaned_embed[:50]}'")
            
            # Determine what alert would be sent (same logic as monitoring loop)
            # For embeds, always prefer embed_text (title) over regular text
            if msg_info["has_embed"] and cleaned_embed:
                alert_msg = cleaned_embed[:150] + ("..." if len(cleaned_embed) > 150 else "")
            elif cleaned_text:
                alert_msg = cleaned_text[:150] + ("..." if len(cleaned_text) > 150 else "")
            elif msg_info["has_image"] or msg_info["has_embed"]:
                alert_msg = "New image/embed message"
            else:
                alert_msg = "(No content)"
            
            # Reverse numbering: newest (last) = #1, oldest (first) = #5
            msg_num = len(last_5_msgs) - i + 1
            
            # Compact display
            latest_label = " (latest)" if msg_num == 1 else ""
            # Display message
            print(f"#{msg_num}{latest_label} {'🖼️' if msg_info['has_image'] else ''}{'🔗' if msg_info['has_embed'] else ''} {alert_msg}")
            # Show URL on separate line to avoid truncation
            if msg_info.get("url"):
                print(f"    URL: {msg_info['url']}")
            
            # Add separator between messages (not after the last one)
            if i < len(last_5_msgs):
                print(f"{'='*60}")
        except Exception as e:
            print(f"Message #{i}: Error parsing message - {e}")
            # Add separator between messages (not after the last one)
            if i < len(last_5_msgs):
                print(f"{'='*60}")
    
    print(f"==={'='*60}===")
    
    # Get the newest message for tracking
    last_msg = get_last_message_info(page)
    if not last_msg:
        return None
    
    last_seen_id = last_msg["id"]
    print(f"\n✓ Monitoring reset! Now monitoring from message ID: {last_seen_id}")
    
    # Send API call for the latest message (for testing on slow channels)
    print("Sending test API call for latest message...")
    try:
        server_name = get_server_name(page)
        channel_name = get_channel_name_from_url(DISCORD_CHANNEL_URL)
        msg_for_push = format_pushover_message(last_msg, server_name, channel_name)
        
        if last_msg.get("url"):
            print(f"📎 URL: {last_msg['url']}")
        else:
            print("⚠ No URL found in message")
        
        send_pushover_alert(msg_for_push)
    except Exception as e:
        print(f"⚠ Error sending test API call: {e}")
    
    print("Watching for new messages... (Press ENTER to reset again)\n")
    
    return last_seen_id

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./discord_profile",
            headless=False
        )
        page = browser.new_page()
        page.goto("https://discord.com/login")
        
        print("Log in manually, then press ENTER to continue...")
        input()
        
        print(f"Navigating to channel...")
        page.goto(DISCORD_CHANNEL_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        # Wait for messages to load
        try:
            page.wait_for_selector(MESSAGE_SELECTOR, timeout=15000)
        except Exception as e:
            print(f"✗ Error: Could not find messages. {e}")
            return
        
        # Get all messages and display last 5
        all_msgs = page.query_selector_all(MESSAGE_SELECTOR)
        if not all_msgs:
            print("ERROR: No messages found")
            return
        
        print(f"\n==={'='*60}===")
        print(f"📋 Last 5 messages in channel:")
        print(f"{'='*60}\n")
        
        # Get last 5 messages (oldest first, newest last)
        last_5_msgs = all_msgs[-5:] if len(all_msgs) >= 5 else all_msgs
        
        for i, msg_elem in enumerate(last_5_msgs, 1):
            try:
                msg_info = get_message_info(msg_elem)
                
                # Clean the text to remove Discord UI elements
                cleaned_text = clean_discord_text(msg_info["text"])
                cleaned_embed = clean_discord_text(msg_info.get("embed_text", ""))
                
                # Determine what alert would be sent (same logic as monitoring loop)
                # For embeds, always prefer embed_text (title) over regular text
                if msg_info["has_embed"] and cleaned_embed:
                    alert_msg = cleaned_embed[:150] + ("..." if len(cleaned_embed) > 150 else "")
                elif cleaned_text:
                    alert_msg = cleaned_text[:150] + ("..." if len(cleaned_text) > 150 else "")
                elif msg_info["has_image"] or msg_info["has_embed"]:
                    alert_msg = "New image/embed message"
                else:
                    alert_msg = "(No content)"
                
                # Reverse numbering: newest (last) = #1, oldest (first) = #5
                msg_num = len(last_5_msgs) - i + 1
                
                # Compact display
                latest_label = " (latest)" if msg_num == 1 else ""
                url_display = ""
                if msg_info.get("url"):
                    # Shorten URL for display (show first 50 chars)
                    url_short = msg_info["url"][:50] + ("..." if len(msg_info["url"]) > 50 else "")
                    url_display = f" | URL: {url_short}"
                print(f"#{msg_num}{latest_label} {'🖼️' if msg_info['has_image'] else ''}{'🔗' if msg_info['has_embed'] else ''} {alert_msg}{url_display}")
                
                # Add separator between messages (not after the last one)
                if i < len(last_5_msgs):
                    print(f"{'='*60}")
            except Exception as e:
                print(f"#{i}: Error - {e}")
                # Add separator between messages (not after the last one)
                if i < len(last_5_msgs):
                    print(f"{'='*60}")
        
        print(f"==={'='*60}===")
        
        # Get the newest message for tracking
        last_msg = get_last_message_info(page)
        last_seen_id = last_msg["id"]
        
        print(f"\n✓ Connected! Monitoring from message ID: {last_seen_id}")
        
        # Send API call for the latest message (for testing on slow channels)
        print("Sending test API call for latest message...")
        try:
            server_name = get_server_name(page)
            channel_name = get_channel_name_from_url(DISCORD_CHANNEL_URL)
            msg_for_push = format_pushover_message(last_msg, server_name, channel_name)
            
            if last_msg.get("url"):
                print(f"📎 URL: {last_msg['url']}")
            else:
                print("⚠ No URL found in message")
            
            send_pushover_alert(msg_for_push)
        except Exception as e:
            print(f"⚠ Error sending test API call: {e}")
        
        print("Watching for new messages... (Press ENTER to reset monitoring)\n")
        
        # Flag to track if reset was requested
        reset_requested = threading.Event()
        
        # Thread to listen for ENTER keypress
        def input_listener():
            while True:
                try:
                    input()  # Wait for ENTER
                    reset_requested.set()
                except:
                    break
        
        input_thread = threading.Thread(target=input_listener, daemon=True)
        input_thread.start()
        
        while True:
            try:
                # Check if reset was requested
                if reset_requested.is_set():
                    reset_requested.clear()
                    new_last_seen_id = reset_monitoring(page)
                    if new_last_seen_id:
                        last_seen_id = new_last_seen_id
                    continue
                
                current = get_last_message_info(page)
                if not current:
                    time.sleep(2)
                    continue

                # new message row detected by ID change
                if current["id"] != last_seen_id:
                    last_seen_id = current["id"]

                    # Only alert if:
                    #  - it has text, OR
                    #  - it has an image, OR
                    #  - it has an embed (link card / bot message / forwarded message)
                    if current["text"] or current["has_image"] or current["has_embed"]:
                        # Clean the text to remove Discord UI elements
                        cleaned_text = clean_discord_text(current["text"])
                        cleaned_embed = clean_discord_text(current.get("embed_text", ""))
                        
                        print("\n" + "=" * 60)
                        print("🔔 NEW MESSAGE DETECTED!")
                        icons = ""
                        if current["has_image"]:
                            icons += "🖼️ "
                        if current["has_embed"]:
                            icons += "🔗"
                        if icons:
                            print(f"{icons}")
                        print("=" * 60)

                        # Format message for Pushover
                        server_name = get_server_name(page)
                        channel_name = get_channel_name_from_url(DISCORD_CHANNEL_URL)
                        msg_for_push = format_pushover_message(current, server_name, channel_name)
                        
                        if current.get("url"):
                            print(f"📎 URL: {current['url']}")
                        else:
                            print("⚠ No URL found in message")
                        
                        send_pushover_alert(msg_for_push)

                time.sleep(2)
            except KeyboardInterrupt:
                print("\n✓ Stopping watcher...")
                break
            except Exception as e:
                print(f"✗ Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    main()

