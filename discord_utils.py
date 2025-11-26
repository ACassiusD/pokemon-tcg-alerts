"""Utility functions for Discord message parsing and processing."""

# Discord message selector
MESSAGE_SELECTOR = '[id^="chat-messages-"]'   # each message row

def clean_discord_text(text):
    """Keep only the first 10 lines, URLs, and message text."""
    if not text:
        return ""
    
    lines = text.split('\n')
    
    # Filter out empty lines and collect non-empty lines
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # Keep first 10 lines
    kept_lines = non_empty_lines[:10]
    
    return '\n'.join(kept_lines).strip()

def debug_message_structure(msg_element):
    """Debug function to print all DOM structure and fields of a message element."""
    print("\n" + "=" * 80)
    print("DEBUG: Latest Message Structure")
    print("=" * 80)
    
    try:
        # Get message ID
        msg_id = msg_element.get_attribute("id") or ""
        print(f"\nMessage ID: {msg_id}")
        
        # Get all class names
        class_attr = msg_element.get_attribute("class") or ""
        print(f"\nMessage Classes: {class_attr}")
        
        # Get all direct child elements and their info
        print("\n--- Direct Child Elements ---")
        children = msg_element.query_selector_all(":scope > *")
        for i, child in enumerate(children[:20]):  # Limit to first 20
            child_tag = child.evaluate("el => el.tagName")
            child_id = child.get_attribute("id") or ""
            child_class = child.get_attribute("class") or ""
            child_text = child.inner_text()[:100] if child.inner_text() else ""  # First 100 chars
            print(f"  [{i}] <{child_tag}> id='{child_id}' class='{child_class[:50]}'")
            if child_text:
                print(f"      Text: {child_text[:80]}...")
        
        # Find and display author/username elements
        print("\n--- Author/Username Elements ---")
        author_selectors = [
            '[class*="username"]',
            '[class*="author"]',
            '[class*="messageAuthor"]',
            '[class*="header"]',
        ]
        for selector in author_selectors:
            elems = msg_element.query_selector_all(selector)
            for elem in elems:
                tag = elem.evaluate("el => el.tagName")
                class_attr = elem.get_attribute("class") or ""
                text = elem.inner_text().strip()
                print(f"  Found: <{tag}> class='{class_attr}' text='{text[:50]}'")
        
        # Find and display content elements
        print("\n--- Content Elements ---")
        content_selectors = [
            '[class*="messageContent"]',
            '[class*="message-content"]',
            '[class*="content"]',
            '[class*="markup"]',
        ]
        for selector in content_selectors:
            elems = msg_element.query_selector_all(selector)
            for elem in elems:
                tag = elem.evaluate("el => el.tagName")
                class_attr = elem.get_attribute("class") or ""
                text = elem.inner_text().strip()[:100]
                print(f"  Found: <{tag}> class='{class_attr}' text='{text}...'")
        
        # Find and display timestamp elements
        print("\n--- Timestamp Elements ---")
        timestamp_selectors = [
            '[class*="timestamp"]',
            '[class*="time"]',
            'time',
            '[datetime]',
        ]
        for selector in timestamp_selectors:
            elems = msg_element.query_selector_all(selector)
            for elem in elems:
                tag = elem.evaluate("el => el.tagName")
                class_attr = elem.get_attribute("class") or ""
                datetime_attr = elem.get_attribute("datetime") or ""
                text = elem.inner_text().strip()
                print(f"  Found: <{tag}> class='{class_attr}' datetime='{datetime_attr}' text='{text}'")
        
        # Find and display embed elements
        print("\n--- Embed Elements ---")
        embed_selectors = [
            '[class*="embed"]',
            '[class*="linkPreview"]',
        ]
        for selector in embed_selectors:
            elems = msg_element.query_selector_all(selector)
            for elem in elems:
                tag = elem.evaluate("el => el.tagName")
                class_attr = elem.get_attribute("class") or ""
                text = elem.inner_text().strip()[:100]
                print(f"  Found: <{tag}> class='{class_attr}' text='{text}...'")
                
                # Get embed children
                embed_children = elem.query_selector_all(":scope > *")
                for child in embed_children[:10]:
                    child_tag = child.evaluate("el => el.tagName")
                    child_class = child.get_attribute("class") or ""
                    child_text = child.inner_text().strip()[:50]
                    print(f"    -> <{child_tag}> class='{child_class[:40]}' text='{child_text}...'")
        
        # Get all links
        print("\n--- Links ---")
        links = msg_element.query_selector_all('a[href]')
        for i, link in enumerate(links[:10]):
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()[:50]
            print(f"  [{i}] href='{href[:60]}...' text='{text}'")
        
        # Get full inner text (first 500 chars)
        print("\n--- Full Inner Text (first 500 chars) ---")
        full_text = msg_element.inner_text()
        print(full_text[:500])
        
    except Exception as e:
        print(f"Error in debug: {e}")
    
    print("\n" + "=" * 80)
    print("END DEBUG")
    print("=" * 80 + "\n")

