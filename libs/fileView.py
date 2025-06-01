# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from .pascal_voc_io import PascalVocReader, XML_EXT

class CFileListModel(QStringListModel):
    def __init__(self, parent = None):
        super(CFileListModel, self).__init__(parent)
        
        self.dispList = []
    
    def parseOne(self, s, openedDir = None, defaultSaveDir = None):
        if openedDir is not None and defaultSaveDir is not None:
            relname = os.path.relpath(s, openedDir)
            relname = os.path.splitext(relname)[0]
            xmlPath = os.path.join(defaultSaveDir, relname + XML_EXT)
        else:
            xmlPath = os.path.splitext(s)[0] + XML_EXT
        if os.path.exists(xmlPath) and os.path.isfile(xmlPath):
            tVocParser = PascalVocReader(xmlPath)
            shapes = tVocParser.getShapes()
            info = [os.path.split(s)[1], len(shapes), False]
        else:
            info = [os.path.split(s)[1], None, False]
        return info

    def setStringList(self, strings, openedDir = None, defaultSaveDir = None):
        self.dispList = []

        for s in strings:
            info = self.parseOne(s, openedDir, defaultSaveDir)
            self.dispList.append(info)

        return super(CFileListModel, self).setStringList(strings)

    def data(self, index, role):
        item = self.dispList[index.row()]
        pathname, count = item[0], item[1]
        if role == Qt.DisplayRole:
            if count is None:
                res_str = '%s [0]' % (pathname,)
            else:
                if count == 0:
                    res_str = '%s [BG]' % (pathname,)
                else:
                    res_str = '%s [%d]' % (pathname, count)
            return res_str
        elif role == Qt.ToolTipRole:
            return super(CFileListModel, self).data(index, Qt.EditRole)
        elif role == Qt.BackgroundRole:
            if item[1] is None: # or item[1] == 0:
                brush = QBrush(Qt.transparent)
            else:
                brush = QBrush(Qt.lightGray)
            if item[2]:
                brush = QBrush(Qt.green)
            return brush
        else:
            return super(CFileListModel, self).data(index, role)

    def setData(self, index, value, role = None):

        if role == Qt.BackgroundRole:
            info = self.dispList[index.row()]
            info[1] = value
            info[2] = True
            self.dispList[index.row()] = info

        return super(CFileListModel, self).setData(index, value, role)


class CFileItemEditDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(CFileItemEditDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setReadOnly(True)
        return editor


class CFileView(QListView):
    def __init__(self, parent = None):
        super(CFileView, self).__init__(parent)
        
        model = CFileListModel(self)
        self.setModel(model)

        delegate = CFileItemEditDelegate(self)
        self.setItemDelegateForColumn(0, delegate)
        
        

