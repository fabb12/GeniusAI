from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QSplitter
from PyQt6.QtCore import Qt
from src.ui.CustomDock import CustomDock
from src.ui.ChatDock import ChatDock
import json

class CommentsDock(CustomDock):
    def __init__(self, parent=None):
        super().__init__("Commenti YouTube", parent=parent)
        self.parent_window = parent

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter to divide comments and chat
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Comments display
        self.comments_tree = QTreeWidget()
        self.comments_tree.setColumnCount(2)
        self.comments_tree.setHeaderLabels(["Autore", "Commento"])
        splitter.addWidget(self.comments_tree)

        # Chat dock
        self.chat_dock = ChatDock(parent=self.parent_window)
        splitter.addWidget(self.chat_dock)

        main_layout.addWidget(splitter)
        self.addWidget(main_widget)

    def load_comments(self, comments_path):
        self.comments_tree.clear()
        try:
            with open(comments_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for comment in data.get('comments', []):
                    author = comment.get('author', 'N/A')
                    text = comment.get('text', '')
                    item = QTreeWidgetItem([author, text])
                    self.comments_tree.addTopLevelItem(item)
        except FileNotFoundError:
            self.comments_tree.clear()
            item = QTreeWidgetItem(["N/A", "File dei commenti non trovato."])
            self.comments_tree.addTopLevelItem(item)
        except json.JSONDecodeError:
            self.comments_tree.clear()
            item = QTreeWidgetItem(["N/A", "Errore nel caricamento del file dei commenti."])
            self.comments_tree.addTopLevelItem(item)
