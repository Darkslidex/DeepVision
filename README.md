# DeepVision - Sistema Inteligente de Monitoreo de Operadores

**DeepVision** es una solución de visión por computadora de alto rendimiento diseñada para monitorear en tiempo real el estado y comportamiento de operadores en entornos críticos. Utiliza modelos de Inteligencia Artificial de vanguardia para detectar fatiga, distracción, uso de celular, abandono de puesto y aglomeraciones.

![DeepVision UI](docs/screenshot.png) <!-- Placeholder for screenshot -->

## 🚀 Características Principales

### 👁️ Detección Biométrica (Fatiga y Distracción)
- **Modelo de Postura (Pose Estimation)**: Uso de `yolov8n-pose` para análisis esquelético en tiempo real.
- **Detección de Micro-sueños (Cabeceo)**: Algoritmo geométrico que alerta si la barbilla cae hacia el pecho por tiempo prolongado (>5s).
- **Monitor de Inactividad**: Alerta si el operador no realiza movimientos significativos en su puesto durante 30 segundos.
- **Visualización Esquelética**: Renderizado de puntos clave (nariz, hombros) en el overlay para feedback visual.

### 📱 Detección de Objetos y Comportamiento (YOLOv11)
- Detección precisa de **personas** y **celulares** utilizando modelos YOLO optimizados.
- **Política de Uso de Celular**: Implementación del algoritmo *Leaky Bucket* para detectar uso acumulativo y continuo, filtrando falsos positivos breves.
- **Restricción por ROI**: Análisis focalizado en la Región de Interés (ROI) definida por el usuario.

### 🧠 Lógica de Negocio Avanzada
- **Detección de Abandono**: Alerta si el puesto de trabajo (ROI) permanece vacío por un tiempo configurable.
- **Control de Aforo (Overcrowding)**: Alerta si se detectan más personas de las permitidas en la escena completa.
- **Alertas Multinivel**: Clasificación de eventos en `INFO`, `WARNING`, `ALARM` y `CRITICAL`.

### 🖥️ Interfaz de Usuario Industrial
- Dashboard en modo oscuro ("Industrial Dark Mode") para reducir la fatiga visual.
- **Video Overlay Dinámico**: Visualización de cajas delimitadoras con código de colores (Cian: Operador, Rojo: Celular, Amarillo: Aforo).
- **Panel de Configuración Seguro**: Acceso protegido por contraseña para ajustar umbrales (T1, T2, Aforo) y configurar cámaras RTSP.
- **Logs y Persistencia**: Registro histórico de eventos en base de datos SQLite y persistencia de configuración.
- **Estilo Profesional**: Diseño sobrio y funcional, enfocado en la claridad operativa.

---

## 🛠️ Requisitos del Sistema

- **OS**: Windows 10/11 (Recomendado).
- **Python**: 3.9+.
- **Hardware**:
    - CPU: Procesador moderno (Intel i5/Ryzen 5 o superior).
    - GPU: NVIDIA recomendada para inferencia YOLO (CUDA), aunque funciona en CPU.
    - Cámara: Webcam USB o Cámara IP (RTSP).

## 📦 Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-org/deepvision.git
    cd deepvision
    ```

## 📦 Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-org/deepvision.git
    cd deepvision
    ```

2.  **Instalación Automática (Recomendada)**:
    Ejecute el script de PowerShell para crear el entorno y configurar GPU automáticamente:
    ```powershell
    Example: .\setup_deepvision.ps1
    ```

3.  **Verificación**:
    Puede verificar que todo esté correcto (CUDA, Modelos) ejecutando:
    ```powershell
    python check_environment.py
    ```

## ▶️ Uso

Ejecute el archivo principal para iniciar la aplicación:

```bash
python main.py
```

### Configuración Inicial
1.  Al iniciar, si no se detecta cámara, vaya a **⚙ Configuración**.
2.  Ingrese la contraseña de administrador (`admin123` por defecto).
3.  Configure la **URL RTSP** de su cámara o use `0` para webcam local.
4.  Haga clic en **⛛ Dibujar ROI** en el dashboard y marque el área de trabajo del operador con el mouse (Click izquierdo para puntos, Doble click para cerrar).

---

## 📂 Estructura del Proyecto

```
DeepVision/
├── config/             # Configuración y Settings (Singleton)
├── core/               # Lógica Principal
│   ├── ai/             # Workers de IA (DetectionWorker, BiometricWorker)
│   ├── logic/          # Algoritmos de negocio (LeakyBucket)
│   ├── controller.py   # Orquestador del sistema
│   └── video_worker.py # Manejo de video y reconexión
├── data/               # Base de datos SQLite y logs
├── ui/                 # Interfaz Gráfica (PyQt6)
│   ├── main_window.py  # Ventana principal y diálogos
│   └── overlay.py      # Widget de superposición de video
└── main.py             # Punto de entrada
```

## 🛡️ Licencia

Propiedad de **[Félix Lezama]**. Todos los derechos reservados.
