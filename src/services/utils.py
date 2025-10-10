import re

def remove_timestamps_from_html(html_content):
    """
    Removes timestamp tags from an HTML string.

    Args:
        html_content: The HTML content to process.

    Returns:
        The HTML content with timestamp tags removed.
    """
    if not html_content:
        return ""
    # This pattern is robust and handles other HTML attributes within the <font> tag.
    timestamp_pattern = re.compile(r'\s*<font[^>]*color=["\']?#ADD8E6["\']?[^>]*>\[.*?\]</font>\s*', re.IGNORECASE)
    return timestamp_pattern.sub(' ', html_content).strip()