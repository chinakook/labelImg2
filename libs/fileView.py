# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


class CFileListModel(QStringListModel):
    def __init__(self, parent = None):
        super(CFileListModel, self).__init__(parent)
        
        self.dispList = []
        
    def setStringList(self, strings):
        
        self.dispList = [os.path.split(s)[1] for s in strings]
        return super(CFileListModel, self).setStringList(strings)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.dispList[index.row()]
        elif role == Qt.ToolTipRole:
            return super(CFileListModel, self).data(index, Qt.EditRole)
        else:
            return super(CFileListModel, self).data(index, role)

    def setData(self, index, value, role = None):

        self.dispList.append(os.path.split(value)[1])

        return super(CFileListModel, self).setData(index, value, role)

    #def flags(self, index):
    #    flags = super(CFileListModel, self).flags(index)
    #    flags ^= Qt.ItemIsEditable
        
    #    return flags


class CFileView(QListView):
    def __init__(self, parent = None):
        super(CFileView, self).__init__(parent)
        
        model = CFileListModel(self)
        self.setModel(model)
        
        

