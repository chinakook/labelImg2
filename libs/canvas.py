# -*- coding: utf-8 -*-
from __future__ import absolute_import

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .shape import Shape
from .lib import distance
from libs.labelFile import LabelFile
import math

CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor


class Canvas(QWidget):
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal(bool)
    selectionChanged = pyqtSignal(bool)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)

    hideRRect = pyqtSignal(bool)
    hideNRect = pyqtSignal(bool)
    status = pyqtSignal(str)

    cancelDraw = pyqtSignal()

    toggleEdit = pyqtSignal(bool)

    #CREATE, EDIT = list(range(2))
    CREATE = 0
    EDIT = 1
    CONTINUECREATE = 2

    epsilon = 7.0

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.
        self.mode = self.EDIT
        self.shapes = []
        self.current = None
        self.selectedShape = None  # save the selected shape here
        self.selectedShapeCopy = None
        self.drawingLineColor = QColor(0, 0, 255)
        self.drawingRectColor = QColor(0, 0, 255) 
        self.line = Shape(line_color=self.drawingLineColor)
        self.prevPoint = QPointF()
        self.offsets = QPointF(), QPointF()
        self.scale = 1.0
        self.pixmap = QPixmap()
        
        #self.localScalePixmap = QPixmap()

        self.visible = {}
        self._hideBackround = False
        self.hideBackround = False
        self.hShape = None
        self.hVertex = None
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        self.menus = (QMenu(), QMenu())
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        self.verified = False

        self.canDrawRotatedRect = True
        self.hideRotated = False
        self.hideNormal = False
        self.canOutOfBounding = True
        self.showCenter = False
        
        #self.setAttribute(Qt.WA_PaintOnScreen)


        

    def setDrawingColor(self, qColor):
        self.drawingLineColor = qColor
        self.drawingRectColor = qColor

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)

    def leaveEvent(self, ev):
        self.restoreCursor()

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def isVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        return self.mode == self.CREATE

    def continueDrawing(self):
        return self.mode == self.CONTINUECREATE

    def editing(self):
        return self.mode == self.EDIT

    def setDrawCornerState(self, enabled):
        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            shape.alwaysShowCorner=enabled
        self.repaint()
        self.update()

    def setEditing(self, value=1):
        self.mode = value
        if value == self.CREATE or value == self.CONTINUECREATE:  # Create
            self.unHighlight()
            self.deSelectShape()
        self.prevPoint = QPointF()
        self.repaint()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None

    def selectedVertex(self):
        return self.hVertex is not None

    # reserve function
    def updateLocalScaleMap(self, x, y):
        pass
        #if self.pixmap is None:
        #    return

        #rz = 15
        #x0 = int(x) - rz
        #x1 = int(x) + rz
        #y0 = int(y) - rz
        #y1 = int(y) + rz

        #self.localScalePixmap = self.pixmap.copy(x0, y0, x1 - x0 + 1, y1 - y0 + 1) #self.grab(QRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1))
        ##self.localScalePixmap.grabWidget(self, pos.x(), pos.y(), 30, 30) # TODO: pyQt4
        #w = self.localScalePixmap.width()
        #h = self.localScalePixmap.height()
        #self.localScalePixmap = self.localScalePixmap.scaled(w * 5, h * 5, Qt.KeepAspectRatio)

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        pos = self.transformPos(ev.pos())

        # Update coordinates in status bar if image is opened
        window = self.parent().window()
        if window.filePath is not None:
            self.parent().window().labelCoordinates.setText(
                'X: %d; Y: %d' % (pos.x(), pos.y()))

        # Polygon drawing.
        if self.drawing():
            self.overrideCursor(CURSOR_DRAW)
            if self.current:
                color = self.drawingLineColor
                if self.outOfPixmap(pos):
                    # Don't allow the user to draw outside the pixmap.
                    # Project the point to the pixmap's edges.
                    pos = self.intersectionPoint(self.current[-1], pos)
                elif len(self.current) > 1 and self.closeEnough(pos, self.current[0]):
                    # Attract line to starting point and colorise to alert the
                    # user:
                    pos = self.current[0]
                    color = self.current.line_color
                    self.overrideCursor(CURSOR_POINT)
                    self.current.highlightVertex(0, Shape.NEAR_VERTEX)
                self.line[1] = pos
                self.line.line_color = color
                self.prevPoint = QPointF()
                self.current.highlightClear()
            else:
                self.prevPoint = pos
            
            self.updateLocalScaleMap(pos.x(), pos.y())
            
            self.repaint()
            return

        if self.continueDrawing():
            self.prevPoint = pos
            self.repaint()
            return

        # Polygon copy moving.
        if Qt.RightButton & ev.buttons():
            #if self.selectedShapeCopy and self.prevPoint:
            #    self.overrideCursor(CURSOR_MOVE)
            #    self.boundedMoveShape(self.selectedShapeCopy, pos)
            #    self.repaint()
            #elif self.selectedShape:
            #    self.selectedShapeCopy = self.selectedShape.copy()
            #    self.repaint()
            if self.selectedVertex() and self.selectedShape.isRotated:
                self.boundedRotateShape(pos)
                self.shapeMoved.emit()
                self.selectedShape.highlightCorner = True
                self.repaint()

            self.status.emit("(%d,%d)." % (pos.x(), pos.y()))
            return

        # Polygon/Vertex moving.
        if Qt.LeftButton & ev.buttons():
            if self.selectedVertex():
                self.boundedMoveVertex(pos)
                self.shapeMoved.emit()
                if self.selectedShape:
                    self.selectedShape.highlightCorner = True
            elif self.selectedShape and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShape, pos)
                self.shapeMoved.emit()
            self.updateLocalScaleMap(pos.x(), pos.y())
            self.repaint()
            return

        # Just hovering over the canvas, 2 posibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        self.setToolTip("Background")
        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            index = shape.nearestVertex(pos, self.epsilon / self.scale if self.scale > 1 else self.epsilon)
            if index is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = index, shape
                shape.highlightCorner = True
                shape.highlightVertex(index, shape.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                
                
                self.setToolTip("Click & drag to move point")
                #self.setStatusTip(self.toolTip())
                self.updateLocalScaleMap(pos.x(), pos.y())

                self.update()
                break
            elif shape.containsPoint(pos):
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = None, shape
                shape.highlightCorner = True
                # TODO: optimize here
                if shape.isRotated:
                    # rotbox = LabelFile.convertPoints2RotatedBndBox(shape)
                    # print(rotbox)
                    w = math.sqrt((shape.points[0].x()-shape.points[1].x()) ** 2 +
                        (shape.points[0].y()-shape.points[1].y()) ** 2)

                    h = math.sqrt((shape.points[2].x()-shape.points[1].x()) ** 2 +
                        (shape.points[2].y()-shape.points[1].y()) ** 2)
                    tooltip_str = "%s\n xywhr: (%f, %f, %f, %f, %f)" % (shape.label, shape.center.x(), shape.center.y(), w, h, 
                                                                        (shape.direction * 180 / math.pi) % 360)
                    # print(shape.direction  * 180 / math.pi)
                else:
                    tooltip_str = "%s\n X: (%f, %f)\nY: (%f, %f)" % (shape.label, shape.points[0].x(), shape.points[2].x(), shape.points[0].y(), shape.points[2].y())

                self.setToolTip(tooltip_str)
                #self.setStatusTip(self.toolTip())
                self.overrideCursor(CURSOR_GRAB)
                
                self.updateLocalScaleMap(pos.x(), pos.y())

                self.update()
                break
        else:  # Nothing found, clear highlights, reset state.
            if self.hShape:
                self.hShape.highlightClear()
                #self.hShape.highlightCorner=False

                self.updateLocalScaleMap(pos.x(), pos.y())
                self.update()
            else:
                self.updateLocalScaleMap(pos.x(), pos.y())
                self.repaint()
            self.hVertex, self.hShape = None, None
            self.overrideCursor(CURSOR_DEFAULT)


    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())

        if ev.button() == Qt.LeftButton:
            if self.drawing():
                self.handleDrawing(pos)
            if self.continueDrawing():
                pass
            else:
                self.selectShapePoint(pos)
                self.prevPoint = pos
                self.repaint()
        elif ev.button() == Qt.RightButton and self.editing():
            self.selectShapePoint(pos)
            self.prevPoint = pos
            self.repaint()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.RightButton:
            if self.selectedVertex() and self.selectedShape.isRotated:
                return
            menu = self.menus[bool(self.selectedShapeCopy)]
            self.restoreCursor()
            menu.exec_(self.mapToGlobal(ev.pos()))
            #if not menu.exec_(self.mapToGlobal(ev.pos())) and self.selectedShapeCopy:
            #    # Cancel the move by deleting the shadow copy.
            #    self.selectedShapeCopy = None
            #    self.repaint()
        elif ev.button() == Qt.LeftButton and self.selectedShape and self.editing():
            if self.selectedVertex():
                self.overrideCursor(CURSOR_POINT)
            else:
                self.overrideCursor(CURSOR_GRAB)
        elif ev.button() == Qt.LeftButton:
            pos = self.transformPos(ev.pos())
            if self.drawing():
                self.handleDrawing(pos)

            if self.continueDrawing():
                self.handleClickDrawing(pos)

    def endMove(self, copy=False):
        assert self.selectedShape and self.selectedShapeCopy
        shape = self.selectedShapeCopy
        #del shape.fill_color
        #del shape.line_color
        if copy:
            self.shapes.append(shape)
            self.selectedShape.selected = False
            self.selectedShape = shape
            self.repaint()
        else:
            self.selectedShape.points = [p for p in shape.points]
        self.selectedShapeCopy = None

    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selectedShape:
            # Only hide other shapes if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.repaint()

    def handleDrawing(self, pos):
        if self.current and self.current.reachMaxPoints() is False:
            self.current.highlightCorner=True
            initPos = self.current[0]
            minX = initPos.x()
            minY = initPos.y()
            targetPos = self.line[1]
            maxX = targetPos.x()
            maxY = targetPos.y()
            self.current.addPoint(QPointF(maxX, minY))
            self.current.addPoint(targetPos)
            self.current.addPoint(QPointF(minX, maxY))
            pos_diff = self.current.points[2] - self.current.points[0]
            if pos_diff.y() < 0:
                self.current.direction = math.pi
            self.finalise()
        elif not self.outOfPixmap(pos):
            self.current = Shape()
            self.current.highlightCorner=True
            self.current.addPoint(pos)
            self.line.points = [pos, pos]
            self.setHiding()
            self.drawingPolygon.emit(True)
            self.update()

    def handleClickDrawing(self, pos):
        if not self.outOfPixmap(pos):
            self.current = Shape()
            self.current.highlightCorner=True
            minX = pos.x() - 30
            maxX = pos.x() + 30
            minY = pos.y() - 38
            maxY = pos.y() + 38
            self.current.addPoint(QPointF(minX, minY))
            self.current.addPoint(QPointF(maxX, minY))
            self.current.addPoint(QPointF(maxX, maxY))
            self.current.addPoint(QPointF(minX, maxY))
            self.finalise(continous=True)

    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):
        return self.drawing() and self.current and len(self.current) > 2

    def mouseDoubleClickEvent(self, ev):
        # We need at least 4 points here, since the mousePress handler
        # adds an extra one before this handler is called.
        if self.canCloseShape() and len(self.current) > 3:
            self.current.popPoint()
            self.finalise()

    def selectShape(self, shape):
        self.deSelectShape()
        shape.selected = True
        self.selectedShape = shape
        self.setHiding()
        self.selectionChanged.emit(True)
        self.update()

    def selectShapePoint(self, point):
        """Select the first shape created which contains this point."""
        self.deSelectShape()
        if self.selectedVertex():  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, shape.MOVE_VERTEX)
            self.selectShape(shape)
            return
        for shape in reversed(self.shapes):
            if self.isVisible(shape) and shape.containsPoint(point):
                self.selectShape(shape)
                self.calculateOffsets(shape, point)
                return

    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width()) - point.x()
        y2 = (rect.y() + rect.height()) - point.y()
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if not self.canOutOfBounding and self.outOfPixmap(pos):
            return
            # pos = self.intersectionPoint(point, pos)

        sindex = (index + 2) % 4
        p2,p3,p4 = self.getAdjointPoints(shape.direction, shape[sindex], pos, index)

        pcenter = (pos+p3)/2        
        if self.canOutOfBounding and self.outOfPixmap(pcenter):
            return
        # if one pixal out of map , do nothing
        if not self.canOutOfBounding and (self.outOfPixmap(p2) or
            self.outOfPixmap(p3) or
            self.outOfPixmap(p4)):
                return
                
        shiftPos = pos - point
        shape.moveVertexBy(index, shiftPos)

        lindex = (index + 1) % 4
        rindex = (index + 3) % 4
        
        shape[lindex] = p2
        # shape[sindex] = p3
        shape[rindex] = p4
        shape.close()
        # lshift = None
        # rshift = None
        # if index % 2 == 0:
        #     rshift = QPointF(shiftPos.x(), 0)
        #     lshift = QPointF(0, shiftPos.y())
        # else:
        #     lshift = QPointF(shiftPos.x(), 0)
        #     rshift = QPointF(0, shiftPos.y())
        # shape.moveVertexBy(rindex, rshift)
        # shape.moveVertexBy(lindex, lshift)

    def getAdjointPoints(self, theta, p3, p1, index):
        # p3 = center
        # p3 = 2*center-p1
        a1 = math.tan(theta)
        if (a1 == 0):
            if index % 2 == 0:
                p2 = QPointF(p3.x(), p1.y())
                p4 = QPointF(p1.x(), p3.y())
            else:            
                p4 = QPointF(p3.x(), p1.y())
                p2 = QPointF(p1.x(), p3.y())
        else:    
            a3 = a1
            a2 = - 1/a1
            a4 = - 1/a1
            b1 = p1.y() - a1 * p1.x()
            b2 = p1.y() - a2 * p1.x()
            b3 = p3.y() - a1 * p3.x()
            b4 = p3.y() - a2 * p3.x()

            if index % 2 == 0:
                p2 = self.getCrossPoint(a1,b1,a4,b4)
                p4 = self.getCrossPoint(a2,b2,a3,b3)
            else:            
                p4 = self.getCrossPoint(a1,b1,a4,b4)
                p2 = self.getCrossPoint(a2,b2,a3,b3)

        return p2,p3,p4

    def getCrossPoint(self,a1,b1,a2,b2):
        x = (b2-b1)/(a1-a2)
        y = (a1*b2 - a2*b1)/(a1-a2)
        return QPointF(x,y)

    def boundedRotateShape(self, pos):
        # print("Rotate Shape2")          
        # judge if some vertex is out of pixma
        index, shape = self.hVertex, self.hShape
        point = shape[index]

        angle = self.getAngle(shape.center ,pos,point)
        # for i, p in enumerate(shape.points):
        #     if self.outOfPixmap(shape.rotatePoint(p,angle)):
        #         # print("out of pixmap")
        #         return
        if not self.rotateOutOfBound(angle):
            shape.rotate(angle)
            self.prevPoint = pos

    def getAngle(self, center, p1, p2):
        dx1 = p1.x() - center.x()
        dy1 = p1.y() - center.y()

        dx2 = p2.x() - center.x()
        dy2 = p2.y() - center.y()

        c = math.sqrt(dx1*dx1 + dy1*dy1) * math.sqrt(dx2*dx2 + dy2*dy2)
        if c == 0: return 0
        y = (dx1*dx2+dy1*dy2)/c
        if y>1: return 0
        angle = math.acos(y)

        if (dx1*dy2-dx2*dy1)>0:   
            return angle
        else:
            return -angle

    def boundedMoveShape(self, shape, pos):
        if shape.isRotated and self.canOutOfBounding:
            c = shape.center
            dp = pos - self.prevPoint
            dc = c + dp
            if dc.x() < 0:
                dp -= QPointF(min(0,dc.x()), 0)
            if dc.y() < 0:                
                dp -= QPointF(0, min(0,dc.y()))                
            if dc.x() >= self.pixmap.width():
                dp += QPointF(min(0, self.pixmap.width() - 1  - dc.x()), 0) # TODO
            if dc.y() >= self.pixmap.height():
                dp += QPointF(0, min(0, self.pixmap.height() - 1 - dc.y())) # TODO
        else:
            if self.outOfPixmap(pos):
                return False  # No need to move
            o1 = pos + self.offsets[0]
            if self.outOfPixmap(o1):
                pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
            o2 = pos + self.offsets[1]
            if self.outOfPixmap(o2):
                pos += QPointF(min(0, self.pixmap.width() - 1 - o2.x()),
                            min(0, self.pixmap.height() - 1 - o2.y()))
            dp = pos - self.prevPoint
        # The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason. XXX
        #self.calculateOffsets(self.selectedShape, pos)
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            shape.close()
            return True
        return False

    def boundedMoveShape2(self, shape, pos):
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QPointF(min(0, self.pixmap.width() - o2.x()),
                           min(0, self.pixmap.height() - o2.y()))
        # The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason. XXX
        #self.calculateOffsets(self.selectedShape, pos)
        dp = pos - self.prevPoint
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            shape.close()
            return True
        return False

    def deSelectShape(self):
        if self.selectedShape:
            self.selectedShape.selected = False
            self.selectedShape = None
            self.setHiding(False)
            self.selectionChanged.emit(False)
            self.update()

    def deleteSelected(self):
        if self.selectedShape:
            shape = self.selectedShape
            self.shapes.remove(self.selectedShape)
            self.selectedShape = None
            self.update()
            return shape
        
    def deleteAll(self):
        self.shapes.clear()
        self.selectedShape = None
        self.update()

    def copySelectedShape(self):
        if self.selectedShape:
            shape = self.selectedShape.copy()
            self.deSelectShape()
            self.shapes.append(shape)
            shape.selected = True
            self.selectedShape = shape
            self.boundedShiftShape(shape)
            return shape

    def boundedShiftShape(self, shape):
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        point = shape[0]
        offset = QPointF(2.0, 2.0)
        self.calculateOffsets(shape, point)
        self.prevPoint = point
        if not self.boundedMoveShape(shape, point - offset):
            self.boundedMoveShape(shape, point + offset)

    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        
        #ur = event.rect()
        #tmppix = QPixmap(ur.size())
        #p = QPainter(tmppix)
        #p.translate(-ur.x(), -ur.y())
        ##p.begin(self)

        p.begin(self)



        #p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        if self.scale < 1.0:
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            
        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        p.drawPixmap(0, 0, self.pixmap)
        Shape.scale = self.scale
        for shape in self.shapes:
            if (shape.selected or not self._hideBackround) and self.isVisible(shape):
                if (shape.isRotated and not self.hideRotated) or (not shape.isRotated and not self.hideNormal):
                    shape.fill = shape.selected or shape == self.hShape
                    shape.paint(p)
                elif self.showCenter:
                    shape.fill = shape.selected or shape == self.hShape
                    shape.paintNormalCenter(p) #shape.paint(p)
        if self.current:
            self.current.paint(p)
            self.line.paint(p)
        if self.selectedShapeCopy:
            self.selectedShapeCopy.paint(p)

        # Paint rect
        if self.current is not None and len(self.line) == 2:
            leftTop = self.line[0]
            rightBottom = self.line[1]
            rectWidth = rightBottom.x() - leftTop.x()
            rectHeight = rightBottom.y() - leftTop.y()
            p.setPen(self.drawingRectColor)
            brush = QBrush(Qt.BDiagPattern)
            p.setBrush(brush)
            p.drawRect(leftTop.x(), leftTop.y(), rectWidth, rectHeight)

        if (self.drawing() or self.continueDrawing()) and not self.prevPoint.isNull() and not self.outOfPixmap(self.prevPoint):
            oldmode = p.compositionMode()
            p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
            p.setPen(QPen(QColor(255,255,255), 1/self.scale)) # TODO : limit pen width

            p.drawLine(self.prevPoint.x(), 0, self.prevPoint.x(), self.pixmap.height())
            p.drawLine(0, self.prevPoint.y(), self.pixmap.width(), self.prevPoint.y())
            p.setCompositionMode(oldmode)

        self.setAutoFillBackground(True)
        if self.verified:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(184, 239, 38, 128))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(232, 232, 232, 255))
            self.setPalette(pal)

        #p.translate(-self.offsetToCenter())
        #p.scale(1/self.scale, 1/self.scale)
        #if self.localScalePixmap is not None:
        #    p0 = QPoint(0, 0)
        #    p1 = self.mapFromParent(p0)
        #    if p1.x() > 0:
        #        p0.setX(p1.x())
        #    if p1.y() > 0:
        #        p0.setY(p1.y())
            
        #    p.drawPixmap(p0.x(), p0.y(), self.localScalePixmap)

        p.end()

        #pp = self._painter
        #pp.begin(self)
        #pp.drawPixmap(0,0,tmppix)
        #pp.end()
        

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical coordinates."""
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w and 0 <= p.y() <= h)

    def finalise(self, continous=False):
        if self.current is None:
            return
        if self.current.points[0] == self.current.points[-1]:
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
            return

        self.current.isRotated = self.canDrawRotatedRect
        self.current.close()
        self.shapes.append(self.current)
        self.current = None
        self.setHiding(False)
        self.newShape.emit(continous) # TODO:
        self.update()

    def closeEnough(self, p1, p2):
        #d = distance(p1 - p2)
        #m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        return distance(p1 - p2) < self.epsilon

    def intersectionPoint(self, p1, p2):
        # Cycle through each image edge in clockwise fashion,
        # and find the one intersecting the current line segment.
        # http://paulbourke.net/geometry/lineline2d/
        size = self.pixmap.size()
        points = [(0, 0),
                  (size.width(), 0),
                  (size.width(), size.height()),
                  (0, size.height())]
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QPointF(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QPointF(min(max(0, x2), max(x3, x4)), y3)
        return QPointF(x, y)

    def intersectingEdges(self, x1y1, x2y2, points):
        """For each edge formed by `points', yield the intersection
        with the line segment `(x1,y1) - (x2,y2)`, if it exists.
        Also return the distance of `(x2,y2)' to the middle of the
        edge along with its index, so that the one closest can be chosen."""
        x1, y1 = x1y1
        x2, y2 = x2y2
        for i in range(4):
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QPointF((x3 + x4) / 2, (y3 + y4) / 2)
                d = distance(m - QPointF(x2, y2))
                yield d, i, (x, y)

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):
        qt_version = 4 if hasattr(ev, "delta") else 5
        if qt_version == 4:
            if ev.orientation() == Qt.Vertical:
                v_delta = ev.delta()
                h_delta = 0
            else:
                h_delta = ev.delta()
                v_delta = 0
        else:
            delta = ev.angleDelta()
            h_delta = delta.x()
            v_delta = delta.y()

        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.zoomRequest.emit(v_delta)
        else:
            v_delta and self.scrollRequest.emit(v_delta, Qt.Vertical)
            h_delta and self.scrollRequest.emit(h_delta, Qt.Horizontal)
        ev.accept()

    def keyPressEvent(self, ev):
        key = ev.key()
        if key == Qt.Key_Escape and self.current:
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
        elif key == Qt.Key_Escape and self.current is None:
            if self.drawing() or self.continueDrawing():
                self.cancelDraw.emit()
            self.finalise()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.canCloseShape():
                self.finalise()
            if self.selectedShape:
                self.toggleEdit.emit(True)
            else:
                if len(self.shapes) > 0:
                    self.selectShape(self.shapes[0])
        elif key == Qt.Key_Left and self.selectedShape:
            self.moveOnePixel('Left')
        elif key == Qt.Key_Right and self.selectedShape:
            self.moveOnePixel('Right')
        elif key == Qt.Key_Up and self.selectedShape:
            self.moveOnePixel('Up')
        elif key == Qt.Key_Down and self.selectedShape:
            self.moveOnePixel('Down')
        elif key == Qt.Key_Z and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(0.1):
            self.selectedShape.rotate(0.1)
            self.shapeMoved.emit() 
            self.update()  
        elif key == Qt.Key_X and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(0.01):
            self.selectedShape.rotate(0.01) 
            self.shapeMoved.emit()
            self.update()  
        elif key == Qt.Key_C and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(-0.01):
            self.selectedShape.rotate(-0.01) 
            self.shapeMoved.emit()
            self.update()  
        elif key == Qt.Key_V and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(-0.1):
            self.selectedShape.rotate(-0.1)
            self.shapeMoved.emit()
            self.update()
        elif key == Qt.Key_F and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(-math.pi/2):
            self.selectedShape.rotate(-math.pi/2)
            self.shapeMoved.emit()
            self.update()
        elif key == Qt.Key_R:
            self.hideRotated = not self.hideRotated
            self.hideRRect.emit(self.hideRotated)
            self.update()
        elif key == Qt.Key_N:
            self.hideNormal = not self.hideNormal
            self.hideNRect.emit(self.hideNormal)
            self.update()
        elif key == Qt.Key_O:
            self.canOutOfBounding = not self.canOutOfBounding
        elif key == Qt.Key_B:
            self.showCenter = not self.showCenter
            self.update()

    def rotateOutOfBound(self, angle):
        if self.canOutOfBounding:
            return False
        for i, p in enumerate(self.selectedShape.points):
            if self.outOfPixmap(self.selectedShape.rotatePoint(p,angle)):
                return True
        return False

    def moveOnePixel(self, direction):
        # print(self.selectedShape.points)
        if direction == 'Left' and not self.moveOutOfBound(QPointF(-1.0, 0)):
            # print("move Left one pixel")
            self.selectedShape.points[0] += QPointF(-1.0, 0)
            self.selectedShape.points[1] += QPointF(-1.0, 0)
            self.selectedShape.points[2] += QPointF(-1.0, 0)
            self.selectedShape.points[3] += QPointF(-1.0, 0)
            self.selectedShape.center += QPointF(-1.0, 0)
        elif direction == 'Right' and not self.moveOutOfBound(QPointF(1.0, 0)):
            # print("move Right one pixel")
            self.selectedShape.points[0] += QPointF(1.0, 0)
            self.selectedShape.points[1] += QPointF(1.0, 0)
            self.selectedShape.points[2] += QPointF(1.0, 0)
            self.selectedShape.points[3] += QPointF(1.0, 0)
            self.selectedShape.center += QPointF(1.0, 0)
        elif direction == 'Up' and not self.moveOutOfBound(QPointF(0, -1.0)):
            # print("move Up one pixel")
            self.selectedShape.points[0] += QPointF(0, -1.0)
            self.selectedShape.points[1] += QPointF(0, -1.0)
            self.selectedShape.points[2] += QPointF(0, -1.0)
            self.selectedShape.points[3] += QPointF(0, -1.0)
            self.selectedShape.center += QPointF(0, -1.0)
        elif direction == 'Down' and not self.moveOutOfBound(QPointF(0, 1.0)):
            # print("move Down one pixel")
            self.selectedShape.points[0] += QPointF(0, 1.0)
            self.selectedShape.points[1] += QPointF(0, 1.0)
            self.selectedShape.points[2] += QPointF(0, 1.0)
            self.selectedShape.points[3] += QPointF(0, 1.0)
            self.selectedShape.center += QPointF(0, 1.0)
        self.shapeMoved.emit()
        self.repaint()

    def moveOutOfBound(self, step):
        points = [p1+p2 for p1, p2 in zip(self.selectedShape.points, [step]*4)]
        return True in map(self.outOfPixmap, points)

    def setLastLabel(self, text, line_color  = None, fill_color = None, extra_text=''):
        assert text
        self.shapes[-1].label = text
        self.shapes[-1].extra_label = extra_text
        if line_color:
            self.shapes[-1].line_color = line_color
        
        if fill_color:
            self.shapes[-1].fill_color = fill_color

        return self.shapes[-1]

    def undoLastLine(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)

    def resetAllLines(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)
        self.current = None
        self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap):
        self.pixmap = pixmap
        self.shapes = []
        self.repaint()

    def loadShapes(self, shapes):
        self.shapes = list(shapes)
        self.current = None
        self.repaint()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()

    def currentCursor(self):
        cursor = QApplication.overrideCursor()
        if cursor is not None:
            cursor = cursor.shape()
        return cursor

    def overrideCursor(self, cursor):
        self._cursor = cursor
        if self.currentCursor() is None:
            QApplication.setOverrideCursor(cursor)
        else:
            QApplication.changeOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        #self.localScalePixmap = None
        self.update()
