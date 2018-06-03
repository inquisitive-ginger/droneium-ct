import threading

from firebase import get_firebase_ref

from ObjectDetection import ObjectDetection
from ControlTower import ControlTower
from WebServer import WebServer

FIREBASE_REF = get_firebase_ref()


def main():
    object_detection = ObjectDetection(camera=0, model_name='ssd_mobilenet_toy_gun',
                                       label_path="./label_maps/toygun_label_map.pbtxt", detect_class=1)
    control_tower = ControlTower(FIREBASE_REF, object_detection)
    web_server = WebServer(control_tower)

    web_server.start()


if __name__ == '__main__':
    main()
