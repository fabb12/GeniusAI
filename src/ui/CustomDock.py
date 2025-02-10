import warnings
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.dockarea.Dock import Dock, DockLabel


class CustomDockLabel(DockLabel):
    """
    CustomDockLabel è una sottoclasse di DockLabel che imposta uno style sheet
    per rendere la label con sfondo ciano (#00FFFF) e testo blu (#0000FF),
    ignorando la logica di stile predefinita.
    Sovrascrive updateStyle() e closeEvent() in modo da applicare i colori personalizzati
    e nascondersi anziché essere chiusa.
    """

    def __init__(self, text, closable=False, fontSize="12px", *args, **kwargs):
        # Inizializza la DockLabel di base (che estende VerticalLabel)
        super().__init__(text, closable=closable, *args, **kwargs)
        # Imposta alcuni attributi di base
        self.dim = False
        self.fixedWidth = False
        self.fontSize = fontSize
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.dock = None
        self.setAutoFillBackground(False)
        self.mouseMoved = False

        if closable:
            self.closeButton = QtWidgets.QToolButton(self)
            self.closeButton.clicked.connect(self.sigCloseClicked)
            self.closeButton.setIcon(QtWidgets.QApplication.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TitleBarCloseButton))
        else:
            self.closeButton = None

        # Forza l'uso dello sfondo stilizzato
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        # Applica il nostro stile personalizzato
        self.updateStyle()

    def updateStyle(self):
        # Usa la stessa struttura di formattazione dell'originale,
        # ma forza i colori: sfondo ciano (#00FFFF) e testo blu (#0000FF)
        r = '3px'
        fg = "#0000FF"  # testo blu
        bg = "#00FFFF"  # sfondo ciano
        # Puoi lasciare il bordo uguale a quello originale oppure modificarlo
        border = "#353c66"
        close_button_style = "QToolButton { color: black;  background-color : #b5bbc9; }"

        if self.orientation == 'vertical':
            style = """DockLabel {
                      background-color: %s;
                      color: %s;
                      border-top-right-radius: 0px;
                      border-top-left-radius: %s;
                      border-bottom-right-radius: 0px;
                      border-bottom-left-radius: %s;
                      border-width: 0px;
                      border-right: 2px solid %s;
                      padding-top: 3px;
                      padding-bottom: 3px;
                      font-size: %s;
                  }
                  %s""" % (bg, fg, r, r, border, self.fontSize, close_button_style)
        else:
            style = """DockLabel {
                      background-color: %s;
                      color: %s;
                      border-top-right-radius: %s;
                      border-top-left-radius: %s;
                      border-bottom-right-radius: 0px;
                      border-bottom-left-radius: 0px;
                      border-width: 0px;
                      border-bottom: 2px solid %s;
                      padding-left: 3px;
                      padding-right: 3px;
                      font-size: %s;
                  }
                  %s""" % (bg, fg, r, r, border, self.fontSize, close_button_style)
        self.setStyleSheet(style)

    def closeEvent(self, event):
        # Invece di chiudere la label, la nascondiamo
        self.hide()
        event.ignore()


class CustomDock(Dock):
    """
    CustomDock utilizza CustomDockLabel per il titolo e modifica il comportamento
    di hide/close in modo da non rimuovere il widget dalla gerarchia, ma semplicemente
    nasconderlo. Inoltre, offre il metodo setCustomStyle() per applicare uno style sheet
    al contenitore senza sovrascrivere lo style specifico della label.
    """

    def __init__(self, name, area=None, size=(10, 10), widget=None, hideTitle=False,
                 autoOrientation=True, label=None, **kargs):
        # Rimuovi 'closable' dai kwargs per evitare duplicazioni
        closable_value = kargs.pop('closable', False)
        if label is None:
            label = CustomDockLabel(name, closable=closable_value, **kargs)
        self.label = label
        super().__init__(name, area=area, size=size, widget=widget, hideTitle=hideTitle,
                         autoOrientation=autoOrientation, label=label, **kargs)

    def setCustomStyle(self, style):
        """
        Applica lo style sheet *style* al contenitore del dock e poi riapplica
        lo style specifico per la label (sfondo ciano e testo blu).
        """
        super().setStyleSheet(style)
        self.label.setStyleSheet("background-color: #00FFFF; color: #0000FF;")

    def hideDock(self):
        """Nasconde il dock e la sua label senza rimuoverli dalla gerarchia."""
        self.hide()
        self.label.hide()
        self.updateGeometry()
        if self.parentWidget():
            self.parentWidget().update()

    def showDock(self):
        """Mostra il dock e la sua label."""
        self.show()
        self.label.show()
        self.updateGeometry()
        if self.parentWidget():
            self.parentWidget().update()

    def close(self):
        """
        Nasconde il dock e la sua label (senza rimuoverlo dalla gerarchia)
        per poterlo ripristinare in seguito.
        """
        self.hideDock()
        self.sigClosed.emit(self)
