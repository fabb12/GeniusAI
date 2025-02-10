"""
customDock.py

Questa implementazione definisce:
  - CustomDockLabel: una sottoclasse di DockLabel che sovrascrive il metodo closeEvent()
    in modo da non chiudersi (viene semplicemente nascosta).

  - CustomDock: una sottoclasse di Dock che utilizza CustomDockLabel e che nel metodo close()
    non rimuove la label dalla gerarchia dei widget, evitando così che venga distrutta.

Utilizza CustomDock al posto di Dock nel tuo codice per mantenere la label anche dopo la "chiusura" del dock.
"""

import warnings
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.dockarea.Dock import Dock, DockLabel


class CustomDockLabel(DockLabel):
    """
    CustomDockLabel è una sottoclasse di DockLabel che non viene effettivamente chiusa.
    Sovrascrive il metodo closeEvent() in modo da eseguire solo hide() e ignorare la close.
    """
    def closeEvent(self, event):
        # Invece di distruggere la label, la nascondiamo.
        self.hide()
        event.ignore()


class CustomDock(Dock):
    """
    CustomDock utilizza CustomDockLabel per il titolo e modifica il comportamento del close()
    per evitare la distruzione della label.
    """
    def __init__(self, name, area=None, size=(10, 10), widget=None, hideTitle=False,
                 autoOrientation=True, label=None, **kargs):
        # Rimuovi 'closable' dai kargs per evitare passaggi duplicati
        closable_value = kargs.pop('closable', False)
        if label is None:
            label = CustomDockLabel(name, closable=closable_value, **kargs)
        self.label = label
        super().__init__(name, area=area, size=size, widget=widget, hideTitle=hideTitle,
                         autoOrientation=autoOrientation, label=label, **kargs)

    def hideCustomDock(self):
        """Nasconde il dock, ma non distrugge la label."""
        self.hideDock()
        # Se necessario, puoi anche nascondere la label:
        # self.label.hide()

    def showCustomDock(self):
        """Mostra il dock e la label se era stata nascosta."""
        self.showDock()
        self.label.show()
    def close(self):
        """
        Rimuove il dock dall'area, ma evita di distruggere la label.
        La label viene semplicemente nascosta.
        """
        if self._container is None:
            warnings.warn(f"Cannot close dock {self} because it is not open.",
                          RuntimeWarning, stacklevel=2)
            return

        # Rimuove il dock dalla gerarchia dei widget.
        self.setParent(None)

        # Invece di chiudere (distruggere) la label, la nascondiamo.
        self.label.hide()
        # Non rimuoviamo il parent della label, altrimenti verrebbe distrutta.
        # self.label.setParent(None)  <-- NON chiamare questo!

        # Gestione del container.
        self._container.apoptose(propagate=False)
        self._container = None

        # Emissione del segnale di chiusura.
        self.sigClosed.emit(self)
