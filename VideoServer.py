#!/usr/bin/env python
from flask import Flask, render_template, Response


class VideoServer:
    def __init__(self, gen):
        self.gen = gen  # generator function that yields image

        self.app = Flask(__name__)
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/video_feed", "video_feed", self.video_feed)

    def index(self):
        return render_template('index.html')

    def video_feed(self):
        return Response(self.gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    def start(self):
        self.app.run(host='0.0.0.0', debug=False)
