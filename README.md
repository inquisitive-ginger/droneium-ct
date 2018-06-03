# Droneium

This is an entry to the [GIX Competition](https://gix.uw.edu/2018/03/28/2018-gix-innovation-competition-now-accepting-applications/) which uses Tensorflow's Object Detection API and a [Crazyflie 2.0](https://www.bitcraze.io/crazyflie-2/) to aid in the deterrance of active shooting situations.

## Main Dependencies

* [Tensorflow Object Detection API](https://github.com/tensorflow/models/tree/master/research/object_detection) - Uses custom trained model to detect the presence of a weapon (emulated with nerf guns).
* [cflib: Crazyflie python library](https://github.com/bitcraze/crazyflie-lib-python) - API to control the Crazyflie via RF
* [OpenCV](https://github.com/opencv/opencv) - For grabbing video stream from camera
* [Flask](https://github.com/pallets/flask) - User interface

## Usage

Once the dependencies are installed, use `droneium.py` as the main entry point. This will create necessary class instances and spin up a web server to interact with them.
