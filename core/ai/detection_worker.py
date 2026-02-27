import time
import queue
import traceback
import logging

import cv2
import numpy as np
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QPoint, Qt
from PyQt6.QtGui import QPolygon

from core.worker import BaseWorker

# Try to import ultralytics, handle if missing
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class DetectionWorker(BaseWorker):
    """
    Worker for YOLOv11 Object Detection.
    """
    detection_signal = pyqtSignal(object)  # Emit detections

    def __init__(self, model_path="yolov11m.pt", pose_model_path="yolov8n-pose.pt", roi=None):
        super().__init__(name="DetectionWorker")
        self.model_path = model_path
        self.pose_model_path = pose_model_path
        self.roi_polygon = None  # QPolygon
        self.model = None
        self.model_pose = None  # Pose Model
        self.frame_queue = queue.Queue(maxsize=1)  # Drop frames if busy
        self.last_phone_det = None  # (time, detection_dict) for smoothing

        from config.settings import Settings
        self.settings = Settings()

    @pyqtSlot(object)
    def add_frame(self, frame):
        if not self.frame_queue.full():
            self.frame_queue.put(frame)

    @pyqtSlot(list)
    def set_roi(self, roi_points):
        """
        Updates the ROI.
        roi_points: List of [(x,y), ...] or None.
        Requires at least 3 points to form a valid polygon.
        """
        if not roi_points or len(roi_points) < 3:
            self.roi_polygon = None
            self.logger.info("ROI cleared in DetectionWorker.")
            return

        # Create QPolygon from points
        points = [QPoint(int(p[0]), int(p[1])) for p in roi_points]
        self.roi_polygon = QPolygon(points)
        self.logger.info(f"ROI updated in DetectionWorker (Polygon with {len(points)} points)")

    def load_model(self):
        if not YOLO_AVAILABLE:
            self.logger.warning("Ultralytics not installed. Detection disabled.")
            return False

        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.logger.info(f"Dispositivo de Inferencia: {device.upper()}")

            self.logger.info(f"Loading YOLO Object Model from {self.model_path}...")
            self.model = YOLO(self.model_path)
            self.model.to(device)

            # Load Pose Model
            self.logger.info(f"Loading YOLO Pose Model from {self.pose_model_path}...")
            self.model_pose = YOLO(self.pose_model_path)
            self.model_pose.to(device)

            self.logger.info(f"YOLO models loaded successfully on {device}.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load YOLO models: {e}")
            return False

    def process_frame(self, frame):
        if not self.model:
            return []

        h_orig, w_orig = frame.shape[:2]

        # OFFSETS for ROI Inference
        offset_x, offset_y = 0, 0
        inference_frame = frame

        # 1. Crop to ROI if available (Improves detection of small objects)
        if hasattr(self, 'roi_polygon') and self.roi_polygon:
            rect = self.roi_polygon.boundingRect()
            rx, ry, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()

            # Safety check for valid crop
            if rw > 0 and rh > 0:
                # Clamp to frame
                rx = max(0, rx)
                ry = max(0, ry)
                rw = min(rw, w_orig - rx)
                rh = min(rh, h_orig - ry)

                inference_frame = frame[ry:ry+rh, rx:rx+rw]
                offset_x, offset_y = rx, ry

        # A. Object Detection (Person, Phone, Weapons)
        results = self.model(
            inference_frame, conf=0.15, iou=0.5,
            agnostic_nms=False, classes=[0, 67, 43, 76], verbose=False
        )

        detections = []
        phone_detected_this_frame = False

        for r in results:
            if not self.is_running:
                break
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names[cls]

                if conf < 0.15:
                    continue

                # Get Local Coordinates (Relative to Frame/Crop)
                xyxy = box.xyxy[0].cpu().numpy()
                lx1, ly1, lx2, ly2 = map(int, xyxy)

                # Convert to Global Coordinates for Check & UI
                x1 = lx1 + offset_x
                y1 = ly1 + offset_y
                x2 = lx2 + offset_x
                y2 = ly2 + offset_y

                # Check if detection center is inside ROI polygon
                in_roi = False
                if hasattr(self, 'roi_polygon') and self.roi_polygon:
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    if self.roi_polygon.containsPoint(QPoint(center_x, center_y), Qt.FillRule.OddEvenFill):
                        in_roi = True

                # Normalize BBox for UI
                h, w = frame.shape[:2]
                norm_bbox = [x1/w, y1/h, x2/w, y2/h]

                fatigue_info = None

                # B. Pose Estimation (Person only, in ROI, saves resources)
                if cls == 0 and in_roi and self.model_pose:
                    m = 10
                    px1 = max(0, x1 - m)
                    py1 = max(0, y1 - m)
                    px2 = min(w, x2 + m)
                    py2 = min(h, y2 + m)

                    if px2 > px1 and py2 > py1:
                        person_crop = frame[py1:py2, px1:px2]

                        pose_results = self.model_pose(person_crop, verbose=False, conf=0.5)

                        if pose_results and len(pose_results) > 0:
                            kpts = pose_results[0].keypoints
                            if kpts is not None and kpts.has_visible:
                                xy = kpts.xy.cpu().numpy()[0]  # First detection

                                # Build global normalized keypoints for UI
                                ui_keypoints = []
                                for kp in xy:
                                    if kp[0] == 0 and kp[1] == 0:  # Not detected
                                        ui_keypoints.append((0, 0))
                                        continue
                                    gkp_x = kp[0] + px1
                                    gkp_y = kp[1] + py1
                                    ui_keypoints.append((gkp_x / w, gkp_y / h))

                                fatigue_info = {
                                    'has_pose': (len(ui_keypoints) > 0),
                                    'keypoints': ui_keypoints,
                                    'centroid': ((x1+x2)/2/w, (y1+y2)/2/h)
                                }

                                # Chin-to-Chest heuristic (Nose 0, LShoulder 5, RShoulder 6)
                                if len(xy) >= 7:
                                    nose = xy[0]
                                    l_sh = xy[5]
                                    r_sh = xy[6]

                                    if nose[0] != 0 and l_sh[0] != 0 and r_sh[0] != 0:
                                        mid_sh_y = (l_sh[1] + r_sh[1]) / 2
                                        nose_y = nose[1]
                                        box_h = y2 - y1
                                        chin_dist = (mid_sh_y - nose_y) / box_h
                                        fatigue_info['chin_dist'] = chin_dist

                # Append detection by class
                if cls == 0:  # Person
                    detections.append({
                        'class': 'person',
                        'conf': conf,
                        'bbox': norm_bbox,
                        'in_roi': in_roi,
                        'fatigue': fatigue_info
                    })
                elif cls == 67:  # Cell phone
                    detections.append({
                        'class': 'cell phone',
                        'conf': conf,
                        'bbox': norm_bbox,
                        'in_roi': in_roi
                    })
                elif cls == 43 or cls == 76:  # Weapons (knife / scissors)
                    detections.append({
                        'class': class_name,
                        'conf': conf,
                        'bbox': norm_bbox,
                        'in_roi': in_roi
                    })

                # Phone persistence: store last valid detection for anti-flicker
                if cls == 67:
                    phone_detected_this_frame = True
                    if detections:
                        self.last_phone_det = (time.time(), detections[-1])

        # Stabilization / Persistence for Cell Phones (Anti-Flicker, 0.5 s buffer)
        if not phone_detected_this_frame and self.last_phone_det:
            last_t, last_det = self.last_phone_det
            if time.time() - last_t < 0.5:
                detections.append(last_det)

        return detections

    def work(self):
        if not self.load_model():
            return

        while self.is_running:
            try:
                # Wait for frame with timeout to check is_running
                frame = self.frame_queue.get(timeout=1)
                detections = self.process_frame(frame)
                self.detection_signal.emit(detections)
            except queue.Empty:
                continue
            except Exception as e:
                traceback.print_exc()
                self.logger.error(f"Error in detection loop: {e}")
