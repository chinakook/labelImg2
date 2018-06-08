# -*- coding: utf-8 -*-
from __future__ import absolute_import

import sys
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
from .ustr import ustr

class HashableQStandardItem(QStandardItem):
    def __init__(self, text):
        super(HashableQStandardItem, self).__init__(text)

    def __hash__(self):
        return hash(id(self))


class CComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent, listItem):
        super(CComboBoxDelegate, self).__init__(parent)
        self.listItem = listItem

    def updateListItem(self, listItem):
        self.listItem = listItem

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        for i in self.listItem:
            editor.addItem(i)
        editor.currentIndexChanged.connect(self.editorIndexChanged)
        editor.setCurrentIndex(0)
        return editor

    # commit data early, prevent to loss data when clicking OpenNextImg
    def editorIndexChanged(self, index):
        combox = self.sender()
        self.commitData.emit(combox)

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.EditRole)
        if sys.version_info < (3, 0, 0):
            text = text.toPyObject()
        combox = editor
        tindex = combox.findText(ustr(text))
        combox.setCurrentIndex(tindex)

    def setModelData(self, editor, model, index):
        comboBox = editor
        strData = comboBox.currentText()
        oldstrData = index.model().data(index, Qt.EditRole)
        if strData != oldstrData:
            model.setData(index, strData, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class CEditDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(CEditDelegate, self).__init__(parent)
        self.currsender = None
        self.currstr = None

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.textEdited.connect(self.editorTextEdited)
        return editor

    def setEditorData(self, editor, index):
        self.currsender = None
        self.currstr = None
        return super(CEditDelegate, self).setEditorData(editor, index)

    def editorTextEdited(self, editorstr):
        self.currsender = self.sender()
        self.currstr = editorstr

    def earlyCommit(self):
        if self.currsender is not None and self.currstr is not None:
            # TODO: bug here,  should disable create rect when editing
            print(self.currsender)
            self.commitData.emit(self.currsender)


class CHeaderView(QHeaderView):
    clicked = pyqtSignal(int, bool)
    _x_offset = 3
    _y_offset = 0 # This value is calculated later, based on the height of the paint rect
    _width = 20
    _height = 20

    def __init__(self, orientation, parent=None):
        super(CHeaderView, self).__init__(orientation, parent)
        self.setFixedWidth(40)
        self.isChecked = []

    def rowsInserted(self, parent, start, end):
        self.isChecked.insert(start, 1)
        return super(CHeaderView, self).rowsInserted(parent, start, end)

    def rowsAboutToBeRemoved(self, parent, start, end):
        del self.isChecked[start]
        return super(CHeaderView, self).rowsAboutToBeRemoved(parent, start, end)

    def paintSection(self, painter, rect, logicalIndex):
        self._y_offset = int((rect.height()-self._width)/2.)
        
        option = QStyleOptionButton()
        option.state = QStyle.State_Enabled | QStyle.State_Active
        option.rect = QRect(rect.x() + self._x_offset, rect.y() + self._y_offset, self._width, self._height)
        
        if self.isChecked[logicalIndex]:
            option.state |= QStyle.State_On
        else:
            option.state |= QStyle.State_Off

        self.style().drawPrimitive(QStyle.PE_IndicatorCheckBox, option, painter)
        #self.style().drawControl(QStyle.CE_CheckBox, option, painter)
    
    def mouseReleaseEvent(self, e):
        index = self.logicalIndexAt(e.pos())
        
        if 0 <= index < self.count():
            # vertical orientation
            y = self.sectionViewportPosition(index)
            if self._x_offset < e.pos().x() < self._x_offset + self._width \
                and y + self._y_offset < e.pos().y() < y + self._y_offset + self._height:
                if self.isChecked[index] == 1:
                    self.isChecked[index] = 0
                else:
                    self.isChecked[index] = 1
                self.clicked.emit(index, self.isChecked[index])
                
                self.viewport().update()
            else:
                super(CHeaderView, self).mousePressEvent(e)
        else:
            super(CHeaderView, self).mousePressEvent(e)


class CLabelView(QTableView):
    def __init__(self, labelHist, parent = None):
        super(CLabelView, self).__init__(parent)
        
        header = CHeaderView(Qt.Vertical, self)
        self.setVerticalHeader(header)

        self.label_delegate = CComboBoxDelegate(self, labelHist)
        self.setItemDelegateForColumn(0, self.label_delegate)
        self.extra_delegate = CEditDelegate(self)
        self.setItemDelegateForColumn(1, self.extra_delegate)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setStyleSheet("selection-background-color: rgb(0,90,140)")

        model = QStandardItemModel(self)
        model.setColumnCount(2)
        model.setHorizontalHeaderLabels(["Label", "Extra Info"])

        self.setModel(model)
        
        self.sm = self.selectionModel()

    def earlyCommit(self):
        self.extra_delegate.earlyCommit()

    def updateLabelList(self, labelHist):
        self.label_delegate.updateListItem(labelHist)