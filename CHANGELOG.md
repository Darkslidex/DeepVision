# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

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
