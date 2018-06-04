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

        # initialize state in firebase
        self.db.update({
            "state": "IDLE",
            "deltas": {"x": 0, "y": 0}
        }, self.user['idToken'])

        self.deterred = False

    def state_machine(self):
        # Initialize the low-level drivers (don't list the debug drivers)
        cflib.crtp.init_drivers(enable_debug_driver=False)
        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            self.cf = scf.cf

            self.take_off()
            self.search_mode()
            self.land()

            if self.deterred:
                self.db.update({"state": "MISSION ACCOMPLISHED"},
                               self.user['idToken'])
            else:
                self.db.update({"state": "IDLE"}, self.user['idToken'])

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
        self.db.update({"state": "SEARCH"}, self.user['idToken'])
        print('Entering SEARCH mode...')

        start_time = time.time()
        gun_detected = False
        while not gun_detected:
            self.cf.commander.send_hover_setpoint(0, 0, 36, 1.0)
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
        self.db.update({"state": "APPROACH"}, self.user['idToken'])

        zeroed_in = False
        detecting = True
        while not zeroed_in and detecting:
            (delta_x, delta_y, area) = self.od.calculate_deltas()
            self.db.update({
                "deltas": {
                    "x": delta_x,
                    "y": delta_y
                }
            }, self.user['idToken'])

            # rotate to center on gun and move in
            vx = 0 if abs(delta_x) < 0.1 else 50 * -delta_x
            vy = 0 if area > 0.25 else 0.2

            self.cf.commander.send_hover_setpoint(vy, 0, vx, 1.0)
            time.sleep(0.1)

            detecting = self.od.detection_is_fresh(5)
            zeroed_in = area > 0.5

        if not detecting:
            self.search_mode()

        if zeroed_in:
            self.deter_mode()

    def deter_mode(self):
        print("Entering DETER mode...")
        self.db.update({"state": "DETER"}, self.user['idToken'])

        for _ in range(20):
            self.cf.commander.send_hover_setpoint(-1.0, 0, -36, 1.0)
            time.sleep(0.1)

        for _ in range(15):
            self.cf.commander.send_hover_setpoint(2.0, 0, 62, 1.0)
            time.sleep(0.1)

        for _ in range(20):
            self.cf.commander.send_hover_setpoint(-1.0, 0, 0, 1.0)
            time.sleep(0.1)

        for _ in range(15):
            self.cf.commander.send_hover_setpoint(2.0, 0, 0, 1.0)
            time.sleep(0.1)

        for _ in range(20):
            self.cf.commander.send_hover_setpoint(-1.0, 0, 36, 1.0)
            time.sleep(0.1)

        for _ in range(15):
            self.cf.commander.send_hover_setpoint(2.0, 0, -62, 1.0)
            time.sleep(0.1)

        self.deterred = True

    def take_off(self):
        self.db.update({"state": "LAUNCH"}, self.user['idToken'])
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
        self.db.update({"state": "LANDING"}, self.user['idToken'])
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
