# Archivo: ui/main_window.py (o main.py si ejecutas desde raíz)
import sys
import random
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QSpinBox, QRadioButton, QButtonGroup, QMessageBox, QStackedLayout,
    QApplication, QSizePolicy, QCheckBox, QListWidget, QListWidgetItem,
    QInputDialog
)
# Ajuste de rutas para importar desde la misma carpeta o paquete ui
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..')) # Parent dir
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Insert at 0 to prioritize
sys.path.append(current_dir)

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QImage, QPixmap
from config.settings import Settings
import cv2

# winsound is Windows-only; import conditionally to keep the app portable
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    from ui.overlay import VideoOverlay
except ImportError:
    # Fallback si están en la misma carpeta
    from overlay import VideoOverlay

from data.db import DBManager

# --- Add Camera Dialog ---
class AddCameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Cámara")
        self.resize(400, 200)
        self.layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Cámara Entrada")
        form_layout.addRow("Nombre:", self.name_input)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("rtsp://...")
        form_layout.addRow("URL RTSP:", self.url_input)
        
        self.layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def get_data(self):
        return self.name_input.text().strip(), self.url_input.text().strip()

# --- Configuration Dialog ---
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Sistema")
        self.setModal(True)
        self.resize(450, 400)
        self.layout = QVBoxLayout(self)
        self.settings = Settings() # Load Settings
        self.auth_passed = False
        self.init_auth_ui()
        
    def init_auth_ui(self):
        self.clear_layout()
        self.pass_label = QLabel("Ingrese Contraseña de Administrador:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = QPushButton("Acceder")
        self.login_btn.clicked.connect(self.check_password)
        
        self.layout.addWidget(self.pass_label)
        self.layout.addWidget(self.pass_input)
        self.layout.addWidget(self.login_btn)
        self.layout.addStretch()

    def init_settings_ui(self):
        self.clear_layout()
        form_layout = QFormLayout()

        # --- 1. Aforo Control (Top) ---
        self.aforo_cb = QCheckBox("Habilitar Control de Aforo")
        self.aforo_cb.setChecked(self.settings.enable_aforo)
        self.aforo_cb.toggled.connect(self.toggle_aforo_input)
        form_layout.addRow("Control de Aforo:", self.aforo_cb)
        
        # New: Max People Limit
        self.max_people_input = QSpinBox()
        self.max_people_input.setRange(1, 20)
        self.max_people_input.setValue(int(self.settings.max_people))
        self.max_people_input.setSuffix(" pers")
        self.max_people_input.setEnabled(self.settings.enable_aforo)
        form_layout.addRow("Máximo de Personas:", self.max_people_input)

        self.t_aforo_input = QSpinBox()
        self.t_aforo_input.setRange(0, 999)
        self.t_aforo_input.setValue(int(self.settings.t_aforo))
        self.t_aforo_input.setSuffix(" s")
        self.t_aforo_input.setEnabled(self.settings.enable_aforo)
        form_layout.addRow("Tiempo Límite Aforo:", self.t_aforo_input)

        # --- 1.5 Abandonment Control ---
        self.abandonment_cb = QCheckBox("Habilitar Detección Abandono")
        self.abandonment_cb.setChecked(self.settings.enable_abandonment)
        self.abandonment_cb.toggled.connect(self.toggle_abandonment_input)
        form_layout.addRow("Abandono de Puesto:", self.abandonment_cb)

        self.t_abandonment_input = QSpinBox()
        self.t_abandonment_input.setRange(0, 999)
        self.t_abandonment_input.setValue(int(self.settings.t_abandonment))
        self.t_abandonment_input.setSuffix(" s")
        self.t_abandonment_input.setEnabled(self.settings.enable_abandonment)
        form_layout.addRow("Tiempo Límite Abandono:", self.t_abandonment_input)



        # --- 2. Cell Phone Policy ---
        self.policy_group = QButtonGroup(self)
        self.radio_strict = QRadioButton("Estricto")
        self.radio_continuous = QRadioButton("Continuo")
        self.radio_accumulated = QRadioButton("Acumulado")
        
        # Set default based on settings
        current_policy = getattr(self.settings, 'cell_policy', 'continuous')
        if current_policy == 'strict':
            self.radio_strict.setChecked(True)
        elif current_policy == 'accumulated':
            self.radio_accumulated.setChecked(True)
        else:
            self.radio_continuous.setChecked(True)
        
        self.policy_group.addButton(self.radio_strict)
        self.policy_group.addButton(self.radio_continuous)
        self.policy_group.addButton(self.radio_accumulated)
        
        policy_layout = QHBoxLayout()
        policy_layout.addWidget(self.radio_strict)
        policy_layout.addWidget(self.radio_continuous)
        policy_layout.addWidget(self.radio_accumulated)
        
        form_layout.addRow("Política Celular:", policy_layout)

        # --- 3. Time Settings (T1, T2) ---
        self.t1_input = QSpinBox()
        self.t1_input.setRange(0, 999)
        self.t1_input.setValue(int(self.settings.t1_continuous))
        self.t1_input.setSuffix(" s")
        form_layout.addRow("Tiempo Continuo (T1):", self.t1_input)

        self.t2_input = QSpinBox()
        self.t2_input.setRange(0, 999)
        self.t2_input.setValue(int(self.settings.t2_cumulative))
        self.t2_input.setSuffix(" s")
        form_layout.addRow("Tiempo Acumulado (T2):", self.t2_input)
        
        # --- 4. Notification Management ---
        from PyQt6.QtWidgets import QGroupBox
        self.notif_group = QGroupBox("Gestión de Notificaciones")
        notif_layout = QFormLayout()
        
        self.direct_alert_cb = QCheckBox("Alerta Directa al Supervisor")
        self.direct_alert_cb.setChecked(getattr(self.settings, 'notification_direct_alert', False))
        
        self.warning_mode_cb = QCheckBox("Modo Advertencias")
        self.warning_mode_cb.setChecked(getattr(self.settings, 'notification_warning_mode', True))
        
        # Mutual Exclusion Logic Connections
        self.direct_alert_cb.toggled.connect(self.on_direct_alert_toggled)
        self.warning_mode_cb.toggled.connect(self.on_warning_mode_toggled)

        notif_layout.addRow(self.direct_alert_cb)
        notif_layout.addRow(self.warning_mode_cb)
        
        self.warning_limit_input = QSpinBox()
        self.warning_limit_input.setRange(1, 10)
        self.warning_limit_input.setValue(getattr(self.settings, 'notification_warning_limit', 3))
        notif_layout.addRow("Límite de Advertencias:", self.warning_limit_input)
        
        self.reduction_time_input = QSpinBox()
        self.reduction_time_input.setRange(1, 999)
        self.reduction_time_input.setValue(getattr(self.settings, 'notification_reduction_time', 60))
        self.reduction_time_input.setSuffix(" min")
        notif_layout.addRow("Tiempo de Reducción:", self.reduction_time_input)
        
        # Initial State Update logic for inputs
        self.toggle_warning_input(self.warning_mode_cb.isChecked())
        # Re-connect toggle to enable/disable inputs
        self.warning_mode_cb.toggled.connect(self.toggle_warning_input)
        
        self.notif_group.setLayout(notif_layout)
        self.layout.addWidget(self.notif_group)

        # --- 5. Fatigue Detection ---
        self.fatigue_group = QGroupBox("Detector de Fatiga y Sueño")
        fatigue_layout = QFormLayout()
        
        self.fatigue_cb = QCheckBox("Habilitar Monitor de Sueño")
        self.fatigue_cb.setChecked(getattr(self.settings, 'enable_fatigue', False))
        
        self.fatigue_policy_safe = QRadioButton("Modo Advertencia (Vidas)")
        self.fatigue_policy_crit = QRadioButton("Modo Crítico (Inmediato)")
        self.fatigue_policy_group = QButtonGroup()
        self.fatigue_policy_group.addButton(self.fatigue_policy_safe)
        self.fatigue_policy_group.addButton(self.fatigue_policy_crit)
        
        current_fatigue_policy = getattr(self.settings, 'fatigue_policy', 'warning')
        if current_fatigue_policy == 'critical':
            self.fatigue_policy_crit.setChecked(True)
        else:
            self.fatigue_policy_safe.setChecked(True)
            
        fatigue_layout.addRow(self.fatigue_cb)
        fatigue_layout.addRow(self.fatigue_policy_safe)
        fatigue_layout.addRow(self.fatigue_policy_crit)
        
        self.fatigue_group.setLayout(fatigue_layout)
        self.layout.addWidget(self.fatigue_group)

        self.layout.addLayout(form_layout)

        # --- 6. Telegram Notifications ---
        from PyQt6.QtWidgets import QGroupBox
        self.telegram_group = QGroupBox("Notificaciones Telegram")
        telegram_layout = QFormLayout()

        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_token_input.setPlaceholderText("123456789:ABCdef...")
        self.telegram_token_input.setText(getattr(self.settings, "telegram_token", ""))
        telegram_layout.addRow("Bot Token:", self.telegram_token_input)

        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("-100123456789")
        self.telegram_chat_id_input.setText(getattr(self.settings, "telegram_chat_id", ""))
        telegram_layout.addRow("Chat ID:", self.telegram_chat_id_input)

        test_telegram_btn = QPushButton("▶ Probar Conexión")
        test_telegram_btn.clicked.connect(self.test_telegram)
        telegram_layout.addRow(test_telegram_btn)

        self.telegram_group.setLayout(telegram_layout)
        self.layout.addWidget(self.telegram_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def test_telegram(self):
        """Sends a test message via the credentials currently typed in the dialog."""
        from services.telegram import TelegramService
        token = self.telegram_token_input.text().strip()
        chat_id = self.telegram_chat_id_input.text().strip()
        svc = TelegramService(token=token, chat_id=chat_id)
        if not svc.is_configured():
            QMessageBox.warning(self, "Telegram", "Token o Chat ID inválido.\nRevisa los valores ingresados.")
            return
        ok = svc.send_test_message()
        if ok:
            QMessageBox.information(self, "Telegram", "✅ Mensaje de prueba enviado correctamente.")
        else:
            QMessageBox.critical(self, "Telegram", "❌ Error al enviar.\nVerifica el token y el Chat ID.")

    def on_direct_alert_toggled(self, checked):
        if checked:
            self.warning_mode_cb.setChecked(False)

    def on_warning_mode_toggled(self, checked):
        if checked:
            self.direct_alert_cb.setChecked(False)
        self.toggle_warning_input(checked)

    def toggle_aforo_input(self, checked):
        self.t_aforo_input.setEnabled(checked)
        self.max_people_input.setEnabled(checked)

    def toggle_abandonment_input(self, checked):
        self.t_abandonment_input.setEnabled(checked)
        
    def toggle_warning_input(self, checked):
        self.warning_limit_input.setEnabled(checked)
        self.reduction_time_input.setEnabled(checked)

    def check_password(self):
        import hashlib
        from data.db import DBManager
        entered = self.pass_input.text()
        entered_hash = hashlib.sha256(entered.encode("utf-8")).hexdigest()
        stored_hash = DBManager().get_settings("admin_password_hash", "")
        if entered_hash and entered_hash == stored_hash:
            self.auth_passed = True
            self.init_settings_ui()
        else:
            QMessageBox.warning(self, "Error", "Contraseña Incorrecta")

    def save_and_accept(self):
        # Save values to singleton Settings
        self.settings.update("t1_continuous", self.t1_input.value())
        self.settings.update("t2_cumulative", self.t2_input.value())
        self.settings.update("enable_aforo", self.aforo_cb.isChecked())
        self.settings.update("max_people", self.max_people_input.value()) # NEW
        self.settings.update("t_aforo", self.t_aforo_input.value())
        self.settings.update("enable_abandonment", self.abandonment_cb.isChecked())
        self.settings.update("t_abandonment", self.t_abandonment_input.value())
        
        # Save New Settings (Notifications)
        self.settings.update("notification_direct_alert", self.direct_alert_cb.isChecked())
        self.settings.update("notification_warning_mode", self.warning_mode_cb.isChecked())
        self.settings.update("notification_warning_limit", self.warning_limit_input.value())
        self.settings.update("notification_reduction_time", self.reduction_time_input.value())
        
        # Save Cell Policy
        policy = "continuous"
        if self.radio_strict.isChecked(): policy = "strict"
        elif self.radio_accumulated.isChecked(): policy = "accumulated"
        self.settings.update("cell_policy", policy)

        # Save Fatigue Settings
        self.settings.update("enable_fatigue", self.fatigue_cb.isChecked())
        fatigue_pol = "warning"
        if self.fatigue_policy_crit.isChecked():
            fatigue_pol = "critical"
        self.settings.update("fatigue_policy", fatigue_pol)
        
        # Save Telegram credentials
        self.settings.update("telegram_token", self.telegram_token_input.text().strip())
        self.settings.update("telegram_chat_id", self.telegram_chat_id_input.text().strip())

        # Config changed notification (no restart needed for video here anymore)
        if self.parent() and hasattr(self.parent(), 'on_config_changed'):
            self.parent().on_config_changed(restart_video=False)

        self.accept()

    def clear_layout(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

# --- Camera List Widget ---
class CameraListWidget(QWidget):
    camera_selected = pyqtSignal(str, str) # Emits (Name, RTSP URL) - for double-click/connect
    camera_clicked = pyqtSignal(str, str)  # Emits (Name, RTSP URL) - for single-click/select
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("CÁMARAS")
        title.setStyleSheet("color: #00ffff; font-weight: bold;") 
        header.addWidget(title)
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 30)
        # Professional Style logic used to call global QSS unless filtered.
        # But we want specific blue button here probably.
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
        """)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_camera)
        header.addWidget(add_btn)
        
        self.layout.addLayout(header)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #383838; color: white; border: 1px solid #555;")
        self.list_widget.itemClicked.connect(self.on_single_click)      # Single click = select
        self.list_widget.itemDoubleClicked.connect(self.on_double_click) # Double click = connect
        self.layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        cameras = self.db.get_cameras()
        for cam_id, name, url in cameras:
            # Custom Widget for Item
            item_widget = QWidget()
            item_widget.setStyleSheet("background-color: transparent;") 
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 4, 5, 4)
            item_layout.setSpacing(8)
            
            # Status Indicator
            status_indicator = QLabel("●")
            status_indicator.setFixedWidth(12)
            status_indicator.setStyleSheet("color: #666; font-size: 10px;")  # Gray default
            status_indicator.setObjectName("status_indicator")
            item_layout.addWidget(status_indicator)
            
            # Camera Name
            label = QLabel(f"{name}")
            label.setStyleSheet("color: white;") 
            item_layout.addWidget(label)
            
            item_layout.addStretch()
            
            # Delete Button
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: #aaa;
                    border: none;
                    border-radius: 3px;
                    font-size: 10px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #c62828;
                    color: white;
                }
            """)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, cid=cam_id: self.delete_camera(cid))
            item_layout.addWidget(del_btn)
            
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, url)
            item.setData(Qt.ItemDataRole.UserRole + 1, name)
            
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)
    
    def set_active_camera(self, active_url):
        """Updates status indicators."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_url = item.data(Qt.ItemDataRole.UserRole)
            item_widget = self.list_widget.itemWidget(item)
            
            if item_widget:
                indicator = item_widget.findChild(QLabel, "status_indicator")
                if indicator:
                    if item_url == active_url:
                        indicator.setStyleSheet("color: #00ff00; font-size: 10px;")  # Green Active
                    else:
                        indicator.setStyleSheet("color: #666; font-size: 10px;")  # Gray Inactive
    
    def clear_active_indicators(self):
        """Resets all indicators to gray (no active camera)."""
        self.set_active_camera(None)
            
    def delete_camera(self, cam_id):
        reply = QMessageBox.question(
            self, "Confirmar", "¿Eliminar esta cámara?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_camera(cam_id):
                self.refresh_list()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la cámara.")

    def add_camera(self):
        dialog = AddCameraDialog(self)
        if dialog.exec():
            name, url = dialog.get_data()
            if name and url:
                if self.db.add_camera(name, url):
                    self.refresh_list()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo agregar la cámara.")
            else:
                QMessageBox.warning(self, "Error", "Campos obligatorios.")

    def on_single_click(self, item):
        """Single click = select camera (store for later connection)"""
        url = item.data(Qt.ItemDataRole.UserRole)
        name = item.data(Qt.ItemDataRole.UserRole + 1)
        if url and name:
            self.camera_clicked.emit(name, url)

    def on_double_click(self, item):
        """Double click = connect immediately"""
        url = item.data(Qt.ItemDataRole.UserRole)
        name = item.data(Qt.ItemDataRole.UserRole + 1)
        if url and name:
            self.camera_selected.emit(name, url)

# --- Main Window ---
class MainWindow(QMainWindow):
    # Signal for switching camera (proxied from sidebar)
    request_switch_camera = pyqtSignal(str)
    
    # Signal for stopping video
    # Signal for stopping video
    request_stop_video = pyqtSignal()
    
    # Signal for restarting video from ConfigDialog
    request_restart_video = pyqtSignal()

    # Signal for ROI updates (mapped to image coords)
    roi_updated = pyqtSignal(list)
    
    # Signal for clearing ROI
    clear_roi_signal = pyqtSignal()
    
    # Signal for accepting warning (Warning Type)
    warning_accepted_signal = pyqtSignal(str)

    def __init__(self):

        super().__init__()
        self.setWindowTitle("DeepVision System - Monitoring Station")
        self.resize(1280, 720)

        # CENTER WINDOW ON STARTUP
        # Force strict centering to avoid "Out of Bounds" issues
        if self.screen():
            screen_geometry = self.screen().availableGeometry()
            center_x = (screen_geometry.width() - self.width()) // 2
            center_y = (screen_geometry.height() - self.height()) // 2
            
            # Ensure positive coordinates
            center_x = max(0, center_x)
            center_y = max(0, center_y)
            
            self.move(center_x, center_y)
        
        # Connect internal signal
        self.roi_updated.connect(self.on_roi_drawn_ui)

        
        # Database Manager
        self.db_manager = DBManager()

        # Audio
        self.sound_enabled = True
        
        # State
        self.last_active_url = None
        self.last_active_name = None
        self.is_connected = False
        self.is_boca_mode = False
        
        self.apply_styles()
        self.setup_ui()
        
    # ...

    @pyqtSlot(list)
    def on_roi_drawn(self, ui_points):
        """Maps UI coordinates to Image coordinates and emits signal."""
        if not hasattr(self, 'last_frame_size') or not self.last_frame_size:
            print("WARNING: No frame size known, cannot map ROI.")
            return

        fw, fh = self.last_frame_size
        lw, lh = self.video_label.width(), self.video_label.height()
        
        if fw == 0 or fh == 0: return
        
        # Calculate how image is scaled/positioned in label (KeepAspectRatio)
        scale = min(lw / fw, lh / fh)
        nw = fw * scale
        nh = fh * scale
        
        # Offsets (Center alignment)
        off_x = (lw - nw) / 2
        off_y = (lh - nh) / 2
        
        mapped_points = []
        for (ux, uy) in ui_points:
            # Inverse transform: (ui - offset) / scale
            ix = (ux - off_x) / scale
            iy = (uy - off_y) / scale
            
            # Clamp to frame limits
            ix = max(0, min(fw, ix))
            iy = max(0, min(fh, iy))
            
            mapped_points.append((ix, iy))
        
        self.roi_updated.emit(mapped_points)

    @pyqtSlot(object)
    def update_frame(self, frame):
        """Receives frame from Controller/VideoThread."""
        try:
            # OPTIMIZATION: Resize for UI Display (reduce lag on 4K cams)
            # Keep original 'frame' for AI, but resize 'display_frame'
            target_h = 720
            h_orig, w_orig = frame.shape[:2]
            scale_ratio = target_h / float(h_orig)
            target_w = int(w_orig * scale_ratio)
            
            display_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
            
            h, w, ch = display_frame.shape
            self.last_frame_size = (w, h) # Store DISPLAY dims for ROI mapping
            bytes_per_line = ch * w
            
            rgb_frame = display_frame[:, :, ::-1].copy() # BGR to RGB
            qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)
            
            # Scale to fit label
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
            
            # Update Overlay dims
            self.overlay.update_frame_dims(w, h)
            
            # Update Status and Button if connection just succeeded
            if not self.is_connected:
                self.is_connected = True
                
                # Cancel connection timeout timer
                if hasattr(self, 'connection_timer') and self.connection_timer.isActive():
                    self.connection_timer.stop()
                
                # Update status label
                if self.last_active_name:
                    self.status_camera.setText(f"● Cámara: {self.last_active_name}")
                else:
                    self.status_camera.setText("● Cámara: CONECTADA")
                self.status_camera.setStyleSheet("color: #F2A900; font-size: 14px;") # Gold
                
                # Update Button to 'Disconnect' state
                self.toggle_btn.setText("Desconectar Cámara")
                # Style remains global
                
                # Update camera list indicator to green
                if self.last_active_url:
                    self.camera_list.set_active_camera(self.last_active_url)

        except Exception as e:
            import logging
            logging.getLogger("DeepVision.UI").error(f"Error updating frame: {e}")

    def apply_styles(self):
        # Industrial Dark Mode (PROFESSIONAL DEFAULT)
        qss = """
        QMainWindow { background-color: #2b2b2b; }
        QLabel { color: #e0e0e0; font-family: 'Segoe UI', Arial; }
        QTableWidget { background-color: #383838; color: #ffffff; border: 1px solid #555; }
        QHeaderView::section { background-color: #444; color: #00ffff; padding: 4px; border: 1px solid #555; }
        
        /* Default Button Style */
        QPushButton { 
            background-color: #005f73; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            font-weight: bold; 
        }
        QPushButton:hover { background-color: #0a9396; }
        
        QLineEdit { background-color: #222; color: #fff; border: 1px solid #555; padding: 4px; }
        QDialog { background-color: #333; color: #fff; }
        """
        self.setStyleSheet(qss)



    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Sidebar (Left) ---
        sidebar_panel = QFrame()
        sidebar_panel.setFixedWidth(200)
        sidebar_panel.setStyleSheet("background-color: #252525; border-right: 1px solid #444;")
        sidebar_layout = QVBoxLayout(sidebar_panel)
        
        self.camera_list = CameraListWidget(self.db_manager)
        self.camera_list.camera_selected.connect(self.on_camera_selected)   # Double-click = connect
        self.camera_list.camera_clicked.connect(self.on_camera_clicked)     # Single-click = select
        
        sidebar_layout.addWidget(self.camera_list)
        main_layout.addWidget(sidebar_panel)

        # --- Video Area (Center) ---
        video_container = QWidget()
        video_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        video_container.setSizePolicy(video_policy)
        
        self.video_stack = QStackedLayout(video_container)
        self.video_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Layer 1: Placeholder Video
        self.video_label = QLabel("NO SIGNAL")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; color: #e0e0e0; font-size: 24px; font-weight: bold;")
        self.video_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Allow clicks to pass through to overlay? 
        # Actually overlay is ON TOP (index 1), so overlay gets it first. 
        # But just in case.
        self.video_stack.addWidget(self.video_label)
        
        # Layer 2: Overlay
        self.overlay = VideoOverlay()
        self.overlay.roi_drawn.connect(self.on_roi_drawn) # Connect locally for mapping
        self.video_stack.addWidget(self.overlay)
        
        main_layout.addWidget(video_container, stretch=3)
        
        # --- Dashboard ---
        dashboard_panel = QFrame()
        dashboard_panel.setFixedWidth(350)
        dashboard_panel.setStyleSheet("background-color: #333; border-left: 2px solid #444;")
        dash_layout = QVBoxLayout(dashboard_panel)
        
        title = QLabel("PANEL DE CONTROL")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #00ffff; margin-bottom: 20px;")
        dash_layout.addWidget(title)
        
        self.status_system = QLabel("● Sistema: ONLINE")
        self.status_system.setStyleSheet("color: #00ff00; font-size: 14px;") # Green
        self.status_camera = QLabel("● Cámara: DESCONECTADA")
        self.status_camera.setStyleSheet("color: #ff0000; font-size: 14px;") # Red
        
        dash_layout.addWidget(self.status_system)

        dash_layout.addWidget(self.status_camera)
        
        # Toggle Connection Button
        self.toggle_btn = QPushButton("Conectar Cámara")
        self.toggle_btn.setStyleSheet("background-color: #2e7d32; margin-top: 5px;") # Green default
        self.toggle_btn.clicked.connect(self.toggle_connection)
        dash_layout.addWidget(self.toggle_btn)
        
        dash_layout.addSpacing(20)

        
        log_label = QLabel("Log de Eventos")
        log_label.setStyleSheet("color: #aaa; font-size: 12px;")
        dash_layout.addWidget(log_label)
        
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(2)
        self.log_table.setHorizontalHeaderLabels(["Hora", "Evento"])
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setAlternatingRowColors(True)
        dash_layout.addWidget(self.log_table)
        
        self.config_btn = QPushButton("⚙ Configuración")
        self.config_btn.clicked.connect(self.open_config)
        dash_layout.addWidget(self.config_btn)
        

        
        self.roi_btn = QPushButton("⛛ Dibujar ROI")
        self.roi_btn.setStyleSheet("background-color: #444;")
        self.roi_btn.clicked.connect(self.toggle_roi_action)
        dash_layout.addWidget(self.roi_btn)
        
        # Removed separate Clear ROI button
        
        main_layout.addWidget(dashboard_panel, stretch=1)

    @pyqtSlot(str, str)
    def on_camera_selected(self, name, url):

        """Updates status and requests camera switch."""
        self.last_active_name = name
        self.last_active_url = url
        # Don't set is_connected=True yet - wait for actual frames
        
        self.status_camera.setText(f"● Cámara: {name} (Conectando...)")
        self.status_camera.setStyleSheet("color: #ffaa00; font-size: 14px;") # Orange for "connecting"
        
        # Start 5-second connection timeout
        if not hasattr(self, 'connection_timer'):
            self.connection_timer = QTimer(self)
            self.connection_timer.setSingleShot(True)
            self.connection_timer.timeout.connect(self.on_connection_timeout)
        self.connection_timer.start(5000)  # 5 seconds
        
        self.request_switch_camera.emit(url)
    
    def on_connection_timeout(self):
        """Called if connection fails after 5 seconds."""
        if not self.is_connected:
            QMessageBox.warning(
                self, 
                "Error de Conexión", 
                "No se pudo conectar a la cámara.\nVerifique la URL RTSP o la red."
            )
            # Restore UI to disconnected state
            self.status_camera.setText("● Cámara: DESCONECTADA")
            self.status_camera.setStyleSheet("color: #ff0000; font-size: 14px;")
            self.toggle_btn.setText("Conectar Cámara")
            if not self.is_connected:
                 self.toggle_btn.setStyleSheet("background-color: #2e7d32; margin-top: 5px;") # Green

    @pyqtSlot(str, str)
    def on_camera_clicked(self, name, url):
        """Single-click on camera = store selection for later connection via button."""
        self.selected_camera_name = name
        self.selected_camera_url = url
        self.status_camera.setText(f"● Seleccionada: {name}")
        self.status_camera.setStyleSheet("color: #ffaa00; font-size: 14px;")  # Orange = selected

    @pyqtSlot()
    def toggle_connection(self):
        """Toggles between connecting to selected/last camera and disconnecting."""
        # Priority 1: If connected, disconnect immediately
        if self.is_connected:
            self.request_stop_video.emit()
            return
        
        # Priority 2: Try to connect using selected camera (single-click)
        if hasattr(self, 'selected_camera_url') and self.selected_camera_url:
            self.on_camera_selected(self.selected_camera_name, self.selected_camera_url)
            return
        
        # Priority 3: Fall back to last active camera (reconnect)
        if self.last_active_url:
            self.on_camera_selected(self.last_active_name, self.last_active_url)
            return
        
        # No camera available
        QMessageBox.information(self, "Información", "Seleccione una cámara de la lista primero.")

    def open_config(self):
        dialog = ConfigDialog(self)
        dialog.exec()

    @pyqtSlot()
    def toggle_roi_action(self):
        """Toggles between starting ROI drawing and clearing existing ROI."""
        if getattr(self, 'is_roi_active', False):
             self.clear_roi_handler()
        else:
             self.start_roi_tool()

    def start_roi_tool(self):
        # Activa el modo dibujo y fuerza el foco al overlay para que reciba el mouse
        self.overlay.start_drawing_roi()
        self.overlay.raise_() 
        self.overlay.setFocus()
        self.log_event("SISTEMA", "Modo dibujo ROI activado (Click Izq: Puntos, Doble Click: Terminar)")

    @pyqtSlot()
    def clear_roi_handler(self):
        """Clears ROI from Overlay and Controller."""
        self.overlay.clear_roi_visuals()
        self.clear_roi_signal.emit()
        self.log_event("SISTEMA", "ROI eliminado por usuario.")
        
        # Reset Button State
        self.is_roi_active = False
        self.roi_btn.setText("⛛ Dibujar ROI")
        if not self.is_boca_mode:
            self.roi_btn.setStyleSheet("background-color: #444;")

    @pyqtSlot(list)
    def on_roi_drawn_ui(self, coords):
        """Called when ROI drawing is finished."""
        if coords:
            self.is_roi_active = True
            self.roi_btn.setText("🟥 Borrar ROI")
            
    @pyqtSlot(str, str)
    def show_blocking_warning(self, warning_type, message):
        """
        Displays a MODAL blocking warning.
        Stops user interaction until acknowledged.
        """
        self.log_event("ADVERTENCIA", f"Bloqueo por {warning_type}")

        # Play Sound (Windows only)
        if self.sound_enabled and WINSOUND_AVAILABLE:
            winsound.Beep(1000, 500)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚠️ LLAMADO DE ATENCIÓN ⚠️")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Warning)

        btn_accept = msg_box.addButton("Aceptar y Continuar", QMessageBox.ButtonRole.AcceptRole)
        msg_box.setDefaultButton(btn_accept)

        msg_box.setStyleSheet("""
            QMessageBox { background-color: #330000; color: white; }
            QLabel { color: white; font-size: 14px; font-weight: bold; }
            QPushButton { background-color: #d32f2f; color: white; border: 2px solid white; padding: 10px; font-weight: bold; }
            QPushButton:hover { background-color: #b71c1c; }
        """)

        # BLOCKING CALL — waits for user to click
        msg_box.exec()

        self.log_event("SISTEMA", "Usuario confirmó advertencia. Reanudando...")

        # Signal LogicWorker to resume (connected in main.py)
        self.warning_accepted_signal.emit(warning_type)

    def log_event(self, time_str, message):
        import logging
        logging.getLogger("DeepVision.UI").info(f"[{time_str}] {message}")
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        self.log_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.log_table.setItem(row, 1, QTableWidgetItem(message))
        self.log_table.scrollToBottom()
        
        # Limit rows to prevent memory/layout issues
        if self.log_table.rowCount() > 100:
            self.log_table.removeRow(0)

    def on_config_changed(self, restart_video):
        """Called by ConfigDialog when settings are saved."""
        self.log_event("CONFIG", "Configuración actualizada.")
        if restart_video:
            self.request_restart_video.emit()

    @pyqtSlot()
    def reset_video_ui(self):
        """Resets the video area to 'No Signal' state. Called when video stops."""
        self.is_connected = False
        
        # Force clear and repaint video area
        self.video_label.clear()
        self.video_label.setText("NO SIGNAL")
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 24px; font-weight: bold;")
        self.video_label.repaint()  # Force immediate repaint
        
        # Update status label
        self.status_camera.setText("● Cámara: DESCONECTADA")
        self.status_camera.setStyleSheet("color: #ff0000; font-size: 14px;")
        
        # Update Button to 'Connect' state (Green)
        self.toggle_btn.setText("Conectar Cámara")
        self.toggle_btn.setStyleSheet("background-color: #2e7d32; margin-top: 5px;")
        
        # Reset ALL camera list indicators to gray
        self.camera_list.clear_active_indicators()



    @pyqtSlot(list)
    def update_detections(self, detections):
        """Receives detections list from Controller."""
        self.overlay.update_detections(detections)

    @pyqtSlot(float, float)
    def update_bucket_status(self, current, capacity):
        """Actualiza la visualización del bucket de abandono en el overlay."""
        self.overlay.set_bucket_status(current, capacity)

    @pyqtSlot(str, str, str)
    def handle_alarm(self, level, type, message):
        """Receives alarm signal from Controller."""
        
        # 0. Log full raw message for audit
        self.log_event("ALERTA", f"[{level}] {type}: {message}")
        
        # 1. Format Message for Overlay (Professional Look)
        display_msg = type.upper()
        if "CELULAR" in type.upper():
            display_msg = "USO DE CELULAR"
        elif "ABANDONO" in type.upper():
            display_msg = "ABANDONO DE PUESTO"
            
        # 2. Handle Persistent Warnings (Overlay Text)
        if level == "WARNING":
            # Extract count if present (e.g. "Advertencia 1/3") 
            # Logic sends: "Uso continuo... (Advertencia 1/3)"
            count_str = "?/3"
            if "(" in message and ")" in message:
                start = message.rfind("(")
                end = message.rfind(")")
                # Extract "Advertencia 1/3" -> take only "1/3"? 
                # User wants "ADVERTENCIA (X/3)"
                # Let's try to parse "Advertencia 1/3"
                content = message[start+1:end] # "Advertencia 1/3"
                parts = content.split()
                if len(parts) > 1:
                    count_str = parts[-1] # "1/3"
            
            final_text = f"⚠ ADVERTENCIA ({count_str})"
            self.overlay.set_warning_status(final_text)
            
            # Optional: Small beep (Windows only)
            if self.sound_enabled and WINSOUND_AVAILABLE:
                import threading
                threading.Thread(
                    target=lambda: winsound.Beep(800, 100), daemon=True
                ).start()
            return

        # 3. Handle Major Alarms (CRITICAL / ALARM)
        color = "red" if level == "CRITICAL" else "orange"
        
        # TRANSFORMATION: "Escalado" -> "Notificando Supervisor"
        alert_text = f"🚨 {display_msg} 🚨"
        
        if level == "CRITICAL" or "ESCALADO" in type.upper():
             alert_text = "🚨 NOTIFICANDO SUPERVISOR 🚨"
        elif level == "ALARM":
             alert_text = display_msg 
        
        self.overlay.set_alert(alert_text, color)

        
        # Sound Alert (Windows only)
        if self.sound_enabled and WINSOUND_AVAILABLE:
            import threading
            threading.Thread(
                target=lambda: winsound.Beep(1000, 200), daemon=True
            ).start()


        
        # Clear visual alert after 3 seconds
        
        # Clear visual alert after 3 seconds
        QTimer.singleShot(3000, self.overlay.clear_alert)

# --- DO NOT RUN DIRECTLY ---
# Use main.py as the single entry point
if __name__ == "__main__":
    print("ERROR: Do not run main_window.py directly.")
    print("       Use: python main.py")
    import sys
    sys.exit(1)