def get_message_info(msg_element):
    """Return info about a message element (text/img/embed flags + id)."""
    msg_id = msg_element.get_attribute("id") or ""

    # Extract message content from the content area, excluding username, roles, timestamps, etc.
    # Discord has separate elements for message content vs UI elements
    text = ""
    try:
        # Try to find the message content container (excludes author, timestamp, etc.)
        # Target the actual message text area, not the header/author section
        content_selectors = [
            '[class*="messageContent"]',
            '[class*="message-content"]',
            '[class*="markup"]',
            '[id*="message-content"]',
            'div[class*="message"] [class*="content"]:not([class*="header"]):not([class*="author"])',
            '[class*="message"] [class*="textContainer"]',
            '[class*="message"] [class*="text"]',
            # More specific: content area that's not in the header
            '[class*="message"] > div:not([class*="header"]) [class*="content"]',
        ]
        
        for selector in content_selectors:
            content_elem = msg_element.query_selector(selector)
            if content_elem:
                # Get text from content area, but make sure we're not including author/header
                # Try to find child elements that are actual content, not author info
                content_text = content_elem.inner_text().strip()
                
                # Check if this content area has author/username elements - if so, exclude them
                author_in_content = content_elem.query_selector('[class*="username"], [class*="author"], [class*="messageAuthor"]')
                if author_in_content:
                    # Get author text and remove it from content
                    author_text = author_in_content.inner_text().strip()
                    if author_text and content_text.startswith(author_text):
                        content_text = content_text[len(author_text):].strip()
                
                if content_text:
                    text = content_text
                    break
        
        # If no specific content area found, try to exclude known UI elements
        # by getting text from message but excluding author/timestamp areas
        if not text:
            # Get all text, but we'll try to filter out author area
            all_text = msg_element.inner_text().strip()
            
            # Try to find and exclude author/username area
            author_selectors = [
                '[class*="username"]',
                '[class*="author"]',
                '[class*="messageAuthor"]',
                '[class*="header"]',
            ]
            
            author_text = ""
            for selector in author_selectors:
                author_elem = msg_element.query_selector(selector)
                if author_elem:
                    author_text = author_elem.inner_text().strip()
                    if author_text:
                        # Remove author text from the beginning of all_text
                        if all_text.startswith(author_text):
                            text = all_text[len(author_text):].strip()
                        break
            
            # If still no text, fall back to inner_text but this is not ideal
            if not text:
                text = all_text
    except Exception as e:
        # Fallback to inner_text if extraction fails
        text = (msg_element.inner_text() or "").strip()

    # any images in the message (attachment or embed thumbnail)
    has_image = bool(msg_element.query_selector('img[src*="cdn.discordapp.com/attachments"], img[src*="media.discordapp.net"]'))

    # Enhanced embed detection - check multiple embed-related selectors
    embed_selectors = [
        '[class*="embedWrapper"]',
        '[class*="embedTitle"]',
        '[class*="embedDescription"]',
        '[class*="embed"]',
        '[class*="Embed"]',
        '[class*="embedInner"]',
        '[class*="embedField"]',
        '[class*="embedAuthor"]',
        '[class*="embedFooter"]',
        'div[class*="embed"]',
        'article[class*="embed"]',
    ]
    
    has_embed = False
    embed_text = ""
    
    # First, try to find embed wrapper
    embed_elem = None
    for selector in embed_selectors:
        embed_elem = msg_element.query_selector(selector)
        if embed_elem:
            has_embed = True
            break
    
    if embed_elem:
        # Extract embed title only (e.g., "Pokemon TCG Scarlet & Violet 10.5 Unova Mini Tin")
        try:
            # Based on debug output: <A> class='...embedTitleLink__623de...embedTitle__623de'
            # The title is in an anchor tag with embedTitleLink in the class
            title_elem = embed_elem.query_selector('a[class*="embedTitleLink"]')
            if not title_elem:
                # Fall back to any element with embedTitle in class (but not the div wrapper)
                title_elem = embed_elem.query_selector('a[class*="embedTitle"]')
            if not title_elem:
                # Last fallback: div with embedTitle, then get the anchor inside it
                title_div = embed_elem.query_selector('div[class*="embedTitle"]')
                if title_div:
                    title_elem = title_div.query_selector('a')
            
            if title_elem:
                title_text = title_elem.inner_text().strip()
                if title_text:
                    embed_text = title_text
        except Exception as e:
            pass
    
    # Also check for link previews and forwarded messages
    if not has_embed:
        # Check for link preview containers
        link_preview = msg_element.query_selector('[class*="linkPreview"], [class*="link-preview"], [class*="messageAttachment"]')
        if link_preview:
            has_embed = True
            try:
                # Get title only from link preview
                preview_title = link_preview.query_selector('[class*="title"], [class*="linkPreviewTitle"]')
                if preview_title:
                    title_text = preview_title.inner_text().strip()
                    if title_text:
                        embed_text = title_text
            except:
                pass
    
    # Extract URLs from the message using DOM selectors only (no regex)
    url = ""
    
    try:
        # Collect all potential URLs to find the longest/most complete one
        all_urls = []
        
        # Look for links in the message using DOM selectors
        links = msg_element.query_selector_all('a[href]')
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith("http"):
                all_urls.append(href)
        
        # Check embed elements more thoroughly
        if has_embed:
            embed_elem = msg_element.query_selector('[class*="embed"], [class*="linkPreview"], [class*="link-preview"]')
            if embed_elem:
                # Get all links in embed
                embed_links = embed_elem.query_selector_all('a[href]')
                for link in embed_links:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        all_urls.append(href)
                
                # Check embed title/author for links
                embed_title = embed_elem.query_selector('[class*="embedTitle"], [class*="embedAuthor"]')
                if embed_title:
                    title_link = embed_title.query_selector('a[href]')
                    if title_link:
                        href = title_link.get_attribute("href")
                        if href and href.startswith("http"):
                            all_urls.append(href)
                
                # Check embed fields and description for links
                embed_fields = embed_elem.query_selector_all('[class*="embedField"], [class*="embedDescription"]')
                for field in embed_fields:
                    # Only get links from DOM, not parse text
                    field_links = field.query_selector_all('a[href]')
                    for link in field_links:
                        href = link.get_attribute("href")
                        if href and href.startswith("http"):
                            all_urls.append(href)
        
        # Choose the longest URL (most complete) from all found URLs
        if all_urls:
            # Remove duplicates and sort by length (longest first)
            unique_urls = list(set(all_urls))
            unique_urls.sort(key=len, reverse=True)
            url = unique_urls[0]  # Use the longest/most complete URL
            
    except Exception as e:
        pass

    return {
        "id": msg_id,
        "text": text,
        "has_image": has_image,
        "has_embed": has_embed,
        "embed_text": embed_text,  # Store embed content separately
        "url": url,  # Store URL if found
    }

def get_last_message_info(page, debug=False):
    """Return info about the newest message (text/img/embed flags + id).
    
    Args:
        page: Playwright page object
        debug: If True, print debug info about message structure (default: False)
    """
    msgs = page.query_selector_all(MESSAGE_SELECTOR)
    if not msgs:
        return None

    last = msgs[-1]
    
    # Debug: print structure of latest message (only if requested)
    if debug:
        debug_message_structure(last)
    
    return get_message_info(last)

