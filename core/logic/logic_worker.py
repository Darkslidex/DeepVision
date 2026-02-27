import math
import time

from PyQt6.QtCore import pyqtSignal, pyqtSlot

from core.worker import BaseWorker
from core.logic.leaky_bucket import LeakyBucket  # Available for future use
from config.settings import Settings


class LogicWorker(BaseWorker):
    """
    Procesa las detecciones para determinar si se disparan alarmas.
    Maneja la lógica de "Abandono de puesto" y uso de celular con políticas avanzadas.
    """
    alarm_signal = pyqtSignal(str, str, str)    # Level, Type, Message
    bucket_status_signal = pyqtSignal(float, float)  # Current, Capacity
    aforo_status_signal = pyqtSignal(int, int)   # Current Count, Max Count
    cell_status_signal = pyqtSignal(float, float)    # Current Time, Max Time
    warning_signal = pyqtSignal(str, str)        # Type, Message (For Blocking Modal)

    def __init__(self):
        super().__init__(name="LogicWorker")
        self.settings = Settings()

        from core.notification_service import NotificationService
        self.notifier = NotificationService()

        # Blocking State
        self.is_paused_for_warning = False

        # Abandonment
        self.abandonment_time_accumulated = 0.0
        self.last_process_time = time.time()
        self.last_abandonment_notification = 0.0

        # Cell Phone
        self.cell_time_continuous = 0.0          # For "Strict" and "Continuous" policies
        self.cell_try_loss_time = 0.0            # Time when cell phone was lost (grace period)
        self.cell_time_accumulated_buffer = 0.0  # For "Accumulated" policy (T2)

        # Per-type alert debounce timestamps (initialized to avoid AttributeError)
        self.last_cell_alert = 0.0
        self.last_aforo_alert = 0.0
        self.last_weapon_alert = 0.0
        self.last_fatigue_alert = 0.0
        self.last_inactivity_alert = 0.0

        # Fatigue
        self.sleep_time = 0.0

        # Inactivity
        self.last_inactivity_centroid = None
        self.last_movement_time = time.time()

        # Aforo
        self.aforo_violation_start = None

        # Warning System ("Good Conduct")
        self.current_warnings = 0
        self.last_warning_time = 0.0
        self.last_decay_check = time.time()

        # ROI State
        self.roi_active = False

    def set_roi_active(self, active: bool):
        self.roi_active = active
        if active:
            # Reset time base to avoid a huge time_diff jump from previous run
            self.last_process_time = time.time()
        else:
            self.reset_counters()

    def reset_counters(self):
        """Resets all accumulation timers and clears UI status."""
        self.abandonment_time_accumulated = 0.0
        self.cell_time_continuous = 0.0
        self.cell_time_accumulated_buffer = 0.0
        self.cell_try_loss_time = 0.0
        self.current_warnings = 0
        self.last_abandonment_notification = 0.0
        self.aforo_violation_start = None
        self.is_paused_for_warning = False
        self.sleep_time = 0.0
        self.last_inactivity_centroid = None
        self.last_movement_time = time.time()

        # Emit cleared status to UI
        self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
        self.cell_status_signal.emit(0.0, 0.0)
        self.aforo_status_signal.emit(0, self.settings.max_people)

    def handle_alarm(self, level, type_str, message):
        """
        Central Incident Manager.
        Decides whether to notify the supervisor or just warn locally (Blocking).
        """
        current_time = time.time()

        # 0. CRITICAL OVERRIDE (Weapons) — bypass all warning logic
        if type_str == "ARMA":
            self.notifier.send_alert("CRITICAL", type_str, message)
            self.alarm_signal.emit("CRITICAL", type_str, message)
            return

        # 1. Direct Alert mode: always notify supervisor immediately
        if getattr(self.settings, 'notification_direct_alert', False):
            self.notifier.send_alert(level, type_str, message)
            self.alarm_signal.emit(level, type_str, message)
            return

        # 2. Warning Mode OFF: emit standard alarm (non-blocking)
        if not getattr(self.settings, 'notification_warning_mode', True):
            self.alarm_signal.emit(level, type_str, message)
            return

        # 3. Warning Logic (Blocking system with "lives")
        self.current_warnings += 1
        self.last_warning_time = current_time

        warning_limit = getattr(self.settings, 'notification_warning_limit', 3)

        if self.current_warnings < warning_limit:
            # CASE A: Has lives → BLOCKING WARNING (Modal)
            self.is_paused_for_warning = True
            full_msg = f"{message}\n\nAdvertencia {self.current_warnings} de {warning_limit}."
            self.warning_signal.emit(type_str, full_msg)
            self.alarm_signal.emit("WARNING", type_str, full_msg)
        else:
            # CASE B: No lives → CRITICAL ESCALATION (Notification to supervisor)
            full_msg = f"{message} (Escalado por {self.current_warnings} advertencias)"
            self.notifier.send_alert("CRITICAL", type_str, full_msg)
            self.alarm_signal.emit("CRITICAL", "ESCALADO", full_msg)

    @pyqtSlot(str)
    def resume_from_warning(self, warning_type):
        """Called by UI when user accepts a blocking warning. Resets the specific counter."""
        self.logger.info(f"Resuming from warning: {warning_type}")
        self.is_paused_for_warning = False

        if warning_type == "CELULAR":
            self.cell_time_continuous = 0.0
            self.cell_time_accumulated_buffer = 0.0
            self.cell_try_loss_time = 0.0
            self.cell_status_signal.emit(0.0, 0.0)
            self.last_cell_alert = time.time()

        elif warning_type == "ABANDONO":
            self.abandonment_time_accumulated = 0.0
            self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
            self.last_abandonment_notification = time.time()

        elif warning_type == "AFORO":
            self.aforo_violation_start = None
            self.last_aforo_alert = time.time()

    def check_good_conduct(self):
        """Reduces warning count if enough time has passed without incidents."""
        if self.current_warnings == 0:
            return

        current_time = time.time()
        if (current_time - self.last_decay_check) < 10.0:
            return

        self.last_decay_check = current_time
        reduction_seconds = getattr(self.settings, 'notification_reduction_time', 60) * 60

        if (current_time - self.last_warning_time) > reduction_seconds:
            self.current_warnings -= 1
            self.last_warning_time = current_time

    @pyqtSlot(object)
    def process_detections(self, detections):
        if not self.is_running:
            return

        # Pause logic when a blocking modal is shown to the operator
        if self.is_paused_for_warning:
            return

        # No ROI active → reset counters to prevent ghost accumulation
        if not self.roi_active:
            self.reset_counters()
            return

        current_time = time.time()
        time_diff = current_time - self.last_process_time
        self.last_process_time = current_time

        self.check_good_conduct()

        # --- 1. Aforo Check ---
        total_people = sum(1 for d in detections if d['class'] == 'person')
        self.aforo_status_signal.emit(total_people, self.settings.max_people)

        if self.settings.enable_aforo and total_people > self.settings.max_people:
            if self.aforo_violation_start is None:
                self.aforo_violation_start = current_time
            elif (current_time - self.aforo_violation_start) > self.settings.t_aforo:
                if (current_time - self.last_aforo_alert) > 5.0:
                    self.handle_alarm("ALARM", "AFORO", f"Exceso de personas: {total_people} > {self.settings.max_people}")
                    self.last_aforo_alert = current_time
        else:
            self.aforo_violation_start = None

        # --- 2. Cell Phone Detection ---
        cell_detected = False
        for d in detections:
            if d['class'] == 'cell phone' and d.get('in_roi', False) and d['conf'] > 0.3:
                cell_detected = True
                break

        policy = getattr(self.settings, 'cell_policy', 'continuous')

        # Update the continuous cell timer (shared by 'strict' and 'continuous' policies)
        if policy in ('strict', 'continuous'):
            if cell_detected:
                self.cell_try_loss_time = 0.0
                self.cell_time_continuous += time_diff
            else:
                if self.cell_time_continuous > 0.0:
                    if self.cell_try_loss_time == 0.0:
                        self.cell_try_loss_time = current_time
                    time_lost = current_time - self.cell_try_loss_time
                    if time_lost >= 2.0:  # Grace period expired → reset
                        self.cell_time_continuous = 0.0
                        self.cell_try_loss_time = 0.0
                else:
                    self.cell_try_loss_time = 0.0

        # Policy-specific alarm logic
        if policy == 'strict':
            # Zero tolerance: any detection > 0.1 s triggers alarm
            self.cell_status_signal.emit(self.cell_time_continuous, 0.1)
            if self.cell_time_continuous > 0.1:
                if (current_time - self.last_cell_alert) > 5.0:
                    self.handle_alarm("ALARM", "CELULAR", f"Uso de celular detectado ({self.cell_time_continuous:.1f}s)")
                    self.last_cell_alert = current_time

        elif policy == 'continuous':
            limit = getattr(self.settings, 't1_continuous', 3.0)
            self.cell_status_signal.emit(self.cell_time_continuous, limit)
            if self.cell_time_continuous > limit:
                if (current_time - self.last_cell_alert) > 2.0:
                    self.handle_alarm("ALARM", "CELULAR", f"Uso continuo durante {limit}s")
                    self.last_cell_alert = current_time

        elif policy == 'accumulated':
            limit = getattr(self.settings, 't2_cumulative', 10.0)
            if cell_detected:
                self.cell_time_accumulated_buffer += time_diff
            else:
                leak_rate = getattr(self.settings, 't3_leak_rate', 1.0)
                self.cell_time_accumulated_buffer = max(
                    0.0, self.cell_time_accumulated_buffer - (leak_rate * time_diff)
                )
            self.cell_status_signal.emit(self.cell_time_accumulated_buffer, limit)
            if self.cell_time_accumulated_buffer > limit:
                if (current_time - self.last_cell_alert) > 5.0:
                    self.handle_alarm("ALARM", "CELULAR", f"Uso acumulado > {limit}s")
                    self.last_cell_alert = current_time
                    self.cell_time_accumulated_buffer = limit - 2.0  # Avoid immediate re-trigger

        # --- 3. Weapon Detection (Immediate, no policy) ---
        weapons = [d for d in detections if d['class'] in ['knife', 'scissors']]
        if weapons:
            if (current_time - self.last_weapon_alert) > 3.0:
                self.handle_alarm("CRITICAL", "ARMA", "OBJETO PELIGROSO DETECTADO")
                self.last_weapon_alert = current_time
            self.cell_status_signal.emit(0.0, 0.0)

        # --- 4. Fatigue Detection (Chin-to-Chest heuristic) ---
        if getattr(self.settings, 'enable_fatigue', False):
            persons_with_pose = [
                d for d in detections
                if d['class'] == 'person' and d.get('fatigue') and d['fatigue'].get('has_pose')
            ]

            sleep_detected = any(
                p['fatigue'].get('chin_dist', 999.0) < self.settings.chin_dist_threshold
                for p in persons_with_pose
            )

            dt = 0.1  # Approximate frame delta for fatigue timer
            if sleep_detected:
                self.sleep_time += dt
            else:
                self.sleep_time = max(0.0, self.sleep_time - dt * 2)

            if self.sleep_time > 5.0:
                if (current_time - self.last_fatigue_alert) > 5.0:
                    msg = "SUEÑO DETECTADO (Cabeceo)"
                    fatigue_policy = getattr(self.settings, 'fatigue_policy', 'warning')
                    if fatigue_policy == 'critical':
                        self.handle_alarm("CRITICAL", "SUEÑO", msg)
                    else:
                        self.handle_alarm("WARNING", "SUEÑO", msg)
                    self.last_fatigue_alert = current_time
                    self.sleep_time = 0.0

        # --- 5. Inactivity Detection ---
        if getattr(self.settings, 'enable_inactivity', False):
            person = next(
                (d for d in detections
                 if d['class'] == 'person' and d.get('in_roi', False) and d.get('fatigue')),
                None
            )

            if person:
                centroid = person['fatigue'].get('centroid')  # (cx, cy) normalized
                if centroid:
                    if self.last_inactivity_centroid:
                        dx = centroid[0] - self.last_inactivity_centroid[0]
                        dy = centroid[1] - self.last_inactivity_centroid[1]
                        # Convert normalized distance to approximate pixels (1080p reference)
                        dist_px = math.sqrt(dx*dx + dy*dy) * 1080.0

                        if dist_px > self.settings.inactivity_dist_threshold:
                            self.last_movement_time = current_time
                            self.last_inactivity_centroid = centroid
                        else:
                            time_static = current_time - self.last_movement_time
                            if time_static > self.settings.inactivity_time_limit:
                                if (current_time - self.last_inactivity_alert) > 5.0:
                                    self.handle_alarm(
                                        "WARNING", "INACTIVIDAD",
                                        f"Operador inmóvil por {int(time_static)}s"
                                    )
                                    self.last_inactivity_alert = current_time
                    else:
                        self.last_inactivity_centroid = centroid
                        self.last_movement_time = current_time
            else:
                # No person in ROI → reset inactivity timer
                self.last_movement_time = current_time
                self.last_inactivity_centroid = None

        # --- 6. Abandonment Check ---
        if not self.settings.enable_abandonment:
            self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
        else:
            person_in_roi = any(
                d['class'] == 'person' and d.get('in_roi', False) for d in detections
            )

            if person_in_roi:
                self.abandonment_time_accumulated = 0.0
            else:
                self.abandonment_time_accumulated += time_diff

            self.bucket_status_signal.emit(self.abandonment_time_accumulated, self.settings.t_abandonment)

            if self.abandonment_time_accumulated >= self.settings.t_abandonment:
                if (current_time - self.last_abandonment_notification) > 5.0:
                    self.handle_alarm(
                        "CRITICAL", "ABANDONO",
                        f"Abandono detectado ({self.abandonment_time_accumulated:.1f}s)"
                    )
                    self.last_abandonment_notification = current_time
            else:
                self.last_abandonment_notification = 0.0

    def work(self):
        while self.is_running:
            time.sleep(1)
