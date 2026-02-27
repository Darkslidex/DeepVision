# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [0.9.0] - 2026-02-27

### ✨ Agregado (Added)
- **Notificaciones Telegram**: Integración completa con la Telegram Bot API (`services/telegram.py`).
  - Nuevo servicio `TelegramService` con `send_message()`, `send_photo()` y `send_test_message()`.
  - Instrucciones de configuración incluidas en el docstring del módulo (BotFather → token → Chat ID).
- **Captura de Evidencia**: Cada alarma genera automáticamente una captura JPEG del frame activo.
  - Las imágenes se guardan en `data/evidence/<timestamp>_<TIPO>.jpg`.
  - La foto se adjunta al mensaje de Telegram cuando está disponible (fallback a texto si no).
- **Persistencia de Alertas en DB**: `handle_alarm()` ahora registra cada evento en la tabla `events` de SQLite con `level`, `event_type`, `message` y `evidence_path`.
- **Configuración Telegram en la UI**: Nuevo grupo "Notificaciones Telegram" en `ConfigDialog` con campos para Bot Token (oculto) y Chat ID, más un botón **▶ Probar Conexión** que valida las credenciales sin necesidad de reiniciar.
- **Credenciales por variable de entorno**: Se pueden preconfiguar con `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`; los valores guardados en la DB tienen prioridad.

### 🔧 Modificado (Changed)
- **`NotificationService.send_alert()`**: Firma extendida con parámetro `evidence_path=None`. Ahora delega en `TelegramService` en lugar de imprimir a consola.
- **`LogicWorker.handle_alarm()`**: Captura screenshot → loguea en DB → envía a Telegram antes de emitir señales de UI. El parámetro `evidence_path` se propaga a todas las rutas de notificación.
- **`SystemController.process_frame()`**: Asigna `self.logic_worker.last_frame = frame` en cada frame recibido para alimentar la captura de evidencia (seguro bajo el GIL de CPython).

---

## [0.8.1] - 2026-02-27

### 🔒 Seguridad (Security)
- **Contraseña de administrador hasheada**: La contraseña ya no se compara en texto plano. Ahora se almacena como digest SHA-256 en la base de datos y se configura mediante la variable de entorno `ADMIN_PASSWORD` (fallback: `admin123`). El texto plano nunca reside en el código fuente.
- **Eliminado decorador `@dataclass` de `Settings`**: Era incompatible con el patrón Singleton y podía generar un `__init__` con comportamiento inesperado.

### 🐛 Corregido (Fixed)
- **Política "Strict" de celular nunca disparaba**: El timer `cell_time_continuous` se incrementaba solo dentro del bloque `elif continuous`, por lo que la política estricta siempre leía 0. El timer ahora se actualiza antes del bloque `if/elif` de política, compartido entre `strict` y `continuous`.
- **`log_signal` conectado dos veces**: Se eliminó la conexión duplicada en `main.py` que causaba que cada mensaje de log apareciera dos veces en la tabla de eventos.
- **`set_roi` con condición imposible**: `len(roi_points) < 0` nunca podía ser verdadero. Corregido a `len(roi_points) < 3` (mínimo de puntos para un polígono válido). Con 1 ó 2 puntos ahora se limpia el ROI en lugar de crear un polígono inválido.
- **`show_blocking_warning` lógica contradictoria**: El bloque `if hasattr(self, 'controller')` nunca se ejecutaba (`MainWindow` no tiene esa referencia directa), y en el `else` el estilo del botón ROI se modificaba incorrectamente. Simplificado al único flujo correcto: `self.warning_accepted_signal.emit(warning_type)`.
- **`setup_ui` definido dos veces**: Se eliminó el stub incompleto (línea ~523) que Python ignoraba en favor de la definición real.
- **`roi_coords` sin valor por defecto**: El atributo no se inicializaba en `load_config()`, causando `AttributeError` en cualquier acceso previo a la primera sincronización con DB. Ahora se inicializa con `[]`.
- **`VideoThread.stop()` podía bloquear la UI indefinidamente**: Si la cámara se colgaba en `cap.read()`, el hilo principal quedaba congelado. `BaseWorker.stop()` ahora usa `wait(5000)` y fuerza `terminate()` si el hilo no responde en 5 segundos.

### 🧹 Calidad de Código (Chores)
- **Eliminados todos los `print` de debug de producción**:
  - `core/worker.py`: `"🚀 [DEBUG] EL WORKER HA ARRANCADO..."`
  - `core/ai/detection_worker.py`: ~90 prints por segundo en el loop de inferencia (`[DEBUG] Processing Frame`, `[DEBUG] Raw Detections`, `[DEBUG] ¡LA IA NO VE NADA!`)
  - `core/logic/logic_worker.py`: `"DEBUG: Resuming from warning..."`
  - `ui/main_window.py`: `"DEBUG: ROI Mapped..."` y `"WARNING: No frame size known..."`
  - Los `print` de UI reemplazados por llamadas al logger (`logging.getLogger("DeepVision.UI")`)
- **Imports movidos al top del módulo**: `import time`, `import math`, `import traceback` ya no se importan dentro de métodos en bucles calientes.
- **`winsound` import condicional**: Deja de causar `ImportError` en Linux/macOS. Se usa la bandera `WINSOUND_AVAILABLE` para proteger todas las llamadas a `Beep()`.
- **Atributos de debounce inicializados en `__init__`**: `last_cell_alert`, `last_aforo_alert`, `last_weapon_alert`, `last_fatigue_alert`, `last_inactivity_alert` y `sleep_time` ahora se declaran explícitamente en `LogicWorker.__init__`, eliminando el uso inconsistente de `getattr(..., 0)`.
- **Import duplicado en `detection_worker.py`**: Se eliminó la importación doble de `PyQt6.QtCore`.

