#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import codecs
import distutils.spawn
import os
import platform
import re
import sys
import subprocess

from functools import partial
from collections import defaultdict

from libs.naturalsort import natsort

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

# Add internal libs
from libs.constants import *
from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut, generateColorByText
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.canvas import Canvas
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.labelFile import LabelFile, LabelFileError
from libs.pascal_voc_io import PascalVocReader, XML_EXT
from libs.ustr import ustr

from libs.labelView import CLabelView, HashableQStandardItem
from libs.fileView import CFileView

__appname__ = 'labelImg2'

# Utility functions and classes.

def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))

def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = QToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        if actions:
            if isinstance(action, QWidgetAction):
                return super(ToolBar, self).addAction(action)
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            toolbar.addWidget(btn)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None, defaultSaveDir=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        # Save as Pascal voc xml
        self.defaultSaveDir = defaultSaveDir

        # For loading all image under a directory
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None

        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)

        self.ShapeItemDict = {}
        self.ItemShapeDict = {}

        labellistLayout = QVBoxLayout()
        labellistLayout.setContentsMargins(0, 0, 0, 0)

        self.default_label = self.labelHist[0]

        # Create a widget for edit and diffc button
        self.diffcButton = QCheckBox(u'difficult')
        self.diffcButton.setChecked(False)
        self.diffcButton.stateChanged.connect(self.btnstate)
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        labellistLayout.addWidget(self.editButton)
        labellistLayout.addWidget(self.diffcButton)

        # Create and add a widget for showing current label items
        labelListContainer = QWidget()
        labelListContainer.setLayout(labellistLayout)

        self.labelList = CLabelView(self.labelHist)
        self.labelModel = self.labelList.model()
        self.labelModel.dataChanged.connect(self.labelDataChanged)
        
        self.labelList.extraEditing.connect(self.updateLabelShowing)

        self.labelsm = self.labelList.selectionModel()
        self.labelsm.currentChanged.connect(self.labelCurrentChanged)

        myHeader = self.labelList.verticalHeader()
        myHeader.clicked.connect(self.labelHeaderClicked)


        labellistLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Box Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)

        self.labelList.toggleEdit.connect(self.toggleExtraEditing)

        self.fileListView = CFileView()
        

        self.fileModel = self.fileListView.model()
        self.filesm = self.fileListView.selectionModel()
        self.filesm.currentChanged.connect(self.fileCurrentChanged)


        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)

        self.prevButton = QToolButton()
        self.nextButton = QToolButton()
        self.playButton = QToolButton()
        self.prevButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.nextButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.playButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.controlButtonsLayout = QHBoxLayout()
        self.controlButtonsLayout.setAlignment(Qt.AlignLeft)
        self.controlButtonsLayout.addWidget(self.prevButton)
        self.controlButtonsLayout.addWidget(self.nextButton)
        self.controlButtonsLayout.addWidget(self.playButton)

        filelistLayout.addLayout(self.controlButtonsLayout)

        filelistLayout.addWidget(self.fileListView)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)

        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)

        self.zoomWidget = ZoomWidget()

        scroll = QScrollArea()
        self.canvas = Canvas(parent=scroll)
        self.canvas.zoomRequest.connect(self.zoomRequest)

        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.canvas.cancelDraw.connect(self.createCancel)
        self.canvas.toggleEdit.connect(self.toggleExtraEditing)

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        self.dock.setFeatures(QDockWidget.DockWidgetFloatable)
        self.filedock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.displayTimer = QTimer(self)
        self.displayTimer.setInterval(1000)
        self.displayTimer.timeout.connect(self.autoNext)

        self.playing = False

        # Actions
        action = partial(newAction, self)
        quit = action('&Quit', self.close,
                      'Ctrl+Q', 'power.svg', u'Quit application')

        open = action('&Open', self.openFile,
                      'Ctrl+O', 'open.svg', u'Open image or label file')

        opendir = action('&Open Dir', self.openDirDialog,
                         'Ctrl+u', 'dir.svg', u'Open Dir')

        changeSavedir = action('&Change Save Dir', self.changeSavedirDialog,
                               'Ctrl+r', 'dir.svg', u'Change default saved Annotation dir')

        openAnnotation = action('&Open Annotation', self.openAnnotationDialog,
                                'Ctrl+Shift+O', 'open.svg', u'Open Annotation')



        verify = action('&Verify Image', self.verifyImg,
                        'space', 'downloaded.svg', u'Verify Image')

        save = action('&Save', self.saveFile,
                      'Ctrl+S', 'save.svg', u'Save labels to file', enabled=False)

        saveAs = action('&Save As', self.saveFileAs,
                        'Ctrl+Shift+S', 'save.svg', u'Save labels to a different file', enabled=False)

        close = action('&Close', self.closeFile, 'Ctrl+W', 'close.svg', u'Close current file')

        resetAll = action('&ResetAll', self.resetAll, None, 'reset.svg', u'Reset all')

        create = action('Create\nRectBox', self.createShape,
                        'w', 'rect.png', u'Draw a new Box', enabled=False)

        createSo = action('Create\nSolidRectBox', self.createSoShape,
                          None, 'rect.png', None, enabled=False)

        createRo = action('Create\nRotatedRBox', self.createRoShape,
                        'e', 'rectRo.png', u'Draw a new RotatedRBox', enabled=False)        
        
        delete = action('Delete\nRectBox', self.deleteSelectedShape,
                        'Delete', 'cancel2.svg', u'Delete', enabled=False)

        copy = action('&Duplicate\nRectBox', self.copySelectedShape,
                      'Ctrl+D', 'copy.svg', u'Create a duplicate of the selected Box',
                      enabled=False)

        showInfo = action('&About', self.showInfoDialog, None, 'info.svg', u'About')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in.svg', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out.svg', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom100.svg', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+F', 'zoomReset.svg', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width.svg', u'Zoom follows window width',
                          checkable=True, enabled=False)

        openPrevImg = action('&Prev Image', self.openPrevImg,
                             'a', 'previous.svg', u'Open Prev')

        openNextImg = action('&Next Image', self.openNextImg,
                             'd', 'next.svg', u'Open Next')        
        
        play = action('Play', self.playStart,
                    'Ctrl+Shift+P', 'play.svg', u'auto next',
                    checkable=True, enabled=True)
        
        self.prevButton.setDefaultAction(openPrevImg)
        self.nextButton.setDefaultAction(openNextImg)
        self.playButton.setDefaultAction(play)

        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Manage Labels', self.editLabel,
                      'Ctrl+M', 'tags.svg', u'Modify the label of the selected Box',
                      enabled=True)
        self.editButton.setDefaultAction(edit)

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))

        # Store actions for further handling.
        self.actions = struct(save=save, saveAs=saveAs, open=open, close=close, resetAll = resetAll,
                              create=create, createSo=createSo, createRo=createRo, delete=delete, edit=edit, copy=copy,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth, play=play,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  open, opendir, save, saveAs, close, resetAll, quit),
                              beginner=(),
                              editMenu=(edit, copy, delete,
                                        None),
                              beginnerContext=(create, createSo, createRo, copy, delete),
                              onLoadActive=(
                                  close, create),
                              onShapesPresent=(saveAs,))

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            labelList=labelMenu)

        # Auto saving : Enable auto saving if pressing next
        self.autoSaving = QAction("Auto Saving", self)
        self.autoSaving.setCheckable(True)
        self.autoSaving.setChecked(settings.get(SETTING_AUTO_SAVE, False))
        
        # Add option to enable/disable labels being painted at the top of bounding boxes
        self.paintLabelsOption = QAction("Paint Labels", self)
        self.paintLabelsOption.setShortcut("Ctrl+Shift+P")
        self.paintLabelsOption.setCheckable(True)
        self.paintLabelsOption.setChecked(settings.get(SETTING_PAINT_LABEL, False))
        self.paintLabelsOption.triggered.connect(self.togglePaintLabelsOption)

        self.drawCorner = QAction('Always Draw Corner', self)
        self.drawCorner.setCheckable(True)
        self.drawCorner.setChecked(settings.get(SETTING_DRAW_CORNER, False))
        self.drawCorner.triggered.connect(self.canvas.setDrawCornerState)
        
        addActions(self.menus.file,
                   (open, opendir, changeSavedir, openAnnotation, self.menus.recentFiles, save, saveAs, close, resetAll, quit))
        addActions(self.menus.help, (showInfo,))
        addActions(self.menus.view, (
            self.autoSaving,
            self.paintLabelsOption,
            self.drawCorner,
            None,
            None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (open, opendir, changeSavedir, verify, save, None, create, createSo, createRo, copy, delete, None,
            zoomIn, zoom, zoomOut, zoomOrg, fitWindow, fitWidth)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        ## Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recentFileQStringList = settings.get(SETTING_RECENT_FILES)
                self.recentFiles = [ustr(i) for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(settings.get(SETTING_SAVE_DIR, None))
        self.lastOpenDir = ustr(settings.get(SETTING_LAST_OPEN_DIR, None))
        if self.defaultSaveDir is None and saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)
        # Add chris
        Shape.difficult = self.difficult

        # Populate the File menu dynamically.
        self.updateFileMenu()

        # Since loading the file may take some time, make sure it runs in the background.
        if self.filePath and os.path.isdir(self.filePath):
            self.queueEvent(partial(self.importDirImages, self.filePath or ""))
        elif self.filePath:
            self.queueEvent(partial(self.loadFile, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        self.imageDim = QLabel('')
        self.statusBar().addPermanentWidget(self.imageDim)

        self.statFile = QLabel('')
        self.statusBar().addPermanentWidget(self.statFile)

        # Open Dir if deafult file
        if self.filePath and os.path.isdir(self.filePath):
            self.openDirDialog(dirpath=self.filePath)

    def noShapes(self):
        return not self.ItemShapeDict

    def populateModeActions(self):
        tool, menu = self.actions.beginner, self.actions.beginnerContext
        self.tools.clear()
        
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create, self.actions.createSo, self.actions.createRo) 
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setDirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)
        self.actions.createSo.setEnabled(True)
        self.actions.createRo.setEnabled(True)

    def autoNext(self):
        if self.playing:
            suc = self.openNextImg()
            if not suc:
                self.actions.play.triggered.emit(False)
                self.actions.play.setChecked(False)

    def playStart(self, value=True):
        if value:
            self.playing = True
            self.displayTimer.start()
        else:
            self.playing = False
            self.displayTimer.stop()

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.labelModel.clear()
        self.labelModel.setHorizontalHeaderLabels(["Label", "Extra Info"])
        self.ShapeItemDict.clear()
        self.ItemShapeDict.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()
        self.labelCoordinates.clear()
        self.imageDim.clear()

    def labelDataChanged(self, topLeft, bottomRight):
        item0 = self.labelModel.item(topLeft.row(), 0)
        shape = self.ItemShapeDict[item0]
        if topLeft.column() == 0:
            shape.label = self.labelModel.data(topLeft)
            if sys.version_info < (3, 0, 0):
                shape.label = shape.label.toPyObject()
            color = generateColorByText(shape.label)
            item1 = self.labelModel.item(topLeft.row(), 1)
            item0.setBackground(color)
            item1.setBackground(color)
            shape.line_color = color
            shape.fill_color = color
        else:
            shape.extra_label = self.labelModel.data(topLeft)
            if sys.version_info < (3, 0, 0):
                shape.extra_label = shape.extra_label.toPyObject()
        self.setDirty()
        
        return

    def updateLabelShowing(self, index, str):
        item0 = self.labelModel.item(index.row(), 0)
        shape = self.ItemShapeDict[item0]
        shape.extra_label = str
        self.canvas.update()

    def addRecentFile(self, filePath):
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def showInfoDialog(self):
        msg = u'{0} \n©Chinakook 2018. chinakook@msn.com'.format(__appname__)
        QMessageBox.information(self, u'About', msg)

    def createShape(self):
        self.canvas.setEditing(0)
        self.canvas.canDrawRotatedRect = False
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)

    def createSoShape(self):
        self.canvas.setEditing(2)
        self.canvas.canDrawRotatedRect = False
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)

    def createRoShape(self):
        self.canvas.setEditing(0)
        self.canvas.canDrawRotatedRect = True
        self.actions.create.setEnabled(False)
        self.actions.createSo.setEnabled(False)
        self.actions.createRo.setEnabled(False)
        
    def createCancel(self):
        self.canvas.setEditing(1)
        self.canvas.restoreCursor()
        self.actions.create.setEnabled(True)
        self.actions.createSo.setEnabled(True)
        self.actions.createRo.setEnabled(True)

    def toggleDrawingSensitive(self, drawing=True):
        if not drawing:
            self.canvas.setEditing(1)
            self.canvas.restoreCursor()
            self.actions.create.setEnabled(True)
            self.actions.createSo.setEnabled(True)
            self.actions.createRo.setEnabled(True)

    def toggleDrawMode(self, edit=1):
        self.canvas.setEditing(edit)

    def toggleExtraEditing(self, state):
        index = self.labelsm.currentIndex()
        #print("ExtraEditing", self.sender())
        editindex = self.labelModel.index(index.row(), 1)
        self.labelList.edit(editindex)

    def updateFileMenu(self):
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('print-setup.svg')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def editLabel(self):
        if not self.canvas.editing():
            return
        self.labelDialog.updateListItems(self.labelHist)
        res = self.labelDialog.popUp()

        if res is not None:
            self.labelHist, self.default_label = res
            self.labelList.updateLabelList(self.labelHist)


    def fileCurrentChanged(self, current, previous):
        self.statFile.setText('{0}/{1}'.format(current.row()+1, current.model().rowCount()))
        if self.autoSaving.isChecked():
            if self.defaultSaveDir is not None:
                
                self.labelList.earlyCommit()
                if self.dirty is True:
                    self.fileModel.setData(previous, len(self.canvas.shapes), Qt.BackgroundRole)
                    self.saveFile()
            else:
                self.changeSavedirDialog()
                return
        filename = self.fileModel.data(current, Qt.EditRole)
        if filename:
            self.loadFile(filename)

        if self.canvas.selectedShape:
            self.canvas.selectedShape.selected = False
            self.canvas.selectedShape = None
            self.canvas.setHiding(False)

    # Add chris
    def btnstate(self, item= None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return
        
        item0 = self.labelModel.itemFromIndex(self.labelModel.index(self.labelsm.currentIndex().row(), 0))
        if item0 is None:
            item0 = self.labelModel.item(self.labelModel.rowCount() - 1,0)

        difficult = self.diffcButton.isChecked()

        try:
            shape = self.ItemShapeDict[item0]
        except:
            pass
        # Checked and Update
        try:
            if difficult != shape.difficult:
                shape.difficult = difficult
                self.setDirty()
            else:  # User probably changed item visibility
                #self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)
                pass
        except:
            pass

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape and shape in self.ShapeItemDict:
                item0 = self.ShapeItemDict[shape]
                index = self.labelModel.indexFromItem(item0)
                self.labelList.selectRow(index.row())
                #self.labelsm.setCurrentIndex(index, QItemSelectionModel.SelectCurrent)

            else:
                
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)

    def addLabel(self, shape):
        shape.paintLabel = self.paintLabelsOption.isChecked()

        item0 = HashableQStandardItem(shape.label)
        item1 = QStandardItem(shape.extra_label)
        color = generateColorByText(shape.label)
        item0.setBackground(color)
        item1.setBackground(color)
        self.labelModel.appendRow([item0, item1])

        self.ShapeItemDict[shape] = item0
        self.ItemShapeDict[item0] = shape
        
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def remLabel(self, shape):
        if shape is None:
            return

        item0 = self.ShapeItemDict[shape]
        index = self.labelModel.indexFromItem(item0)
        
        self.labelModel.removeRows(index.row(), 1)
        del self.ShapeItemDict[shape]
        del self.ItemShapeDict[item0]

    def loadLabels(self, shapes):
        s = []
        for shape_info in shapes:
            if len(shape_info) == 5:
                label, points, line_color, fill_color, difficult = shape_info
                extra_label = ''
                isRotated = False
                direction = 0
            elif len(shape_info) == 6:
                label, points, line_color, fill_color, difficult, extra_label = shape_info
                isRotated = False
                direction = 0
            elif len(shape_info) == 7:
                label, points, line_color, fill_color, difficult, isRotated, direction = shape_info
                extra_label = ''
            elif len(shape_info) == 8:
                label, points, line_color, fill_color, difficult, isRotated, direction, extra_label = shape_info
            else:
                pass
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.difficult = difficult
            shape.direction = direction
            shape.isRotated = isRotated
            shape.extra_label = extra_label
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = generateColorByText(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = generateColorByText(label)
            
            shape.alwaysShowCorner = self.drawCorner.isChecked()

            if not label in self.labelHist:
                self.labelHist.append(label)
                self.labelList.updateLabelList(self.labelHist)
                

            self.addLabel(shape)

        self.canvas.loadShapes(s)

    def saveLabels(self, annotationFilePath):
        annotationFilePath = ustr(annotationFilePath)
        if self.labelFile is None:
            self.labelFile = LabelFile()
            self.labelFile.verified = self.canvas.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                       # add chris
                        difficult = s.difficult,
                        direction = s.direction,
                        center = s.center,
                        isRotated = s.isRotated,
                        extra_text = s.extra_label)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add differrent annotation formats here
        try:
            if ustr(annotationFilePath[-4:]) != ".xml":
                annotationFilePath += XML_EXT
            print ('Img: ' + self.filePath + ' -> Its xml: ' + annotationFilePath)
            self.labelFile.savePascalVocFormat(annotationFilePath, shapes, self.filePath, self.imageData,
                                                self.lineColor.getRgb(), self.fillColor.getRgb())
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data', u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        self.addLabel(self.canvas.copySelectedShape())
        # fix copy and delete
        self.shapeSelectionChanged(True)


    def labelCurrentChanged(self, current, previous):
        if current.row() < 0:
            return
        item0 = self.labelModel.itemFromIndex(self.labelModel.index(current.row(), 0))
        if self.canvas.editing():
            self._noSelectionSlot =True
            shape = self.ItemShapeDict[item0]
            self.canvas.selectShape(shape)
            self.diffcButton.setChecked(shape.difficult)

    def labelHeaderClicked(self, index, checked):
        item0 = self.labelModel.item(index, 0)
        shape = self.ItemShapeDict[item0]
        self.canvas.setShapeVisible(shape, checked)

    # Callback functions:
    def newShape(self, continous):
        text = self.default_label
        extra_text = ""
        if text is not None:
            generate_color = generateColorByText(text)
            shape = self.canvas.setLastLabel(text, generate_color, generate_color, extra_text)
            shape.alwaysShowCorner=self.drawCorner.isChecked()

            self.addLabel(shape)
            if continous:
                pass
            else:
                self.canvas.setEditing(1)
                self.actions.create.setEnabled(True)
                self.actions.createSo.setEnabled(True)
                self.actions.createRo.setEnabled(True)

            self.setDirty()

        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

    def scrollRequest(self, delta, orientation):
        #units = - delta / (8 * 15)
        units = - delta / (2 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def loadFile(self, filePath=None):
        """Load the specified file, or the last opened file if None."""
        self.resetState()
        self.canvas.setEnabled(False)
        if filePath is None:
            filePath = self.settings.get(SETTING_FILENAME)

        # Make sure that filePath is a regular python string, rather than QString
        if sys.version_info < (3, 0, 0):
            filePath = filePath.toPyObject()
        filePath = ustr(filePath)

        unicodeFilePath = ustr(filePath)
        
        if unicodeFilePath and os.path.exists(unicodeFilePath):
            if LabelFile.isLabelFile(unicodeFilePath):
                try:
                    self.labelFile = LabelFile(unicodeFilePath)
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.")
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData
                self.lineColor = QColor(*self.labelFile.lineColor)
                self.fillColor = QColor(*self.labelFile.fillColor)
                self.canvas.verified = self.labelFile.verified
            else:
                # Load image:
                # read data first and store for saving into label file.
                # self.imageData = read(unicodeFilePath, None)
                self.labelFile = None
                self.canvas.verified = False

            # image = QImage.fromData(self.imageData)
            # if image.isNull():
            #     self.errorMessage(u'Error opening file',
            #                       u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
            #     self.status("Error reading %s" % unicodeFilePath)
            #     return False
            #self.status("Loaded %s" % os.path.basename(unicodeFilePath))

            reader0 = QImageReader(unicodeFilePath)
            reader0.setAutoTransform(True)
            # transformation = reader0.transformation()
            # print(transformation)
            image = reader0.read()

            self.image = image
            self.filePath = unicodeFilePath
            self.canvas.loadPixmap(QPixmap.fromImage(image))
            self.imageDim.setText('%d x %d' % (self.image.width(), self.image.height()))
            if self.labelFile is not None:
                self.loadLabels(self.labelFile.shapes)
            self.setClean()
            self.canvas.setEnabled(True)
            self.adjustScale(initial=True)
            self.paintCanvas()
            self.addRecentFile(self.filePath)
            self.toggleActions(True)

            # Label xml file and show bound box according to its filename
            vocReader = None
            if self.defaultSaveDir is not None:
                relname = os.path.relpath(self.filePath, self.dirname)
                relname = os.path.splitext(relname)[0]
                # TODO: defaultSaveDir changed to another dir need mkdir for subdir
                xmlPath = os.path.join(self.defaultSaveDir, relname + XML_EXT)

                if os.path.exists(xmlPath) and os.path.isfile(xmlPath):
                    vocReader = self.loadPascalXMLByFilename(xmlPath)
            else:
                xmlPath = os.path.splitext(filePath)[0] + XML_EXT
                if os.path.isfile(xmlPath):
                    vocReader = self.loadPascalXMLByFilename(xmlPath)
            if vocReader is not None:
                vocWidth, vocHeight, _ = vocReader.getSize()
                if self.image.width() != vocWidth or self.image.height() != vocHeight:
                    #self.errorMessage("Image info not matched", "The width or height of annotation file is not matched with that of the image")
                    self.saveFile()

            self.canvas.setFocus(True)
            return True
        return False

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        if self.image.isNull():
            return
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            settings[SETTING_FILENAME] = self.filePath if self.filePath else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        settings[SETTING_RECENT_FILES] = self.recentFiles
        if self.defaultSaveDir and os.path.exists(self.defaultSaveDir):
            settings[SETTING_SAVE_DIR] = ustr(self.defaultSaveDir)
        else:
            settings[SETTING_SAVE_DIR] = ""

        if self.lastOpenDir and os.path.exists(self.lastOpenDir):
            settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
        else:
            settings[SETTING_LAST_OPEN_DIR] = ""

        settings[SETTING_AUTO_SAVE] = self.autoSaving.isChecked()
        settings[SETTING_DRAW_CORNER] = self.drawCorner.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        settings.save()
    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    path = ustr(os.path.abspath(relativePath))
                    images.append(path)
        # TODO: ascii decode error in natsort
        #images = natsort(images, key=lambda x: x.lower())
        #images.sort(key= lambda a, b: lexicographical_compare(a,b) )
        return images

    def changeSavedirDialog(self, _value=False):
        if self.defaultSaveDir is not None:
            path = ustr(self.defaultSaveDir)
        else:
            path = '.'

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                       '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.defaultSaveDir = dirpath

        imglist = self.scanAllImages(self.dirname)
        self.fileModel.setStringList(imglist, self.dirname, self.defaultSaveDir)

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotationDialog(self, _value=False):
        if self.filePath is None:
            self.statusBar().showMessage('Please select image first')
            self.statusBar().show()
            return

        path = os.path.dirname(ustr(self.filePath))\
            if self.filePath else '.'
        filters = "Open Annotation XML file (%s)" % ' '.join(['*.xml'])
        filename = ustr(QFileDialog.getOpenFileName(self,'%s - Choose a xml file' % __appname__, path, filters))
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
        self.loadPascalXMLByFilename(filename)

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else '.'
        if self.lastOpenDir and os.path.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            defaultOpenDirPath = os.path.dirname(self.filePath) if self.filePath else '.'

        targetDirPath = ustr(QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, defaultOpenDirPath,
                                                     QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
        self.importDirImages(targetDirPath)

    def importDirImages(self, dirpath):
        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.dirname = dirpath
        self.filePath = None
        
        imglist = self.scanAllImages(dirpath)
        self.fileModel.setStringList(imglist)

        self.defaultSaveDir = dirpath
        self.setWindowTitle(__appname__ + ' ' + self.dirname)
        self.openNextImg()

    def verifyImg(self, _value=False):
        # Proceding next image without dialog if having any label
         if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.saveFile()
                self.labelFile.toggleVerify()

            self.fileModel.setData(self.filesm.currentIndex(), len(self.canvas.shapes), Qt.BackgroundRole)
            self.canvas.verified = self.labelFile.verified
            self.paintCanvas()
            self.saveFile()

    def openPrevImg(self, _value=False):
        currIndex = self.filesm.currentIndex()
        if currIndex.row() - 1 < 0:
            return False
        
        prevIndex = self.fileModel.index(currIndex.row() - 1)
      
        self.filesm.setCurrentIndex(prevIndex, QItemSelectionModel.SelectCurrent)

        return True

    def openNextImg(self, _value=False):
        currIndex = self.filesm.currentIndex()
        if currIndex.row() + 1 >= self.fileModel.rowCount():
            return False

        nextIndex = self.fileModel.index(currIndex.row() + 1)      
        self.filesm.setCurrentIndex(nextIndex, QItemSelectionModel.SelectCurrent)

        return True

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.loadFile(filename)
    
    def saveFile(self, _value=False):
        
        if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):
            if self.filePath:
                relname = os.path.relpath(self.filePath, self.dirname)
                relname = os.path.splitext(relname)[0]
                savedPath = os.path.join(ustr(self.defaultSaveDir), relname)
                self._saveFile(savedPath)
        else:
            imgFileDir = os.path.dirname(self.filePath)
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0]
            savedPath = os.path.join(imgFileDir, savedFileName)
            self._saveFile(savedPath if self.labelFile
                           else self.saveFileDialog())

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            fullFilePath = ustr(dlg.selectedFiles()[0])
            return os.path.splitext(fullFilePath)[0] # Return file path without the extension.
        return ''

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):

            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(os.path.abspath(__file__))

    def mayContinue(self):
        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def deleteSelectedShape(self):
        self.remLabel(self.canvas.deleteSelected())
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.labelHist = [line]
                    else:
                        self.labelHist.append(line)

    def loadPascalXMLByFilename(self, xmlPath):
        if self.filePath is None:
            return None
        if os.path.isfile(xmlPath) is False:
            return None

        tVocParseReader = PascalVocReader(xmlPath)
        shapes = tVocParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tVocParseReader.verified
        return tVocParseReader

    def togglePaintLabelsOption(self):
        paintLabelsOptionChecked = self.paintLabelsOption.isChecked()
        for shape in self.canvas.shapes:
            shape.paintLabel = paintLabelsOptionChecked

def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("tag-black-shape.svg"))
    
    # Usage : labelImg.py image predefClassFile saveDir
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join(
                         os.path.dirname(sys.argv[0]),
                         'data', 'predefined_classes.txt'),
                     argv[3] if len(argv) >= 4 else None)
    win.show()
    return app, win


def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
