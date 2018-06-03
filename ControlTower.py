import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/250K'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class ControlTower():
    def __init__(self, user, db, od):
        self.user = user  # credentials for writing to firebase
        self.db = db  # firebase reference
        self.od = od  # object detection reference

        print(user)

    def state_machine(self):
        # Initialize the low-level drivers (don't list the debug drivers)
        cflib.crtp.init_drivers(enable_debug_driver=False)
        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            self.cf = scf.cf

            self.take_off()
            self.search_mode()
            self.land()

    def sleep_2(self):
        for _ in range(20):
            time.sleep(0.1)

    def mock_state_machine(self):
        self.db.update({"state": "LAUNCH"}, self.user['idToken'])
        self.sleep_2()
        self.db.update({"state": "SEARCH"}, self.user['idToken'])
        self.sleep_2()
        self.db.update({"state": "APPROACH"}, self.user['idToken'])
        self.sleep_2()
        self.db.update({"state": "DETER"}, self.user['idToken'])

    # flies in a pre-determined path until a gun has been
    # detected, then enters APPROACH mode.
    def search_mode(self):
        # do a loop while looking for gun
        print("Entering SEARCH mode...")

        start_time = time.time()
        gun_detected = False
        while not gun_detected:
            self.cf.commander.send_hover_setpoint(0, 0, 18, 1.0)
            time.sleep(0.1)

            # check for transition to APPROACH
            if self.od.detection_is_fresh(1):
                gun_detected = True
                break

            # exit if taking too long to detect
            if time.time() - start_time > 15:
                break

        if gun_detected:
            self.approach_mode()

    def approach_mode(self):
        print("Entering APPROACH mode...")

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
    user_interface = UserInterface(control_tower)
    user_interface.start()


if __name__ == '__main__':
    main()
