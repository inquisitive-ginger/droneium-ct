import numpy as np
import os
import sys
import tarfile
import time

import tensorflow as tf
if tf.__version__ < '1.4.0':
    raise ImportError(
        'Please upgrade your tensorflow installation to v1.4.* or later!')

import zipfile
import sys
from collections import defaultdict

import cv2
import six.moves.urllib as urllib
from io import StringIO
# from matplotlib import pyplot as plt
# from PIL import Image

# This is needed since the notebook is stored in the object_detection folder.
MODEL_DIR = '../tensorflow/models/research/object_detection/'
sys.path.append(MODEL_DIR)

from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util
from utils import label_map_util
from utils import visualization_utils as vis_util

NUM_CLASSES = 90


class ObjectDetection():
    def __init__(self,
                 model_name='ssd_mobilenet_toy_gun',
                 loca_model=False,
                 label_path='./toygun_label_map.pbtxt',
                 detect_class=1,
                 camera=0):

        # general initialization variables
        self.model_name = model_name
        self.detect_class = detect_class
        self.label_path = label_path
        self.camera = camera

        # core detection variables
        self.detection_graph = None
        self.object_detected = False
        self.object_bounds = []

        # variables needed for ControlTower
        self.current_detection = {
            'bounding_box': [None, None, None, None],
            'timestamp': None
        }

        # go load model file (download if needed)
        self.initialize_model()

    def download_model(self):
        print("Downloading model file....")
        download_base = 'http://download.tensorflow.org/models/object_detection/'
        model_file = self.model_name + '.tar.gz'

        opener = urllib.request.URLopener()
        opener.retrieve(download_base + model_file, model_file)
        tar_file = tarfile.open(model_file)
        for file in tar_file.getmembers():
            file_name = os.path.basename(file.name)
            if 'frozen_inference_graph.pb' in file_name:
                tar_file.extract(file, os.getcwd())

    def initialize_model(self):
        # only download trained model if it doesn't exist already
        if (not os.path.exists(self.model_name)):
            self.download_model()

        # Path to frozen detection graph. This is the actual model that is used for the object detection.
        ckpt_path = self.model_name + '/frozen_inference_graph.pb'

        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(ckpt_path, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

    # only return boxes that meet a certain score threshold
    def filter_boxes(self, min_score, boxes, scores, classes, categories):
        n = len(classes)
        idxs = []
        for i in range(n):
            if classes[i] in categories and scores[i] >= min_score:
                idxs.append(i)

        filtered_boxes = boxes[idxs, ...]
        filtered_scores = scores[idxs, ...]
        filtered_classes = classes[idxs, ...]

        return filtered_boxes, filtered_scores, filtered_classes

    # open video stream a look run object detection algo
    def begin_detection(self):
        print('I am being run multiple times...')
        cap = cv2.VideoCapture(self.camera)

        # List of the strings that is used to add correct label for each box.
        # label_path = os.path.join(MODEL_DIR + 'data', 'mscoco_label_map.pbtxt')
        # load up label map
        label_map = label_map_util.load_labelmap(self.label_path)
        categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
        category_index = label_map_util.create_category_index(categories)

        with self.detection_graph.as_default():
            with tf.Session(graph=self.detection_graph) as sess:
                while True:
                    ret, image_np = cap.read()
                    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
                    image_np_expanded = np.expand_dims(image_np, axis=0)
                    image_tensor = self.detection_graph.get_tensor_by_name(
                        'image_tensor:0')
                    # Each box represents a part of the image where a particular object was detected.
                    boxes = self.detection_graph.get_tensor_by_name(
                        'detection_boxes:0')
                    # Each score represent how level of confidence for each of the objects.
                    # Score is shown on the result image, together with the class label.
                    scores = self.detection_graph.get_tensor_by_name(
                        'detection_scores:0')
                    classes = self.detection_graph.get_tensor_by_name(
                        'detection_classes:0')
                    num_detections = self.detection_graph.get_tensor_by_name(
                        'num_detections:0')
                    # Actual detection.
                    (boxes, scores, classes, num_detections) = sess.run(
                        [boxes, scores, classes, num_detections],
                        feed_dict={image_tensor: image_np_expanded})

                    (f_boxes, f_scores, f_classes) = self.filter_boxes(
                        0.5, boxes[0], scores[0], classes[0], [1])

                    # print(f_classes, f_scores, f_boxes)

                    # print(category_index[1])
                    # create bounded box and classes only if it is detect(52) and the confidence is more than 60%
                    if (len(f_boxes) > 0):
                        # print('Detected!')
                        max_detect_scores = np.array(f_scores)
                        max_detect_boxes = np.array(f_boxes)
                        max_detect_classes = np.array(
                            f_classes.astype(np.int32))

                        # set detection state
                        self.current_detection['bounding_box'] = max_detect_boxes[0]
                        self.current_detection['timestamp'] = time.time()

                        image_np = vis_util.visualize_boxes_and_labels_on_image_array(
                            image_np,
                            max_detect_boxes,
                            max_detect_classes,
                            max_detect_scores,
                            category_index,
                            min_score_thresh=0.5,
                            use_normalized_coordinates=True,
                            line_thickness=8)

                    ret, jpeg = cv2.imencode('.jpg', image_np)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    # check if there has ever been a detection
    def has_detected(self):
        return self.current_detection['timestamp'] is not None

    # check if current detection is recent
    def detection_is_fresh(self, threshold):
        if (self.current_detection['timestamp'] is None):
            return False
        return (time.time() - self.current_detection['timestamp']) < threshold

    # check how centered bounding box is
    def calculate_deltas(self):
        y_min, x_min, y_max, x_max = self.current_detection['bounding_box']
        x_delta, y_delta = [0, 0]

        if (x_min and y_min and x_max and y_max):
            x_delta = (1 - x_max) - x_min
            y_delta = (1 - y_max) - y_min

        return (x_delta, y_delta)


def main():
    object_detector = ObjectDetection(camera=0, model_name='ssd_mobilenet_toy_gun',
                                      label_path="./toygun_label_map.pbtxt", detect_class=1)
    object_detector.begin_detection()


if __name__ == '__main__':
    main()
