import numpy as np
import os
import sys
import tarfile

import tensorflow as tf
if tf.__version__ < '1.4.0':
  raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')

import zipfile
import sys
from collections import defaultdict

import cv2
import six.moves.urllib as urllib
from io import StringIO
from matplotlib import pyplot as plt
from PIL import Image

# This is needed since the notebook is stored in the object_detection folder.
MODEL_DIR = '../tensorflow/models/research/object_detection/'
sys.path.append(MODEL_DIR)
from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util
from utils import label_map_util
from utils import visualization_utils as vis_util

NUM_CLASSES = 90

class ObjectDetection():
    def __init__(self, model_name='ssd_mobilenet_v2_coco_2018_03_29', detect_class=1):
        # general initialization variables
        self.model_name = model_name
        self.detect_class = detect_class

        # core detection variables
        self.detection_graph = None
        self.object_detected = False
        self.object_bounds = []

        self.initialize_model()
        self.begin_detection()

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

    def begin_detection(self):
        cap = cv2.VideoCapture(0)

        # List of the strings that is used to add correct label for each box.
        label_path = os.path.join(MODEL_DIR + 'data', 'mscoco_label_map.pbtxt')

        # load up label map
        label_map = label_map_util.load_labelmap(label_path)
        categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
        category_index = label_map_util.create_category_index(categories)

        with self.detection_graph.as_default():
            with tf.Session(graph=self.detection_graph) as sess:
                while True:
                    ret, image_np = cap.read()
                    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
                    image_np_expanded = np.expand_dims(image_np, axis=0)
                    image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
                    # Each box represents a part of the image where a particular object was detected.
                    boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
                    # Each score represent how level of confidence for each of the objects.
                    # Score is shown on the result image, together with the class label.
                    scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
                    classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
                    num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')
                    # Actual detection.
                    (boxes, scores, classes, num_detections) = sess.run(
                    [boxes, scores, classes, num_detections],
                    feed_dict={image_tensor: image_np_expanded})
                    #print(category_index[1])
                    # create bounded box and classes only if it is banana(52) and the confidence is more than 60%
                    for i in range(0,len(classes[0])):
                        if int(float(classes[0][i])) == self.detect_class and scores[0,i] > 0.6:
                            # Visualization of the results of a detection.
                            image_np = vis_util.visualize_boxes_and_labels_on_image_array(
                                image_np,
                                np.squeeze(boxes),
                                np.squeeze(classes).astype(np.int32),
                                np.squeeze(scores),
                                category_index,
                                use_normalized_coordinates=True,
                                line_thickness=8)
                        #print the boxes coordinate
                        height = 800
                        width = 600
                        for f, box in enumerate(np.squeeze(boxes)):
                            if(np.squeeze(scores)[f] > 0.6):
                                print("ymin={}, xmin={}, ymax={}, xmax={}".format(box[0]*height,box[1]*width,box[2]*height,box[3]*width))
                                #Print the detected objects with the confidence
                        objects = []
                        for index, value in enumerate(classes[0]):
                            object_dict = {}
                            if scores[0, index] > 0.6:
                                object_dict[(category_index.get(value)).get('name').encode('utf8')] = \
                                scores[0, index]
                                objects.append(object_dict)
                        print(objects)

                    cv2.imshow('object detection', cv2.resize(image_np, (800,600)))
                    if cv2.waitKey(25) & 0xFF == ord('q'):
                        cv2.destroyAllWindows()
                        break


def main():
    model_name = 'ssd_mobilenet_v2_coco_2018_03_29'
    detect_class = 77
    object_detector = ObjectDetection(model_name=model_name, detect_class=detect_class)

if __name__ == '__main__':
    main()