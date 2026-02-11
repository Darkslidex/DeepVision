from core.worker import BaseWorker
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import cv2
import numpy as np
import time
import queue

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False

class BiometricWorker(BaseWorker):
    """
    Worker for Fatigue and Distraction detection using MediaPipe.
    """
    fatigue_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__(name="BiometricWorker")
        self.face_mesh = None
        self.mp_face_mesh = None
        self.frame_queue = queue.Queue(maxsize=1)

    @pyqtSlot(object)
    def add_frame(self, frame):
        if not self.frame_queue.full():
            self.frame_queue.put(frame)

    def init_mediapipe(self):
        if not MP_AVAILABLE:
            self.logger.warning("MediaPipe not installed. Biometrics disabled.")
            return False
        
        if not hasattr(mp, 'solutions'):
            self.logger.warning("MediaPipe 'solutions' module not found (Legacy API missing). Biometrics disabled.")
            return False
            
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return True

    def calculate_mar(self, landmarks):
        # Placeholder for Mouth Aspect Ratio calculation
        # Need specific landmark indices for lips
        return 0.0

    def calculate_ear(self, landmarks):
        # Placeholder for Eye Aspect Ratio calculation
        return 0.0

    def process_frame(self, frame):
        if not self.face_mesh:
            return None

        if not self.is_running: return None
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                if not self.is_running: break
                # Analyze landmarks for fatigue
                # Example logic
                fatigue_data = {
                    "is_drowsy": False, 
                    "is_yawning": False,
                    "is_distracted": False
                }
                return fatigue_data
        
        return None

    def work(self):
        if not self.init_mediapipe():
            return

        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=1)
                data = self.process_frame(frame)
                if data:
                    self.fatigue_signal.emit(data)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in biometric loop: {e}")
