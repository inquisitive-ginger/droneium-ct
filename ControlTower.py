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
        self.cf = None  # crazyflie instance
        self.od = ObjectDetection(camera=0, model_name='ssd_mobilenet_toy_gun',
                                  label_path="./toygun_label_map.pbtxt", detect_class=1, visualize_detection=True)

        # start a new object detection thread
        self.fly_thread = threading.Thread(target=self.state_machine)

    def state_machine(self):
        # Initialize the low-level drivers (don't list the debug drivers)
        cflib.crtp.init_drivers(enable_debug_driver=False)

        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            self.cf = scf.cf

            self.take_off()
            self.search_mode()
            self.land()

    # flies in a pre-determined path until a gun has been
    # detected, then enters APPROACH mode.
    def search_mode(self):
        # do a loop while looking for gun
        print("Entering SEARCH mode...")

        start_time = time.time()
        gun_detected = False
        while not gun_detected:
            self.cf.commander.send_hover_setpoint(0.5, 0, 18, 1.0)
            time.sleep(0.1)

            # check for transition to APPROACH
            if self.od.detection_is_fresh(1):
                gun_detected = True
                break

            # exit if taking too long to detect
            if time.time() - start_time > 20:
                break

        if gun_detected:
            self.approach_mode()

    def approach_mode(self):
        print("Entering APPROACH mode...")

    def center_on_image(self):
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

    def take_off(self):
        print('Taking off...')
        # reset kalman filter
        self.cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self.cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(2)

        # move to 1 meter
        for y in range(25):
            self.cf.commander.send_hover_setpoint(0, 0, 0, y / 25)
            time.sleep(0.1)

    def land(self):
        print('Landing...')
        for _ in range(10):
            self.cf.commander.send_hover_setpoint(0, 0, 0, 1.0)
            time.sleep(0.1)

        for y in range(25):
            self.cf.commander.send_hover_setpoint(0, 0, 0, (25 - y) / 25)
            time.sleep(0.1)

        self.cf.commander.send_stop_setpoint()


def main():
    control_tower = ControlTower()
    control_tower.fly_thread.start()
    control_tower.od.begin_detection()


if __name__ == '__main__':
    main()
