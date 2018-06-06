try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import os

class CMyListModel(QStringListModel):
    def __init__(self, parent = None):
        super(CMyListModel, self).__init__(parent)
        self.rowColors = {}
        

    def data(self, index, role):
        if role == Qt.BackgroundRole:
            if index.row() in self.rowColors:
                return self.rowColors[index.row()]

        return super(CMyListModel, self).data(index, role)

    def setData(self, index, value, role = None):
        if role == Qt.BackgroundRole:
            self.rowColors[index.row()] = value
            return True

        return super(CMyListModel, self).setData(index, value, role)

    def flags(self, index):
        flags = super(CMyListModel, self).flags(index)
        flags ^= Qt.ItemIsEditable
        return flags

    
class MyFileListModel(QStringListModel):
    def __init__(self, parent = None):
        super(MyFileListModel, self).__init__(parent)
        self.dispList = []
        
    def setStringList(self, strings):
        
        self.dispList = [os.path.split(s)[1] for s in strings]
        return super(MyFileListModel, self).setStringList(strings)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.dispList[index.row()]
        elif role == Qt.ToolTipRole:
            return super(MyFileListModel, self).data(index, Qt.EditRole)
        else:
            return super(MyFileListModel, self).data(index, role)

    def setData(self, index, value, role = None):

        self.dispList.append(os.path.split(value)[1])

        return super(MyFileListModel, self).setData(index, value, role)

    def flags(self, index):
        flags = super(MyFileListModel, self).flags(index)
        flags ^= Qt.ItemIsEditable
        return flags