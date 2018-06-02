import logging
import time
import threading

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

from firebase import firebase

from ObjectDetection import ObjectDetection
from VideoServer import VideoServer

URI = 'radio://0/80/250K'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class ControlTower():
    def __init__(self):
        self.db = firebase.FirebaseApplication(
            'https://droneium-gix.firebaseio.com/', None)
        self.od = ObjectDetection(camera=0, model_name='ssd_mobilenet_toy_gun',
                                  label_path="./toygun_label_map.pbtxt", detect_class=1)

        self.fly_thread = threading.Thread(target=self.fly)
        self.video_server = VideoServer(self.od.begin_detection)
        self.server_thread = threading.Thread(target=self.video_server.start)

    def search_mode(self, mc):
        start_time = time.time()
        # turn left and then right looking for object
        print("Entering SEARCH mode...")
        while(True):
            mc.start_turn_right(rate=25)
            time.sleep(0.1)

            # state transition checks
            if(self.od.detection_is_fresh(1)):
                self.center_on_image(mc)
                break

            if(time.time() - start_time > 15):
                # return to main control loop
                break

    # def approach_mode(self, mc):
    #     print("Entering APPROACH mode...")
    #     while(self.not_detected_count < 200):
    #         if(self.not_detected_count % 10 == 0):
    #             print("Not Detected Count: ", self.not_detected_count)

    #         if(not self.object_detection.get_detected()):
    #             self.not_detected_count += 1
    #             time.sleep(0.1)
    #             continue

    #         if(self.not_detected_count < 20 or self.object_detection.get_detected()):
    #             print("Weapon Detected - APPROACHING!")
    #             mc.forward(0.5, velocity=0.25)

    #         time.sleep(0.1)

    #     mc.stop()

    def center_on_image(self, mc):
        print("Centering on Image...")
        while(True):
            # move drone based on location of bounding box
            # (x_delta [-1, 1], y_delta [-1, 1])
            x_delta, y_delta = self.od.calculate_deltas()

            # correct horizontal position
            if(x_delta > 0.1):
                mc.left(0.2)
            elif(x_delta < -0.1):
                mc.right(0.2)

            # correct vertical position
            if(y_delta > 0.1):
                mc.up(0.2)
            elif(y_delta < -0.1):
                mc.down(0.2)

            if(not self.od.detection_is_fresh(10)):
                mc.stop()
                break

            time.sleep(0.1)

        self.search_mode(mc)

        # should never reach this point
        mc.stop()

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
                mc.stop()

                self.search_mode(mc)
                # We land when the MotionCommander goes out of scope


def main():
    control_tower = ControlTower()
    control_tower.fly_thread.start()
    control_tower.server_thread.start()
    control_tower.db.post('/state', 'LAUNCH')

    while(1):
        time.sleep(5)
        break

    res = control_tower.db.get('/state', None)

    print(res)


if __name__ == '__main__':
    main()
