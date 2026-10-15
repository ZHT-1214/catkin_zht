import logging

import pyrealsense2 as rs
import numpy as np
import cv2


class RealSenseCamera:
    def __init__(self):
        self.logger = logging.getLogger("Tetris.RealSenseCamera")
        self.rs_pipeline = rs.pipeline()

        # Camera parameters
        self.camera_width = 1280
        self.camera_height = 720
        self.camera_fps = 30

        # CV parameters
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.filter_d = 9
        self.filter_sigma_color = 75
        self.filter_sigma_space = 75
        self.abs_alpha = 3.
        self.abs_beta = 25

    def init(self):
        # Init realsense camera pipeline
        config = rs.config()
        pipeline_wrapper = rs.pipeline_wrapper(self.rs_pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        found_rgb = False
        for s in device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                break
        if not found_rgb:
            self.logger.error("This program needs a Depth camera with Color sensor")
            raise Exception("No RGB camera found")
        config.enable_stream(rs.stream.color, self.camera_width, self.camera_height, rs.format.bgr8, self.camera_fps)
        self.rs_pipeline.start(config)
        self.logger.info("Realsense camera pipeline started")

    def get_frame(self):
        tried_times = 0
        while tried_times < 3:
            frames = self.rs_pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if color_frame:
                return np.asanyarray(color_frame.get_data())
            self.logger.error(f"Get color frame failed, tried times: {tried_times}/3")
            tried_times += 1

        raise Exception("Get color frame failed")
