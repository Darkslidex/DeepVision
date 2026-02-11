# Contexto Maestro: Deep Vision (SIAO)
**Estado:** Arquitectura de Grado Industrial - Listo para Producción
**Entorno:** Windows 10/11 | GPU: NVIDIA GTX 1660 / RTX 2060 (Mínimo)

## I. ARQUITECTURA Y ESTÁNDARES
- **Paradigma:** POO bajo principios SOLID.
- **Modularidad:** Separación estricta: Core (IA), Data (SQLCipher), UI (PyQt6), Services (APIs).
- **Concurrencia:** Inferencia y procesamiento en QThreads independientes. UI estable a 60 FPS.
- **Seguridad:** - DB: SQLite + SQLCipher (AES-256).
    - Auth: Hashing Argon2.
    - Protección: Código preparado para PyArmor.

## II. MOTORES DE INTELIGENCIA ARTIFICIAL (IA)
### A. Presencia, Aforo y ROI (Actualizado)
- **Modelo:** YOLOv11 (class: person).
- **Detección de Operador:** Restringida al ROI (polígono de la silla). Si no hay nadie en el ROI = **Abandono**.
- **Detección de Aforo (>1 Persona):** Análisis del **Frame Completo**.
    - Si `total_person_count` > 1 durante $T_{aforo}$ -> **ALARM**.
    - Independiente del ROI.

### B. Gestión de Celular (Mobile Control)
1. **Strict:** Alerta instantánea (class: cell_phone).
2. **Continuous:** Alerta si visible > $T_{continuo}$.
3. **Cumulative (Leaky Bucket):** Acumulador de tiempo. Sube 1s por uso, baja $k$ segundos por atención. Alerta si $\sum > T_{acumulado}$.

### C. Fatiga y Distracción (Híbrido)
- **MAR (Mouth Aspect Ratio):** Detección de bostezos mediante MediaPipe.
- **Head Pose (6D):** Análisis de Pitch (cabeceo/sueño) y Yaw (mirada fuera de monitores).
- **EAR (Eye Aspect Ratio):** Refuerzo para cierre ocular prolongado.

## III. RESILIENCIA 24/7 E INTEGRACIÓN
- **Dual-Stream:** IA sobre Sub-stream (baja res), UI sobre Main-stream.
- **Watchdog:** Reinicio automático de socket RTSP y monitoreo de proceso externo para evitar cuelgues de Python.
- **Auto-Maintenance:** gc.collect() periódico, purga de discos (>90% uso) y fotos (>30 días).
- **Heartbeat:** Reporte diario de salud vía API (WhatsApp/Telegram).

## IV. EVENTOS Y DB
- **Nivel WARNING:** Alerta local (Audio/Overlay).
- **Nivel ALARM:** Registro en DB cifrada + Captura de evidencia + Notificación externa.
- **Tablas Requeridas:** `users` (auth), `settings` (config/ROI), `logs` (eventos/evidencia).