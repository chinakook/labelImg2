#!/usr/bin/python
# -*- coding: utf-8 -*-


from PyQt5.QtGui import *
from PyQt5.QtCore import *

from libs.lib import distance
import sys
import math

DEFAULT_LINE_COLOR = QColor(0, 255, 0, 128)
DEFAULT_FILL_COLOR = QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QColor(255, 0, 0)


class Shape(object):
    P_SQUARE, P_ROUND = range(2)

    MOVE_VERTEX, NEAR_VERTEX = range(2)

    # The following class variables influence the drawing
    # of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    def __init__(self, label=None, line_color=None, difficult=False, paintLabel=False, extra_label=''):
        self.label = label
        self.points = []
        self.fill = False
        self.selected = False
        self.difficult = difficult
        self.paintLabel = paintLabel
        self.extra_label = extra_label

        self.direction = 0
        self.center = None
        self.isRotated = True

        self.highlightCorner = False
        self.alwaysShowCorner = False

        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color

    def rotate(self, theta):
        for i, p in enumerate(self.points):
            self.points[i] = self.rotatePoint(p, theta)
        self.direction -= theta
        self.direction = self.direction % (2 * math.pi)
        
        # self.direction is the angle between y axis and the dotline, clockwise
        #print(self.direction * 180 / math.pi)

    def rotatePoint(self, p, theta):
        order = p - self.center
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        pResx = cosTheta * order.x() + sinTheta * order.y()
        pResy = - sinTheta * order.x() + cosTheta * order.y()
        pRes = QPointF(self.center.x() + pResx, self.center.y() + pResy)
        return pRes    

    def close(self):
        self.center = QPointF((self.points[0].x()+self.points[2].x()) / 2, (self.points[0].y()+self.points[2].y()) / 2)

        self._closed = True

    def reachMaxPoints(self):
        if len(self.points) >= 4:
            return True
        return False

    def addPoint(self, point):
        if not self.reachMaxPoints():
            self.points.append(point)

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    def paint(self, painter):
        if self.points:
            color = self.select_line_color if self.selected else self.line_color
            pen = QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            #pen.setWidth(int(round(2.0/self.scale)))
            painter.setPen(pen)

            line_path = QPainterPath()
            vrtx_path = QPainterPath()
            
            line_path.moveTo(self.points[0])
            # Uncommenting the following line will draw 2 paths
            # for the 1st vertex, and make it non-filled, which
            # may be desirable.
            #self.drawVertex(vrtx_path, 0)

            for i, p in enumerate(self.points):
                line_path.lineTo(p)
                self.drawVertex(vrtx_path, i)
            if self.isClosed():
                line_path.lineTo(self.points[0])

            painter.drawPath(line_path)
            if self.highlightCorner:
                painter.drawPath(vrtx_path)
                painter.fillPath(vrtx_path, self.vertex_fill_color)

            # Draw text at the top-left
            if self.paintLabel:
                min_x = sys.maxsize
                min_y = sys.maxsize
                for point in self.points:
                    min_x = min(min_x, point.x())
                    min_y = min(min_y, point.y())
                if min_x != sys.maxsize and min_y != sys.maxsize:
                    font = QFont()
                    font.setPointSize(20/self.scale) # TODO : max
                    font.setBold(False)
                    painter.setFont(font)
                    # TODO: optimize
                    if(self.label == None):
                        self.label = ""
                    painter.setPen(QColor(255,0,0))
                    painter.drawText(min_x, min_y, self.extra_label)
                    painter.setPen(pen)
                    
            if self.fill:
                color = self.select_fill_color if self.selected else self.fill_color
                painter.fillPath(line_path, color)

            if self.center is not None and self.isRotated:
                edgemid = (self.points[0] + self.points[1]) / 2

                center_path = QPainterPath()
                
                center_path.moveTo(edgemid)
                center_path.lineTo(self.center)

                pen.setStyle(Qt.DotLine)
                painter.setPen(pen)
                painter.drawPath(center_path)
                #d = self.point_size / self.scale
                #center_path.addRect(self.center.x() - d / 2, self.center.y() - d / 2, d, d)
                #painter.drawPath(center_path)
                
                #painter.fillPath(center_path, self.vertex_fill_color)
                    
            self.highlightCorner = self.alwaysShowCorner


    def paintNormalCenter(self, painter):
        if self.center is not None:
            center_path = QPainterPath();
            d = self.point_size / self.scale
            center_path.addRect(self.center.x() - d / 2, self.center.y() - d / 2, d, d)
            painter.drawPath(center_path)
            if not self.isRotated:
                painter.fillPath(center_path, QColor(0, 0, 0))

    def drawVertex(self, path, i):
        d = self.point_size / self.scale
        shape = self.point_type
        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        for i, p in enumerate(self.points):
            if distance(p - point) <= epsilon:
                return i
        return None

    def containsPoint(self, point):
        return self.makePath().contains(point)

    def makePath(self):
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        self._highlightIndex = None

    def copy(self):
        shape = Shape("%s" % self.label)
        shape.points = [p for p in self.points]

        shape.center = self.center
        shape.direction = self.direction
        shape.isRotated = self.isRotated

        shape.fill = self.fill
        shape.selected = self.selected
        shape._closed = self._closed
        if self.line_color != Shape.line_color:
            shape.line_color = self.line_color
        if self.fill_color != Shape.fill_color:
            shape.fill_color = self.fill_color
        shape.difficult = self.difficult
        shape.extra_label = self.extra_label
        return shape

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value
