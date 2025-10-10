import re

def remove_timestamps_from_html(html_content):
    """
    Removes timestamp tags and raw timestamps (e.g., [00:12:34.5] or [01:23]) from an HTML string,
    and cleans up surrounding whitespace.
    """
    if not html_content:
        return ""

    # Remove styled timestamps, replacing with a space to preserve word separation.
    font_timestamp_pattern = re.compile(r'\s*<font[^>]*color=["\']?#ADD8E6["\']?[^>]*>\[.*?\]</font>\s*', re.IGNORECASE)
    content = font_timestamp_pattern.sub(' ', html_content)

    # Remove raw timestamps, also replacing with a space.
    raw_timestamp_pattern = re.compile(r'\s*\[\d{1,2}:\d{2}(:\d{2})?(\.\d{1,2})?\]\s*')
    content = raw_timestamp_pattern.sub(' ', content)

    # Clean up whitespace issues that may result from the removal.
    # Collapse multiple spaces into a single space.
    content = re.sub(r'\s+', ' ', content)
    # Remove space that might be left after an opening <p> tag.
    content = re.sub(r'<p>\s+', '<p>', content)
    # Remove space that might be left before a closing </p> tag.
    content = re.sub(r'\s+</p>', '</p>', content)

    return content.strip()