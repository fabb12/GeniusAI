import re
import time
import markdown
from bs4 import BeautifulSoup
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QTextDocument, QTextImageFormat

class HtmlManager:
    """
    Una classe per centralizzare la gestione dei contenuti HTML nelle aree di testo.
    """

    def __init__(self):
        self.image_metadata = {}

    def insert_image_with_metadata(self, text_edit, displayed_pixmap, width, height, video_path, timestamp, original_image=None):
        """
        Inserts an image as a document resource and stores its metadata.
        """
        image_name = f"frame_{int(time.time() * 1000)}"
        uri = QUrl(f"frame://{image_name}")

        image_to_store = original_image if original_image is not None else displayed_pixmap.toImage()
        self.image_metadata[image_name] = {
            'video_path': video_path,
            'timestamp': timestamp,
            'original_image': image_to_store
        }

        text_edit.document().addResource(QTextDocument.ResourceType.ImageResource, uri, displayed_pixmap.toImage())

        cursor = text_edit.textCursor()
        image_format = QTextImageFormat()
        image_format.setName(uri.toString())
        image_format.setWidth(width)
        image_format.setHeight(height)

        cursor.insertImage(image_format)
        text_edit.viewport().update()
        return image_name

    def update_image_resource(self, text_edit, image_name, new_image, new_width, new_height):
        uri = QUrl(f"frame://{image_name}")
        text_edit.document().addResource(QTextDocument.ResourceType.ImageResource, uri, new_image)

        if image_name in self.image_metadata:
            self.image_metadata[image_name]['original_image'] = new_image

        cursor = QTextCursor(text_edit.document())
        while not cursor.isNull() and not cursor.atEnd():
            cursor = text_edit.document().find(uri.toString(), cursor, QTextDocument.FindFlag.FindCaseSensitively)
            if not cursor.isNull():
                char_format = cursor.charFormat()
                if char_format.isImageFormat():
                    image_format = char_format.toImageFormat()
                    if image_format.name() == uri.toString():
                        image_format.setWidth(new_width)
                        image_format.setHeight(new_height)
                        temp_cursor = QTextCursor(cursor)
                        temp_cursor.setPosition(cursor.selectionStart())
                        temp_cursor.setPosition(cursor.selectionEnd(), QTextCursor.MoveMode.KeepAnchor)
                        temp_cursor.setCharFormat(image_format)

        text_edit.document().adjustSize()
        text_edit.viewport().update()

    @staticmethod
    def markdown_to_html(markdown_text):
        """
        Converte una stringa Markdown in HTML.
        """
        return markdown.markdown(markdown_text, extensions=['fenced_code', 'tables'])

    @staticmethod
    def remove_inline_styles(html_content):
        """
        Rimuove tutti gli attributi 'style' inline dall'HTML.
        """
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all(True):
            if 'style' in tag.attrs:
                del tag['style']
        if soup.body:
            return soup.body.decode_contents()
        return str(soup)

    @staticmethod
    def remove_timestamps_from_html(html_content):
        """
        Rimuove i timestamp dall'HTML.
        """
        if not html_content:
            return ""

        font_timestamp_pattern = re.compile(
            r'\s*<font[^>]*color=["\']?#ADD8E6["\']?[^>]*>\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,2})?\]</font>\s*',
            re.IGNORECASE
        )
        content = font_timestamp_pattern.sub(' ', html_content)

        raw_timestamp_pattern = re.compile(r'\s*\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,2})?\]\s*')
        content = raw_timestamp_pattern.sub(' ', content)

        content = re.sub(r'\s{2,}', ' ', content)
        content = re.sub(r'(<p[^>]*>)\s+', r'\1', content, flags=re.IGNORECASE)
        content = re.sub(r'\s+</p>', '</p>', content)
        content = re.sub(r'\s+<br\s*/?>', '<br />', content)

        return content.strip()

    def style_timestamps_in_html(self, html_content):
        """
        Applica uno stile coerente a tutti i timestamp all'interno di una stringa HTML.
        """
        timestamp_pattern = re.compile(r'(\[\d{2}:\d{2}(?::\d{2})?(?:\.\d)?\](?: - \[\d{2}:\d{2}(?::\d{2})?(?:\.\d)?\])?)')

        def style_match(match):
            return f"<font color='#ADD8E6'>{match.group(1)}</font>"

        unstyle_pattern = re.compile(r"<font color='#ADD8E6'>(.*?)</font>", re.IGNORECASE)
        unstyled_html = unstyle_pattern.sub(r'\1', html_content)

        styled_html = timestamp_pattern.sub(style_match, unstyled_html)

        return styled_html
