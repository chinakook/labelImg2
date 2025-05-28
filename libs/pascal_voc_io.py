#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
import math

XML_EXT = '.xml'
ENCODE_METHOD = 'utf-8'

class PascalVocWriter:

    def __init__(self, foldername, filename, imgSize,databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.roboxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        '''reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)'''

    def genXML(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.foldername is None or \
                self.imgSize is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        folder = SubElement(top, 'folder')
        folder.text = self.foldername

        filename = SubElement(top, 'filename')
        filename.text = self.filename

        if self.localImgPath is not None:
            localImgPath = SubElement(top, 'path')
            localImgPath.text = self.localImgPath

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.databaseSrc

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        width.text = str(self.imgSize[1])
        height.text = str(self.imgSize[0])
        if len(self.imgSize) == 3:
            depth.text = str(self.imgSize[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult, extra):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        bndbox['extra'] = extra
        self.boxlist.append(bndbox)

    def addRotatedBndBox(self, cx, cy, w, h, angle, name, difficult, extra):
        robndbox = {'cx': cx, 'cy': cy, 'w': w, 'h': h, 'angle': angle}
        robndbox['name'] = name
        robndbox['difficult'] = difficult
        robndbox['extra'] = extra
        self.roboxlist.append(robndbox)

    def appendObjects(self, top):
        for each_object in self.boxlist:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            try:
                name.text = unicode(each_object['name'])
            except NameError:
                # Py3: NameError: name 'unicode' is not defined
                name.text = each_object['name']
            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"
            truncated = SubElement(object_item, 'truncated')
            if int(each_object['ymax']) == int(self.imgSize[0]) or (int(each_object['ymin'])== 1):
                truncated.text = "1" # max == height or min
            elif (int(each_object['xmax'])==int(self.imgSize[1])) or (int(each_object['xmin'])== 1):
                truncated.text = "1" # max == width or min
            else:
                truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str( bool(each_object['difficult']) & 1 )
            bndbox = SubElement(object_item, 'bndbox')
            xmin = SubElement(bndbox, 'xmin')
            xmin.text = str(each_object['xmin'])
            ymin = SubElement(bndbox, 'ymin')
            ymin.text = str(each_object['ymin'])
            xmax = SubElement(bndbox, 'xmax')
            xmax.text = str(each_object['xmax'])
            ymax = SubElement(bndbox, 'ymax')
            ymax.text = str(each_object['ymax'])
            extra = SubElement(object_item, 'extra')
            try:
                extra.text = unicode(each_object['extra'])
            except NameError:
                # Py3: NameError: extra 'unicode' is not defined
                extra.text = each_object['extra']

        for each_object in self.roboxlist:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            try:
                name.text = unicode(each_object['name'])
            except NameError:
                # Py3: NameError: name 'unicode' is not defined
                name.text = each_object['name']
            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"
            truncated = SubElement(object_item, 'truncated')
            # if int(each_object['ymax']) == int(self.imgSize[0]) or (int(each_object['ymin'])== 1):
            #     truncated.text = "1" # max == height or min
            # elif (int(each_object['xmax'])==int(self.imgSize[1])) or (int(each_object['xmin'])== 1):
            #     truncated.text = "1" # max == width or min
            # else:
            truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str( bool(each_object['difficult']) & 1 )
            robndbox = SubElement(object_item, 'robndbox')
            cx = SubElement(robndbox, 'cx')
            cx.text = str(each_object['cx'])
            cy = SubElement(robndbox, 'cy')
            cy.text = str(each_object['cy'])
            w = SubElement(robndbox, 'w')
            w.text = str(each_object['w'])
            h = SubElement(robndbox, 'h')
            h.text = str(each_object['h'])
            angle = SubElement(robndbox, 'angle')
            angle.text = str(each_object['angle'])
            extra = SubElement(object_item, 'extra')
            try:
                extra.text = unicode(each_object['extra'])
            except NameError:
                # Py3: NameError: extra 'unicode' is not defined
                extra.text = each_object['extra']

    def save(self, targetFile=None):
        root = self.genXML()
        self.appendObjects(root)
        out_file = None
        if targetFile is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)

        prettifyResult = self.prettify(root)
        out_file.write(prettifyResult.decode('utf8'))
        out_file.close()


class PascalVocReader:

    def __init__(self, filepath):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.width = 0
        self.height = 0
        self.depth = 0
        self.filepath = filepath
        self.filename = None
        self.verified = False
        try:
            self.parseXML()
        except:
            pass

    def getShapes(self):
        return self.shapes

    def getSize(self):
        return self.width, self.height, self.depth
    
    def getImageFileName(self):
        return self.filename

    def addShape(self, label, bndbox, difficult, extra=None):
        xmin = int(eval(bndbox.find('xmin').text))
        ymin = int(eval(bndbox.find('ymin').text))
        xmax = int(eval(bndbox.find('xmax').text))
        ymax = int(eval(bndbox.find('ymax').text))
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        if extra is not None:
            self.shapes.append((label, points, None, None, difficult, extra))
        else:
            self.shapes.append((label, points, None, None, difficult))

    def addRotatedShape(self, label, robndbox, difficult, extra=None):
        cx = float(robndbox.find('cx').text)
        cy = float(robndbox.find('cy').text)
        w = float(robndbox.find('w').text)
        h = float(robndbox.find('h').text)
        angle = float(robndbox.find('angle').text)

        p0x,p0y = self.rotatePoint(cx,cy, cx - w/2, cy - h/2, -angle)
        p1x,p1y = self.rotatePoint(cx,cy, cx + w/2, cy - h/2, -angle)
        p2x,p2y = self.rotatePoint(cx,cy, cx + w/2, cy + h/2, -angle)
        p3x,p3y = self.rotatePoint(cx,cy, cx - w/2, cy + h/2, -angle)

        points = [(p0x, p0y), (p1x, p1y), (p2x, p2y), (p3x, p3y)]
        if extra is not None:
            self.shapes.append((label, points, None, None, difficult, True, angle, extra))
        else:
            self.shapes.append((label, points, None, None, difficult, True, angle))

    def rotatePoint(self, xc,yc, xp,yp, theta):        
        xoff = xp-xc
        yoff = yp-yc

        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        pResx = cosTheta * xoff + sinTheta * yoff
        pResy = - sinTheta * xoff + cosTheta * yoff
        # pRes = (xc + pResx, yc + pResy)
        return xc+pResx,yc+pResy

    def parseXML(self):
        assert self.filepath.endswith(XML_EXT), "Unsupport file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()
        self.filename = xmltree.find('filename').text
        try:
            verified = xmltree.attrib['verified']
            if verified == 'yes':
                self.verified = True
        except KeyError:
            self.verified = False

        sizetag = xmltree.find('size')
        widthtag = sizetag.find('width')
        heighttag = sizetag.find('height')
        depthtag = sizetag.find('depth')
        self.width = eval(widthtag.text)
        self.height = eval(heighttag.text)
        self.depth = eval(depthtag.text)

        for object_iter in xmltree.findall('object'):
            bndbox = object_iter.find("bndbox")
            if bndbox is None:
                robndbox = object_iter.find('robndbox')
            label = object_iter.find('name').text
            # Add chris
            difficult = False
            if object_iter.find('difficult') is not None:
                difficult = bool(int(object_iter.find('difficult').text))
            extra = None
            if object_iter.find('extra') is not None:
                extra = object_iter.find('extra').text
            if bndbox is None:
                self.addRotatedShape(label, robndbox, difficult, extra)
            else:                
                self.addShape(label, bndbox, difficult, extra)

        return True