---

## [0.8.0] - 2026-02-09

### ✨ Agregado (Added)
- **Sistema de Detección de Fatiga (Micro-sueño)**:
    - Implementación de arquitectura **Dual Model**: `yolo11m.pt` (Objetos) + `yolov8n-pose.pt` (Postura).
    - Algoritmo "Chin-to-Chest": Detecta cabeceos basándose en la distancia vertical nariz-hombros.
    - Alerta visual "CABECEO!" y recuadro rojo tras 5 segundos de postura de sueño.
- **Monitor de Inactividad**:
    - Detección de operadores estáticos (centroide inmóvil < 20px) por más de 30 segundos.
- **Optimización de Rendimiento**:
    - **Aceleración GPU**: Habilitada inferencia CUDA 12.1 para ambos modelos YOLO.
    - **Redimensionado de UI**: El hilo principal ahora redimensiona los frames a 720p antes de renderizar, evitando _freezes_ con cámaras 4K.
    - **Gestión de Contexto QPainter**: Solucionados los crashes de la interfaz gráfica mediante `with QPainter(self)`.

### 🔧 Modificado (Changed)
- **Interfaz Gráfica (Reversión)**:
    - Se eliminó el "Modo Boca" y todos los toggles de temas a pedido del usuario.
    - Restaurado el **"Industrial Dark Mode"** como estilo único y permanente.
    - Overlay restaurado a colores estándar (Verde/Rojo/Cian).
- **Gestión de Dependencias**:
    - Downgrade de `numpy` a `<2.0` para compatibilidad con librerías de visión.
    - Reinstalación de `torch` con soporte CUDA para resolver errores de DLL (WinError 1114).

## [0.7.0] - 2026-02-08

### ✨ Agregado (Added)
- **Automatización de Entorno**:
    - Script `setup_deepvision.ps1` para instalación automática de dependencias y configuración de GPU (CUDA 12.1).
    - Script `check_environment.py` para diagnóstico de hardware y librerías.
- **UI / Personalización**:
    - **Modo Boca 💙💛**: Nuevo tema visual con los colores de Boca Juniors, alternable desde la barra lateral.
- **Lógica e Inteligencia**:
    - **LogicWorker**: Worker dedicado para lógica de negocio (abandonos, reglas complejas).
    - **Monitor de Rendimiento**: Logs de tiempo de inferencia para detectar cuellos de botella (CPU vs GPU).
    - Conexión dinámica de **ROI**: El área de interés dibujada ahora recorta efectivamente la detección en tiempo real.

### 🐛 Corregido (Fixed)
- **Error Crítico de Lógica**: Se restauraron métodos faltantes en `SystemController` (`stop_video`, `restart_video`) que causaban crash al cambiar cámaras.
- **Cableado de IA**: Se conectó correctamente el `DetectionWorker` al controlador y a la UI (antes no arrancaba).
- **Dependencias**: Solucionado conflicto de instalación con `ultralytics` y `torch` en Windows.

## [Legacy] - 2026-02-07

### ✨ Agregado (Added)
- **Frontend / UI**:
    - Implementación de `MainWindow` con estilo "Industrial Dark Mode".
    - `VideoOverlay` dinámico para dibujar Bounding Boxes y ROI.
    - Visualización de alertas en tiempo real (Overlay + Tabla de Logs).
    - Diálogo de Configuración (`ConfigDialog`) protegido por contraseña.
    - Soporte para alertas sonoras (`winsound`).

- **Backend / Core**:
    - Integración de **YOLOv11** (`DetectionWorker`) para detección de personas y celulares.
    - Integración de **MediaPipe** (`BiometricWorker`) para biometría facial.
    - **SystemController**: Orquestador central que gestiona la comunicación entre UI, IA y Video.
    - **VideoThread**: Manejo robusto de streams RTSP con reconexión automática inteligente.

- **Lógica de Negocio**:
    - Detección de **Abandono de Puesto**: Alerta cuando la ROI está vacía.
    - Detección de **Aforo (Overcrowding)**: Alerta cuando hay más de N personas en el cuadro completo.
    - Detección de **Uso de Celular**:
        - Lógica Continua (T1): Alerta por uso ininterrumpido.
        - Lógica Acumulativa (T2/T3): Algoritmo *Leaky Bucket* para uso intermitente.

- **Datos y Persistencia**:
    - Sistema de Base de Datos SQLite (`DBManager`) para logs históricos.
    - Persistencia de configuración (`Settings`) en base de datos.
    - Reinicio automático del hilo de video al cambiar la configuración de red.

### 🔧 Modificado (Changed)
- Optimización de inferencia: Procesamiento de IA en 1 de cada 3 frames para mejorar el rendimiento.
- Lógica de Video:
    - Se fuerza el transporte **TCP** en conexiones RTSP para mayor estabilidad.
    - Sanitización automática de URLs RTSP (eliminación de comillas y espacios).
    - La reconexión automática ahora solo se activa si hubo una conexión exitosa previa, evitando bucles infinitos al inicio.

### 🐛 Corregido (Fixed)
- **Crash de Inicio**: Se agregó validación para entornos donde `mediapipe.solutions` no está disponible, permitiendo que la app inicie con funcionalidad reducida en lugar de cerrarse.
- **Singleton DBManager**: Solucionado error de recursión/inicialización en la clase `DBManager`.

---
*Este changelog sigue el formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).*
