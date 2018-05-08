import logging
import time
import threading

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

from ObjectDetection import ObjectDetection

URI = 'radio://0/80/250K'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

class ControlTower():
    def __init__(self):
        self.object_detection = ObjectDetection(camera=0, label_path="./banana_label_map.pbtxt", detect_class=52, visualize_detection=False)

        # start a new object detection thread
        self.od_thread = threading.Thread(target=self.object_detection.begin_detection)
        self.od_thread.start()

        # keep track of detection trends
        self.not_detected_count = 0

    def calculate_deltas(self, bounds):
        x_min, y_min, x_max, y_max = bounds
        x_delta = (1 - x_max) - x_min
        y_delta = (1 - y_max) - y_min

        print(x_delta, y_delta)

    def fly(self):
        # Initialize the low-level drivers (don't list the debug drivers)
        cflib.crtp.init_drivers(enable_debug_driver=False)

        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            # We take off when the commander is created
            with MotionCommander(scf) as mc:
                time.sleep(3)

                # move up a bit higher
                mc.up(1.0)
                time.sleep(1)

                # turn left and then right looking for object
                while(not self.object_detection.get_detected()):
                    mc.start_turn_right(rate=18)
                    time.sleep(0.1)
                
                mc.stop()

                while(self.not_detected_count < 100):
                    print("Not Detected Count: ", self.not_detected_count)
                    if(not self.object_detection.get_detected()):
                        self.not_detected_count += 1
                        time.sleep(0.1)
                        continue

                    if(self.not_detected_count < 20 or self.object_detection.get_detected()):
                        mc.forward(0.5, velocity=0.25)

                    time.sleep(0.1)

                mc.stop()
                # We land when the MotionCommander goes out of scope

def main():
    control_tower = ControlTower()
    control_tower.fly()

if __name__ == '__main__':
    main()