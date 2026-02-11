from core.worker import BaseWorker
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import cv2
import numpy as np
import logging
import queue
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QPoint, Qt, QRect
from PyQt6.QtGui import QPolygon

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
    detection_signal = pyqtSignal(object) # Emit detections

    def __init__(self, model_path="yolov11m.pt", pose_model_path="yolov8n-pose.pt", roi=None):
        super().__init__(name="DetectionWorker")
        self.model_path = model_path
        self.pose_model_path = pose_model_path
        self.roi_polygon = None # QPolygon
        self.model = None
        self.model_pose = None # Pose Model
        self.frame_queue = queue.Queue(maxsize=1) # Drop frames if busy
        self.last_phone_det = None # (time, detection_dict) for smoothing
        
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
        roi_points: List of [(x,y), ...] or None
        """
        if not roi_points or len(roi_points) < 0:
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
        
        import time
        t_start = time.time()
        
        # A. Object Detection (Person, Phone, Weapons)
        results = self.model(inference_frame, conf=0.15, iou=0.5, agnostic_nms=False, classes=[0, 67, 43, 76], verbose=False) 
        
        # DEBUG: Print raw count
        print(f"[DEBUG] Processing Frame: {frame.shape}")
        print(f"[DEBUG] Raw Detections: {len(results[0].boxes)}")
        
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                # print(f"   -> Clase: {int(box.cls)} | Conf: {float(box.conf):.2f}")
                pass
        else:
            print("[DEBUG] ¡LA IA NO VE NADA!")
        
        t_end = time.time()
        
        detections = []
        phone_detected_this_frame = False
        
        for r in results:
            if not self.is_running: break
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names[cls]
                
                # FORCE LOW THRESHOLD DEBUG
                if conf < 0.15: continue 
                
                # Threshold Filters (DISABLED FOR DEBUG)
                # if cls == 0 and conf < 0.20: pass 
                # if cls == 67 and conf < 0.25: continue
                # if (cls == 43 or cls == 76) and conf < 0.15: continue


                # Get Local Coordinates (Relative to Frame/Crop)
                xyxy = box.xyxy[0].cpu().numpy()
                lx1, ly1, lx2, ly2 = map(int, xyxy)
                
                # Convert to Global Coordinates for Check & UI
                x1 = lx1 + offset_x
                y1 = ly1 + offset_y
                x2 = lx2 + offset_x
                y2 = ly2 + offset_y
                
                # Check if detection intersects ROI (Global Coords)
                in_roi = False
                if hasattr(self, 'roi_polygon') and self.roi_polygon:
                    # STRICT: Check if CENTER of box is inside polygon
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    if self.roi_polygon.containsPoint(QPoint(center_x, center_y), Qt.FillRule.OddEvenFill):
                         in_roi = True

                # Normalize BBox for UI
                h, w = frame.shape[:2]
                norm_bbox = [x1/w, y1/h, x2/w, y2/h]
                
                fatigue_info = None

                # B. Pose Estimation (Classes 0 = Person)
                # Only if in ROI to save resources
                if cls == 0 and in_roi and self.model_pose:
                    # Crop the person from the *original* frame (Global Coords)
                    # Add margin
                    m = 10
                    px1 = max(0, x1 - m)
                    py1 = max(0, y1 - m)
                    px2 = min(w, x2 + m)
                    py2 = min(h, y2 + m)
                    
                    if px2 > px1 and py2 > py1:
                        person_crop = frame[py1:py2, px1:px2]
                        
                        # Pose Inference
                        pose_results = self.model_pose(person_crop, verbose=False, conf=0.5)
                        
                        if pose_results and len(pose_results) > 0:
                            # Use first person found in the crop
                            kpts = pose_results[0].keypoints 
                            if kpts is not None and kpts.has_visible:
                                # Extract Keypoints: 0=Nose, 5=LSh, 6=RSh
                                # xy is tensor [N, 17, 2]
                                xy = kpts.xy.cpu().numpy()[0] # First detection
                                
                                # Global Keypoints List for UI (x, y normalized)
                                ui_keypoints = []
                                for kp in xy:
                                    # Local to crop -> Global -> Normalized
                                    if kp[0] == 0 and kp[1] == 0: # Not detected
                                        ui_keypoints.append((0,0))
                                        continue
                                        
                                    gkp_x = kp[0] + px1
                                    gkp_y = kp[1] + py1
                                    # Normalize
                                    ui_keypoints.append((gkp_x / w, gkp_y / h))

                                # Log raw detection for debugging
                                # self.logger.info(f"DETECTION: {class_name} ({conf:.2f}) - In ROI: {in_roi}")
                                
                                fatigue_info = {
                                     'has_pose': (len(ui_keypoints) > 0),
                                     'keypoints': ui_keypoints,
                                     'centroid': ((x1+x2)/2/w, (y1+y2)/2/h)
                                }
                                
                                # Heuristics: Chin to Chest
                                # Need Nose (0) and Shoulders (5, 6)
                                if len(xy) >= 7:
                                    nose = xy[0]
                                    l_sh = xy[5]
                                    r_sh = xy[6]
                                    
                                    # ... (Calculate chin dist here if needed, or just pass keypoints)
                                    # For now, we pass raw keypoints and let LogicWorker handle it?
                                    # Actually, LogicWorker expects 'chin_dist' in fatigue_info.
                                    
                                    # Calculate Chin-Dist
                                    if nose[0] != 0 and l_sh[0] != 0 and r_sh[0] != 0:
                                        # Midpoint of shoulders
                                        mid_sh_y = (l_sh[1] + r_sh[1]) / 2
                                        nose_y = nose[1]
                                        
                                        # Distance (Positive if nose is above shoulders in image coords)
                                        # Higher Y = Lower in image.
                                        # Nose Y < Mid Sh Y -> Normal
                                        # Nose Y > Mid Sh Y -> Head Down (sleeping? or just looking down)
                                        # Let's normalize by box height specifically?
                                        
                                        box_h = y2 - y1
                                        chin_dist = (mid_sh_y - nose_y) / box_h
                                        fatigue_info['chin_dist'] = chin_dist
                
                # Add to list if valid (DEBUG THRESHOLDS)
                if cls == 0: # Person (Any conf > 0.15)
                     detections.append({
                         'class': 'person',
                         'conf': conf,
                         'bbox': norm_bbox,
                         'in_roi': in_roi,
                         'fatigue': fatigue_info
                     })
                elif cls == 67: # Phone
                     detections.append({
                         'class': 'cell phone',
                         'conf': conf,
                         'bbox': norm_bbox,
                         'in_roi': in_roi
                     })
                elif (cls == 43 or cls == 76): # Weapons
                     detections.append({
                         'class': class_name, 
                         'conf': conf,
                         'bbox': norm_bbox,
                         'in_roi': in_roi
                     })
                
                # Logic for Phone Persistence
                if cls == 67:
                    phone_detected_this_frame = True
                    # Need to store the valid detection dict we just appended.
                    # It's the last one in the list.
                    if len(detections) > 0:
                        self.last_phone_det = (time.time(), detections[-1])
        
        # Stabilization / Persistence for Cell Phones (Anti-Flicker)
        if not phone_detected_this_frame and self.last_phone_det:
             last_t, last_det = self.last_phone_det
             if time.time() - last_t < 0.5: # 0.5s buffer
                 # Keep the last detection alive (Ghost)
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
                import traceback
                traceback.print_exc()
                self.logger.error(f"Error in detection loop: {e}")
