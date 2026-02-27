# DeepVision - Sistema Inteligente de Monitoreo de Operadores

**DeepVision** es una solución de visión por computadora de alto rendimiento diseñada para monitorear en tiempo real el estado y comportamiento de operadores en entornos críticos. Utiliza modelos de Inteligencia Artificial de vanguardia para detectar fatiga, distracción, uso de celular, abandono de puesto y aglomeraciones.

![DeepVision UI](docs/screenshot.png) <!-- Placeholder for screenshot -->

---

## 🚀 Características Principales

### 👁️ Detección Biométrica (Fatiga y Distracción)
- **Modelo de Postura (Pose Estimation)**: Uso de `yolov8n-pose` para análisis esquelético en tiempo real.
- **Detección de Micro-sueños (Cabeceo)**: Algoritmo geométrico que alerta si la barbilla cae hacia el pecho por tiempo prolongado (>5s).
- **Monitor de Inactividad**: Alerta si el operador no realiza movimientos significativos en su puesto durante 30 segundos.
- **Visualización Esquelética**: Renderizado de puntos clave (nariz, hombros) en el overlay para feedback visual.

### 📱 Detección de Objetos y Comportamiento (YOLOv11)
- Detección precisa de **personas** y **celulares** utilizando modelos YOLO optimizados.
- **Tres políticas de uso de celular**:
  - **Estricta**: Tolerancia cero (dispara en <0.1 s de detección).
  - **Continua (T1)**: Alerta tras uso ininterrumpido superado el tiempo configurado.
  - **Acumulada (T2/T3)**: Algoritmo *Leaky Bucket* para uso intermitente.
- **Restricción por ROI**: Análisis focalizado en la Región de Interés dibujada por el usuario.

### 🧠 Lógica de Negocio Avanzada
- **Detección de Abandono**: Alerta si el puesto de trabajo (ROI) permanece vacío por un tiempo configurable.
- **Control de Aforo (Overcrowding)**: Alerta si se detectan más personas de las permitidas.
- **Sistema de Advertencias con "Vidas"**: Bloqueo modal progresivo antes de escalar al supervisor.
- **Alertas Multinivel**: Clasificación de eventos en `WARNING`, `ALARM` y `CRITICAL`.
- **Detección de Armas**: Alerta inmediata y crítica ante la detección de objetos peligrosos (cuchillos/tijeras).

### 🖥️ Interfaz de Usuario Industrial
- Dashboard en modo oscuro ("Industrial Dark Mode") para reducir la fatiga visual.
- **Video Overlay Dinámico**: Visualización de cajas delimitadoras con código de colores.
- **Panel de Configuración Seguro**: Acceso protegido por contraseña (almacenada como hash SHA-256).
- **Gestión de Cámaras**: Agregar, seleccionar y eliminar fuentes RTSP desde la barra lateral.
- **Logs y Persistencia**: Registro histórico de eventos en SQLite con persistencia de configuración.

---

## 🛠️ Requisitos del Sistema

| Requisito | Mínimo | Recomendado |
|---|---|---|
| **OS** | Windows 10 | Windows 11 |
| **Python** | 3.9 | 3.11 |
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 |
| **GPU** | — (CPU mode) | NVIDIA con CUDA 12.x |
| **RAM** | 8 GB | 16 GB |
| **Cámara** | Webcam USB | Cámara IP (RTSP) |

---

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-org/deepvision.git
cd deepvision
```

### 2. Instalación automática (recomendada)
Ejecute el script de PowerShell para crear el entorno virtual e instalar dependencias con soporte GPU:
```powershell
.\setup_deepvision.ps1
```

### 3. Verificación del entorno
Confirme que CUDA, modelos y librerías están correctamente instalados:
```bash
python check_environment.py
```

---

## ▶️ Uso

```bash
python main.py
```

### Configuración inicial
1. Al iniciar, si no se detecta cámara, haga clic en **⚙ Configuración**.
2. Ingrese la contraseña de administrador (ver sección **Seguridad** más abajo).
3. Configure la **URL RTSP** de su cámara o use `0` para webcam local.
4. Haga clic en **⛛ Dibujar ROI** y marque el área de trabajo con el mouse:
   - **Click izquierdo**: agregar punto.
   - **Doble click**: cerrar y confirmar el polígono (mínimo 3 puntos).

---

## 🔒 Seguridad

### Contraseña de administrador
La contraseña **nunca se almacena en texto plano**. Al inicializar la base de datos, se guarda el hash SHA-256 de la contraseña configurada mediante la variable de entorno `ADMIN_PASSWORD`.

```bash
# Opción A: variable de entorno (recomendado para producción)
set ADMIN_PASSWORD=mi_contrasena_segura
python main.py

# Opción B: sin variable de entorno (solo para desarrollo)
# La contraseña por defecto es "admin123"
python main.py
```

> ⚠️ **Importante**: Cambie la contraseña por defecto antes de desplegar en producción configurando la variable `ADMIN_PASSWORD`.

---

## 📂 Estructura del Proyecto

```
DeepVision/
├── config/
│   └── settings.py         # Configuración Singleton (defaults + sync desde DB)
├── core/
│   ├── ai/
│   │   ├── detection_worker.py  # YOLOv11 (personas, celulares, armas)
│   │   └── biometric_worker.py  # MediaPipe (EAR/MAR — en desarrollo)
│   ├── logic/
│   │   ├── logic_worker.py      # Lógica de negocio y alarmas
│   │   └── leaky_bucket.py      # Algoritmo Leaky Bucket (disponible)
│   ├── controller.py            # Orquestador del sistema
│   ├── notification_service.py  # Servicio de notificaciones (stub)
│   └── worker.py                # BaseWorker (ciclo de vida de hilos)
├── data/
│   └── db.py               # DBManager SQLite (Singleton, thread-safe)
├── services/
│   └── whatsapp.py         # Integración WhatsApp Cloud API (stub)
├── ui/
│   ├── main_window.py      # Ventana principal, diálogos y dashboard
│   └── overlay.py          # Widget de superposición de video y ROI
├── assets/
│   └── models/             # Modelos YOLO (.pt)
├── main.py                 # Punto de entrada
├── check_environment.py    # Diagnóstico de entorno
└── setup_deepvision.ps1    # Instalación automática (Windows)
```

---

## 🛡️ Licencia

Propiedad de **Félix Lezama**. Todos los derechos reservados.
