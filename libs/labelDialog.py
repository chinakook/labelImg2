import sys
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from libs.lib import newIcon, labelValidator
from libs.cmylist import CMyListModel

BB = QDialogButtonBox


class LabelDialog(QDialog):

    def __init__(self, text="Enter object label", parent=None, listItem=None):
        super(LabelDialog, self).__init__(parent)

        self.edit = QLineEdit()
        self.edit.setText(text)
        self.edit.setValidator(labelValidator())
        self.edit.editingFinished.connect(self.postProcess)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.edit)

        self.buttonBox = bb = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)
        bb.button(BB.Ok).setIcon(newIcon('done'))
        bb.button(BB.Cancel).setIcon(newIcon('undo'))
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)

        self.horlayout = QHBoxLayout()
        self.setDefaultBtn = QPushButton("set as default")
        self.setDefaultBtn.clicked.connect(self.defaultLabel)
        self.addBtn = QPushButton("add")
        self.addBtn.clicked.connect(self.addLabel)
        self.horlayout.addWidget(self.addBtn)
        self.horlayout.addWidget(self.setDefaultBtn)

        self.listWidget = QListView(self)

        self.model = CMyListModel(self.listWidget)
        

        self.model.setStringList(listItem)
        self.listWidget.setModel(self.model)

        if listItem is not None:
            self.default_label = listItem[0]
            self.model.setData(self.model.index(0), QBrush(Qt.red), Qt.BackgroundRole)
            
        else:
            self.default_label = None

        self.updateListItems(listItem)
        
        
        self.layout.addWidget(self.listWidget)
        self.layout.addLayout(self.horlayout)
        self.layout.addWidget(bb)
        self.setLayout(self.layout)

    def updateListItems(self, listItem):
        self.model.setStringList(listItem)

    def addLabel(self):
        if not self.edit.text() in self.model.stringList():
            lastrow = self.model.rowCount()
            self.model.insertRows(lastrow, 1)
            self.model.setData(self.model.index(lastrow), self.edit.text(), Qt.EditRole)
            self.listWidget.setCurrentIndex(self.model.index(lastrow))


    def defaultLabel(self):
        indexes = self.listWidget.selectedIndexes()
        if indexes is None:
            return

        sl = self.model.stringList()
        if sys.version_info < (3, 0, 0):
            j = sl.indexOf(self.default_label)
        else:
            j = sl.index(self.default_label)
            
        self.model.setData(self.model.index(j), QBrush(Qt.transparent), Qt.BackgroundRole)

        self.default_label = self.model.data(indexes[0], Qt.EditRole)
        if sys.version_info < (3, 0, 0):
            self.default_label = self.default_label.toPyObject()
        self.model.setData(self.model.index(indexes[0].row()), QBrush(Qt.red), Qt.BackgroundRole)


    def validate(self):
        try:
            if self.edit.text().trimmed():
                self.accept()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            if self.edit.text().strip():
                self.accept()

    def postProcess(self):
        try:
            self.edit.setText(self.edit.text().trimmed())
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            self.edit.setText(self.edit.text())

    def popUp(self, move=True):
        self.edit.setFocus(Qt.PopupFocusReason)
        if move:
            self.move(QCursor.pos())
        if self.exec_():
            return self.model.stringList(), self.default_label
        else:
            None

