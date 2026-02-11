import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QFont, QBrush

class VideoOverlay(QWidget):
    roi_drawn = pyqtSignal(list) # Emits [(x, y), ...]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Always track mouse, but only act if drawing
        self.setMouseTracking(True)
        
        self.roi_points = []
        self.mouse_pos = None
        self.detections = [] 
        self.is_drawing_roi = False
        self.current_roi = QPolygon()
        
        self.alert_text = ""
        self.alert_color = QColor(255, 0, 0) 
        self.alert_active = False

    def clear_roi_visuals(self):
        """Clears the visual ROI polygon."""
        self.roi_points = []
        self.current_roi = QPolygon()
        self.roi_start_point = None
        self.update()
        print("DEBUG: ROI Visuals Cleared")

    def set_drawing_mode(self, active: bool):

        self.is_drawing_roi = active
        self.update()

    def start_drawing_roi(self):
        """Resets ROI and starts drawing mode."""
        self.roi_points = []
        self.mouse_pos = None
        self.current_roi = QPolygon()
        self.set_drawing_mode(True)
        self.setFocus()
        self.grabMouse() # Grab mouse to ensure we get events
        self.update()
        print("DEBUG: ROI Drawing Mode STARTED (Polygon)")

    def mousePressEvent(self, event):
        if self.is_drawing_roi:
            if event.button() == Qt.MouseButton.LeftButton:
                # Add Point
                pos = event.pos()
                self.roi_points.append(pos)
                print(f"DEBUG: Added Point {pos}")
                self.update()
                
            elif event.button() == Qt.MouseButton.RightButton:
                # Finish
                if len(self.roi_points) >= 3:
                    self.finish_roi()
                else:
                    print("DEBUG: Need at least 3 points.")

    def mouseMoveEvent(self, event):
        if self.is_drawing_roi:
            self.mouse_pos = event.pos()
            self.update()
            
    def finish_roi(self):
        self.releaseMouse()
        self.set_drawing_mode(False)
        self.mouse_pos = None
        
        # Create final polygon
        # Emits list of (x,y)
        points = [(p.x(), p.y()) for p in self.roi_points]
        self.roi_drawn.emit(points)
        
        # Update Visuals
        self.current_roi = QPolygon([QPoint(x, y) for x, y in points])
        self.update()
        print(f"DEBUG: ROI Finished {points}")

    def mouseReleaseEvent(self, event):
        # We don't need release event for click-based drawing
        pass

    def update_detections(self, detections):
        """
        Updates the list of detections to draw.
        detections: List of dicts from Controller/Worker
        """
        self.detections = []
        for d in detections:
            # Map detection to visual properties
            label = d.get('class', '')
            conf = d.get('conf', 0.0)
            bbox = d.get('bbox', [])
            in_roi = d.get('in_roi', False)
            
            color = QColor(0, 255, 0) # Green Default
            style = Qt.PenStyle.SolidLine
            
            # Filter logic
            if label == 'cell phone':
                color = QColor(255, 0, 0) # Red
            elif label == 'person': 
                if in_roi:
                    color = QColor(0, 255, 0) # Green inside ROI
                else:
                    continue 

            elif label == 'knife' or label == 'scissors':
                color = QColor(128, 0, 128) # Purple
            else:
                continue
            
            # Format Label
            display_label = label
            keypoints = []

            if label == 'person':
                display_label = "Persona"
                
                # FATIGUE / POSE VISUALIZATION
                fatigue = d.get('fatigue')
                if fatigue and fatigue.get('has_pose'):
                    keypoints = fatigue.get('keypoints', []) # List of (norm_x, norm_y)
                    chin_dist = fatigue.get('chin_dist', 999.0)
                    
                    # Store keypoints for drawing
                    d['keypoints'] = keypoints
                    
                    # Debug / HUD Text
                    # Show Chin Dist
                    status_text = f"H-Dist:{chin_dist:.3f}"
                    
                    if chin_dist < 0.05: # Threshold visual check
                        display_label = "CABECEO!"
                        status_text += " [ALERTA]"
                        color = QColor(255, 0, 0) # Red for Alert
                    
                    display_label += f" | {status_text}"
                         
            elif label == 'cell phone':
                display_label = "Celular"
            elif label == 'knife' or label == 'scissors':
                display_label = "ARMA"
                color = QColor(128, 0, 128) # Purple

            
            self.detections.append({
                'bbox': bbox,
                'label': display_label, 
                'color': color,
                'style': style,
                'keypoints': keypoints # Pass keypoints to drawing loop
            })
        self.update()

    def set_alert(self, text, color_name="red"):
        """Displays a large alert text."""
        self.alert_text = text
        self.alert_active = True
        
        if color_name.lower() == "red":
            self.alert_color = QColor(255, 50, 50)
        elif color_name.lower() == "yellow":
            self.alert_color = QColor(255, 255, 0)
        else:
            self.alert_color = QColor(255, 255, 255)
            
        self.update()

    def set_bucket_status(self, current, capacity):
        self.bucket_current = current
        self.bucket_capacity = capacity
        # Clean Format: Only show if active
        if current > 0.1:
            self.bucket_text = f"Tiempo Fuera: {int(current)}s"
        else:
            self.bucket_text = ""
        self.update()

    def set_aforo_status(self, current, maximum):
        self.aforo_current = current
        self.aforo_max = maximum
        self.aforo_text = f"Personas: {current} / Max: {maximum}"
        self.update()

    def set_cell_status(self, current, maximum):
        self.cell_current = current
        self.cell_max = maximum
        # Clean Format: Show in list if > 0
        if current > 0.1:
            self.cell_text = f"Celular: {current:.1f}s / {maximum}s"
        else:
            self.cell_text = "" 
        self.update()



    def set_warning_status(self, text):
        """Sets persistent warning text (e.g. Warning 1/3)."""
        self.warning_text = text
        self.update()

    def clear_alert(self):
        self.alert_active = False
        self.alert_text = ""
        self.update()

    def update_frame_dims(self, w, h):
        """
        Ensure overlay matches video dimensions.
        """
        if self.width() != w or self.height() != h:
             self.resize(w, h)

    def get_roi(self):
        """Returns the current ROI points."""
        return [(p.x(), p.y()) for p in self.roi_points]

    def paintEvent(self, event):
        # Critical Fix: Use Context Manager to ensure painter.end() is called
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 1. Draw ROI
            if self.is_drawing_roi:
                self.draw_roi_preview(painter)
            elif not self.current_roi.isEmpty():
                self.draw_roi_final(painter)

            # 2. Draw Detections
            if self.detections:
                self.draw_detections(painter)

            # 3. Draw Stats & Alerts
            self.draw_stats(painter)
            self.draw_timers(painter)

    def draw_roi_preview(self, painter):
        # Draw Points so far
        roi_color = QColor(0, 255, 255) # Cyan
        painter.setBrush(QBrush(roi_color)) 
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.roi_points:
            painter.drawEllipse(p, 4, 4)
        
        # Draw Lines connecting points
        if len(self.roi_points) > 0:
            pen = QPen(roi_color, 2, Qt.PenStyle.DashLine) 
            painter.setPen(pen)
            
            # Connect existing points
            if len(self.roi_points) > 1:
                painter.drawPolyline(QPolygon([p for p in self.roi_points]))
            
            # Rubberband to mouse
            if self.mouse_pos:
                painter.drawLine(self.roi_points[-1], self.mouse_pos)

    def draw_roi_final(self, painter):
        # Draw Final Polygon
        roi_color = QColor(0, 255, 255) # Cyan
        pen = QPen(roi_color, 2) 
        pen.setStyle(Qt.PenStyle.SolidLine)
        
        painter.setPen(pen)
        brush = QBrush(QColor(0, 255, 255, 50)) # Cyan Alpha 
        painter.setBrush(brush)
        painter.drawPolygon(self.current_roi)
        
        # Draw vertices
        painter.setBrush(QBrush(roi_color))
        for i in range(self.current_roi.count()):
            painter.drawEllipse(self.current_roi.point(i), 4, 4)

    def draw_detections(self, painter):
        w_view = self.width()
        h_view = self.height()

        for d in self.detections:
            bbox = d['bbox']
            color = d['color']
            label = d['label']
            
            # SCALING: Coords are now Normalized [0-1]
            # Unpack and Scale
            nx1, ny1, nx2, ny2 = bbox
            x1 = int(nx1 * w_view)
            y1 = int(ny1 * h_view)
            x2 = int(nx2 * w_view)
            y2 = int(ny2 * h_view)
            
            w = x2 - x1
            h = y2 - y1
            
            style = d.get('style', Qt.PenStyle.SolidLine)
            pen = QPen(color, 2)
            pen.setStyle(style)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x1, y1, w, h)
            
            # Draw Label with Background
            font = QFont("Arial", 12, QFont.Weight.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            
            # Text Dimensions
            txt_w = fm.horizontalAdvance(label) + 10
            txt_h = fm.height() + 4
            
            # Label Position (Above box, or inside top if out of bounds)
            lbl_x = x1
            lbl_y = y1 - txt_h
            if lbl_y < 0: 
                lbl_y = y1 
            
            # Draw Background Box for Label
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(lbl_x, lbl_y, txt_w, txt_h)
            
            # Draw Text (White)
            painter.setPen(QColor(255, 255, 255)) 
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Center text vertically in the label box
            painter.drawText(lbl_x + 5, lbl_y + fm.ascent() + 2, label)

            # --- POSE SKELETON DRAWING ---
            self.draw_skeleton(painter, d.get('keypoints', []), color, w_view, h_view)

    def draw_skeleton(self, painter, keypoints, color, w_view, h_view):
        if not keypoints or len(keypoints) < 7:
            return

        # 0: Nose, 5: L-Sh, 6: R-Sh
        nose = keypoints[0]
        l_sh = keypoints[5]
        r_sh = keypoints[6]
        
        # Convert to Screen Coords
        def to_screen(kp):
            return QPoint(int(kp[0] * w_view), int(kp[1] * h_view))
        
        p_nose = to_screen(nose)
        p_l_sh = to_screen(l_sh)
        p_r_sh = to_screen(r_sh)
        
        # Check validity (0,0 means not detected)
        if p_nose.x() > 0 and p_l_sh.x() > 0 and p_r_sh.x() > 0:
            # Draw Lines
            # Use same color as Box (Red if alert, Green if normal)
            pen_skel = QPen(color, 2)
            painter.setPen(pen_skel)
            
            # Shoulder Line
            painter.drawLine(p_l_sh, p_r_sh)
            
            # Nose to Mid-Shoulder
            mid_sh_x = (p_l_sh.x() + p_r_sh.x()) // 2
            mid_sh_y = (p_l_sh.y() + p_r_sh.y()) // 2
            p_mid = QPoint(mid_sh_x, mid_sh_y)
            
            painter.drawLine(p_nose, p_mid)
            
            # Draw Points
            painter.setBrush(QBrush(QColor(255, 255, 0))) # Yellow Joints
            r = 4
            painter.drawEllipse(p_nose, r, r)
            painter.drawEllipse(p_l_sh, r, r)
            painter.drawEllipse(p_r_sh, r, r)

    def draw_stats(self, painter):
        # Draw Stats (Top Left)
        y_pos = 30
        font_stats = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font_stats)

        # 1. Aforo (Keep at Top Left)
        if hasattr(self, 'aforo_text'):
             # Color: Red if violation, else Green?
             color = QColor(0, 255, 0)
             if hasattr(self, 'aforo_current') and hasattr(self, 'aforo_max'):
                 if self.aforo_current > self.aforo_max:
                     color = QColor(255, 0, 0)
             
             painter.setPen(color)
             painter.drawText(10, y_pos, self.aforo_text)
             y_pos += 25

        # Draw Alert
        if self.alert_active and self.alert_text:
            painter.setPen(self.alert_color)
            font = QFont("Arial", 48, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Draw Centered
            rect = self.rect()
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.alert_text)

    def draw_timers(self, painter):
        # Draw Timers (Bottom Right) - ALWAYS ON TOP
        timers_to_show = []
        if hasattr(self, 'bucket_text') and self.bucket_text:
            color = QColor(255, 255, 0) # Yellow
            timers_to_show.append((self.bucket_text, color)) 
            
        if hasattr(self, 'cell_text') and self.cell_text:
            color = QColor(255, 165, 0) # Orange
            timers_to_show.append((self.cell_text, color))
            
        if timers_to_show:
            font_timer = QFont("Arial", 16, QFont.Weight.Bold)
            painter.setFont(font_timer)
            
            # Box dimensions
            box_w = 300
            box_h = 20 + (len(timers_to_show) * 35)
            x_box = self.width() - box_w - 20
            y_box = self.height() - box_h - 20
            
            # Draw Background
            painter.fillRect(x_box, y_box, box_w, box_h, QColor(0, 0, 0, 180)) # Semi-transparent Black
            
            # Draw Text
            y_text = y_box + 30
            for text, color in timers_to_show:
                painter.setPen(color)
                painter.drawText(x_box + 15, y_text, text)
                y_text += 35
