import os
import shutil
import random
import cv2
import numpy as np
def make_yolo_dirs(basedir, tag = 'train'):
    os.makedirs(os.path.join(basedir, 'images', tag), exist_ok=True)
    os.makedirs(os.path.join(basedir, 'labels', tag), exist_ok=True)

def cvt_lbidata_rotdet(lbi_data_dir, all_shapes_map, yolo_class_map, yolo_data_dir, tag = 'train', format = 'box'):
    make_yolo_dirs(yolo_data_dir, tag=tag)

    f_train_list = open(os.path.join(os.path.join(yolo_data_dir, '{}_list.txt'.format(tag,))), 'w', encoding='utf8')
    

    for i, (anno_img_fn, img_anno) in enumerate(all_shapes_map.items()):
        anno_fn = anno_img_fn
        anno_img_h = img_anno['height']
        anno_img_w = img_anno['width']
        anno_bboxes = img_anno['bboxes']

        f_train_list.write('./images/{}/{}.png\n'.format(tag, i))

        src_fn = os.path.join(lbi_data_dir, anno_fn)
        dst_fn = os.path.join(yolo_data_dir, 'images', tag, '{}.png'.format(i))
        # shutil.copy(os.path.join(lbi_data_dir, anno_fn), os.path.join(yolo_data_dir, 'images', tag, '{}.png'.format(i)))
        decbuf = np.fromfile(src_fn, dtype=np.uint8)
        img = cv2.imdecode(decbuf, cv2.IMREAD_COLOR)

        cv2.imencode('.png', img)[1].tofile(dst_fn)

        f_anno = open(os.path.join(yolo_data_dir, 'labels', tag, '{}.txt'.format(i)), 'w')

        dw = 1./anno_img_w
        dh = 1./anno_img_h

        if format == 'box':
            for b in anno_bboxes:
                xmin = b['x0']
                xmax = b['x2']
                ymin = b['y0']
                ymax = b['y2']
                bc = b['class']

                yolo_x = (xmin + xmax) / 2.0
                yolo_y = (ymin + ymax) / 2.0
                yolo_w = xmax - xmin
                yolo_h = ymax - ymin
                yolo_x *= dw
                yolo_w *= dw
                yolo_y *= dh
                yolo_h *= dh

                f_anno.write("{} {} {} {} {}\n".format(yolo_class_map[bc], yolo_x, yolo_y, yolo_w, yolo_h))
        elif format == 'rotbox':
            for b in anno_bboxes:
                bc = b['class']
                f_anno.write("{} {} {} {} {} {} {} {} {}\n".format(yolo_class_map[bc],
                                                                b['x0'] * dw, b['y0'] * dh, b['x1'] * dw, b['y1'] * dh, 
                                                                b['x2'] * dw, b['y2'] * dh, b['x3'] * dw, b['y3'] * dh
                                                                ))
        else:
            raise NotImplementedError()
        f_anno.close()
