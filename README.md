# DeepVision — Operator Monitoring with Local Computer Vision

**A Windows desktop app (PyQt6) that watches an operator's workstation in real time through a webcam or RTSP camera, with all AI inference running locally.** Inside a Region of Interest (ROI) drawn by the user, it detects and raises alarms for phone use, leaving the post, overcrowding, dangerous objects (knife or scissors), fatigue (head nodding) and inactivity. When an alarm escalates, it sends the supervisor a Telegram message with a photo as evidence, logs the event in SQLite and shows it on an "Industrial Dark Mode" dashboard.

**Why it exists:** in critical posts such as monitoring rooms, call centers and reception desks, what matters is whether the operator is present, alert and not distracted. DeepVision answers that without sending video to the cloud.

**Status:** prototype, functional end to end on a single workstation. See [Project status](#project-status) for what works and the known debt.

---

## Features

### Fatigue and distraction (pose estimation)
- **Pose model:** `yolov8n-pose` for real-time skeletal analysis.
- **Micro-sleep detection (head nodding):** a geometric chin-to-chest heuristic alerts when the head drops for more than 5 seconds.
- **Inactivity monitor:** alerts when the operator makes no significant movement for 30 seconds.
- **Skeleton overlay:** key points (nose, shoulders) drawn on the video for visual feedback.

### Objects and behavior (YOLO11)
- Detection of **people** and **phones** with `yolo11m.pt` (Ultralytics).
- **Three phone-use policies:**
  - **Strict:** zero tolerance (fires in under 0.1 s).
  - **Continuous (T1):** alerts after uninterrupted use exceeds the configured time.
  - **Accumulated (T2/T3):** leaky-bucket logic for intermittent use.
- **ROI filtering:** analysis restricted to the polygon drawn by the user.

### Business logic
- **Abandonment:** alerts when the workstation ROI stays empty for a configurable time.
- **Overcrowding:** alerts when more people than allowed are detected.
- **Warnings with "lives":** a progressive blocking modal before escalating to the supervisor.
- **Multi-level alerts:** `WARNING`, `ALARM` and `CRITICAL`.
- **Dangerous objects:** immediate critical alert on knives or scissors.

### Telegram notifications
- **Alert with photo:** each escalated alarm sends a capture of the current frame with level, type and timestamp.
- **Text fallback:** if no frame is available, the message is sent without an image.
- **Persistent evidence:** captures are saved to `data/evidence/<timestamp>_<TYPE>.jpg` and their path is recorded in the database.
- **Connection test:** a **Test connection** button validates credentials before going live.

### Industrial UI
- Dark dashboard to reduce eye strain.
- Dynamic video overlay with color-coded bounding boxes.
- Password-protected settings panel.
- RTSP camera management from the sidebar.
- Event history and settings persisted in SQLite.

---

## Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 | Windows 11 |
| **Python** | 3.9 | 3.11 |
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 |
| **GPU** | none (CPU mode) | NVIDIA with CUDA 12.x |
| **RAM** | 8 GB | 16 GB |
| **Camera** | USB webcam | IP camera (RTSP) |

---

## Installation

```bash
git clone https://github.com/Darkslidex/DeepVision.git
cd DeepVision
```

Automatic setup (creates the virtual environment and installs dependencies with GPU support):
```powershell
.\setup_deepvision.ps1
```

Check CUDA, models and libraries:
```bash
python check_environment.py
```

## Usage

```bash
set ADMIN_PASSWORD=your_secure_password
python main.py
```

1. If no camera is detected, click **⚙ Configuración** (settings).
2. Enter the admin password (see [Security](#security)).
3. Set the camera **RTSP URL**, or `0` for a local webcam.
4. Click **Dibujar ROI** (draw ROI) and mark the work area: left click adds a point, double click closes the polygon (minimum 3 points).

The interface is in Spanish.

---

## Telegram setup

One-time setup of about 5 minutes.

1. In Telegram, open **@BotFather**, send `/newbot` and copy the **token**.
2. Send any message to your new bot, open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `"id"` inside `"chat"`: that is your **Chat ID**.
3. Configure DeepVision:

**Option A: environment variables (recommended)**
```bash
set TELEGRAM_BOT_TOKEN=<your-token>
set TELEGRAM_CHAT_ID=<your-chat-id>
python main.py
```

**Option B: from the UI.** Open settings, enter the admin password, paste the token and Chat ID under Telegram notifications, click **▶ Probar Conexión** and save.

> **Known debt:** reloading settings from the database on restart (`Settings.sync_from_db()`) is defined but never called. After a restart only the environment variables apply; values entered in the UI last for the current session only. Use Option A for persistent setup.

---

## Security

- **No default password.** The admin password comes from the `ADMIN_PASSWORD` environment variable. If it is not set, no password hash is created and the settings panel stays locked (fail closed).
- **No plaintext.** The database stores a SHA-256 hash of the password, never the password itself.
- **Local inference.** Video and detections never leave the machine; only escalated alerts go to Telegram.
- **Secrets out of the code.** Telegram credentials are read from environment variables.

---

## Project structure

```
DeepVision/
├── config/
│   └── settings.py              # Singleton settings (defaults + sync from DB)
├── core/
│   ├── ai/
│   │   ├── detection_worker.py  # YOLO11 (people, phones, weapons) + pose-based fatigue
│   │   └── biometric_worker.py  # MediaPipe EAR/MAR: dead code, never instantiated
│   ├── logic/
│   │   ├── logic_worker.py      # Business logic, alarms and evidence capture
│   │   └── leaky_bucket.py      # Unused: the accumulated policy is inline in logic_worker
│   ├── controller.py            # System orchestrator
│   ├── notification_service.py  # Notification dispatcher (Telegram)
│   └── worker.py                # BaseWorker (thread lifecycle, QThreads)
├── data/
│   └── db.py                    # SQLite DBManager (singleton, thread-safe)
├── services/
│   ├── telegram.py              # Telegram Bot API (sendMessage / sendPhoto)
│   └── whatsapp.py              # Not wired (sending is commented out)
├── ui/
│   ├── main_window.py           # Main window, dialogs and dashboard
│   └── overlay.py               # Video and ROI overlay widget
├── yolo11m.pt · yolov8n-pose.pt # YOLO models
├── main.py                      # Entry point
├── check_environment.py         # Environment diagnostics
└── setup_deepvision.ps1         # Automatic setup (Windows)
```

---

## Project status

**Works end to end:** video capture (webcam or RTSP) with basic reconnection, ROI-cropped YOLO detection, alarm logic (overcrowding, phone use in 3 policies, weapons, abandonment, pose-based fatigue, inactivity), the warning system with "lives" and a blocking modal, JPEG evidence capture, SQLite logging and Telegram escalation with photo.

**Known debt:**
- `core/ai/biometric_worker.py` (MediaPipe EAR/MAR) is dead code; real fatigue detection uses YOLO pose.
- `services/whatsapp.py` is not wired to notifications.
- `core/logic/leaky_bucket.py` is imported but unused.
- `Settings.sync_from_db()` is never called, so settings saved in the DB are not reloaded on restart.
- The SQLite database is **not encrypted**; SQLCipher is only mentioned in comments.
- The admin password uses an unsalted SHA-256 hash; `argon2-cffi` is listed in `requirements.txt` but not used yet. Moving to Argon2id is the next security fix.
- `tests/verify_logic.py` is outdated: it references attributes the current `SystemController` no longer has. Its last recorded run (`tests/results.txt`) passed 5 logic scenarios (normal operation, abandonment, overcrowding, phone inside and outside the ROI).
- Version numbers are inconsistent: `config/settings.py` says `1.0.0` while the CHANGELOG is at `v0.9.0`.

## License

Owned by **Félix Lezama**. All rights reserved.
