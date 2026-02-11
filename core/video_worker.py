from core.worker import BaseWorker
from PyQt6.QtCore import pyqtSignal
import cv2
import time
import numpy as np

class VideoThread(BaseWorker):
    """
    Worker thread that captures frames from an RTSP stream or camera.
    Handles reconnection automatically.
    """
    frame_captured_signal = pyqtSignal(object) # Emits np.array (frame)
    status_signal = pyqtSignal(str) # Emits status messages (Connected, Retry, etc.)

    def __init__(self, rtsp_url):
        super().__init__(name="VideoThread")
        self.rtsp_url = rtsp_url
        self.cap = None
        self.reconnect_delay = 5 # Seconds

    def connect(self):
        """Attempts to connect to the video source."""
        # Sanitize URL: Remove quotes, whitespace, or potential 'URL = ' prefixes if pasted by user
        url = str(self.rtsp_url).strip().strip('"').strip("'")
        if url.lower().startswith("url = "):
             url = url[6:].strip().strip('"').strip("'")
             
        # Force TCP for RTSP (more stable/robust against packet loss than UDP)
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        
        self.logger.info(f"Connecting to sanitized URL: {url}...")
        self.status_signal.emit("Connecting...")
        
        # Force FFMPEG backend
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        
        # If it's a webcam index (integer), convert back
        if str(url).isdigit():
             self.cap = cv2.VideoCapture(int(url))
        
        if self.cap.isOpened():
            self.logger.info("Connected to camera.")
            self.status_signal.emit("Connected")
            return True
        else:
            self.logger.warning("Failed to connect.")
            return False

    def work(self):
        # Initial Connection Attempt
        if not self.connect():
            self.status_signal.emit("Connection Failed")
            # User request: Only retry if we were once connected.
            # If initial connection fails, we stop the thread.
            return 

        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                if not self.connect():
                    self.status_signal.emit(f"Retry in {self.reconnect_delay}s...")
                    time.sleep(self.reconnect_delay)
                    continue
            
            ret, frame = self.cap.read()
            if ret:
                # Emit frame
                self.frame_captured_signal.emit(frame)
                # Small sleep to limit FPS if needed, but cv2 read is usually blocking to FPS
                # time.sleep(0.01) 
            else:
                self.logger.warning("Lost connection to stream. Reconnecting...")
                self.status_signal.emit("Connection Lost")
                self.cap.release()
                self.cap = None
    
    def stop(self):
        super().stop()
        if self.cap:
            self.cap.release()
