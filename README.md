# DeepVision — Sistema Inteligente de Monitoreo de Operadores

**DeepVision es una estación de escritorio (Windows, PyQt6) que vigila en tiempo real a un operador en su puesto de trabajo usando una cámara (webcam o RTSP) e inteligencia artificial local.** Sobre una Región de Interés (ROI) que el usuario dibuja, detecta y alarma por: uso de celular, abandono del puesto, exceso de aforo, objetos peligrosos (cuchillo/tijera), fatiga (cabeceo) e inactividad. Cuando una alarma escala, envía al supervisor un mensaje con foto de evidencia por Telegram, registra el evento en SQLite y lo muestra en un dashboard "Industrial Dark Mode".

Fue creado como producto de seguridad electrónica para puestos críticos —salas de monitoreo, call centers, recepciones— donde importa saber si el operador está presente, atento y sin distracciones, sin depender de la nube: toda la inferencia corre en la máquina local.

> **Estado:** funcional end-to-end. Es un producto en desarrollo activo; ver la sección [Estado del proyecto](#-estado-del-proyecto) para qué está implementado y qué es deuda conocida.

---

## 🚀 Características Principales

### 👁️ Detección Biométrica (Fatiga y Distracción)
- **Modelo de Postura (Pose Estimation)**: Uso de `yolov8n-pose` para análisis esquelético en tiempo real.
- **Detección de Micro-sueños (Cabeceo)**: Algoritmo geométrico que alerta si la barbilla cae hacia el pecho por tiempo prolongado (>5s).
- **Monitor de Inactividad**: Alerta si el operador no realiza movimientos significativos en su puesto durante 30 segundos.
- **Visualización Esquelética**: Renderizado de puntos clave (nariz, hombros) en el overlay para feedback visual.

### 📱 Detección de Objetos y Comportamiento (YOLO11)
- Detección precisa de **personas** y **celulares** utilizando el modelo `yolo11m.pt` (Ultralytics).
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

### 📲 Notificaciones Telegram
- **Alerta con Foto**: Cada alarma escalada envía al supervisor una captura del frame activo junto con nivel, tipo y timestamp.
- **Fallback a texto**: Si el frame no está disponible, se envía el mensaje sin imagen.
- **Bot Token + Chat ID**: Configurables desde la UI sin reiniciar la aplicación.
- **Evidencia persistente**: Las capturas se guardan localmente en `data/evidence/<timestamp>_<TIPO>.jpg` y se registran en la base de datos con su ruta.
- **Prueba de conexión**: Botón **▶ Probar Conexión** en el diálogo de configuración para validar las credenciales antes de entrar en producción.

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

## 📲 Configuración de Telegram

> Setup único de ~5 minutos. Una vez configurado, cada alarma escalada llega como mensaje con foto al chat del supervisor.

### Paso 1 — Crear el bot
1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot`, elige nombre y usuario.
3. Copia el **token** que te entrega (formato `123456789:ABCdef...`).

### Paso 2 — Obtener tu Chat ID
1. Manda cualquier mensaje a tu bot recién creado.
2. Abre en el navegador:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Copia el campo `"id"` dentro de `"chat"` — ese es tu **Chat ID**.

### Paso 3 — Configurar en DeepVision

**Opción A — Variable de entorno (recomendado para producción):**
```bash
set TELEGRAM_BOT_TOKEN=123456789:ABCdef...
set TELEGRAM_CHAT_ID=987654321
python main.py
```

**Opción B — Desde la UI:**
1. Abre **⚙ Configuración** → ingresa contraseña de administrador.
2. En la sección **Notificaciones Telegram**, pega el token y el Chat ID.
3. Haz clic en **▶ Probar Conexión** — deberías recibir un mensaje de prueba en Telegram.
4. Guarda. Las credenciales se guardan en la base de datos y aplican durante la sesión en curso.

> ⚠️ **Deuda conocida:** la recarga de configuración desde la base de datos al reiniciar (`Settings.sync_from_db()`) está definida pero **no se invoca**. En la práctica, tras reiniciar la aplicación solo se aplican las **variables de entorno** (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`); lo configurado por la UI vale únicamente en esa sesión. Para uso persistente entre reinicios, usar la Opción A (variables de entorno).

---

## 🔒 Seguridad

### Contraseña de administrador
La contraseña **nunca se almacena en texto plano**. Al inicializar la base de datos, se guarda el hash SHA-256 de la contraseña configurada mediante la variable de entorno `ADMIN_PASSWORD`.

```bash
set ADMIN_PASSWORD=mi_contrasena_segura
python main.py
```

> ⚠️ **Sin contraseña por defecto**: si `ADMIN_PASSWORD` no está definida, no se crea ningún hash y el panel de configuración queda bloqueado (falla cerrado).

---

## 📂 Estructura del Proyecto

```
DeepVision/
├── config/
│   └── settings.py              # Configuración Singleton (defaults + sync desde DB)
├── core/
│   ├── ai/
│   │   ├── detection_worker.py  # YOLO11 (personas, celulares, armas) + fatiga por pose
│   │   └── biometric_worker.py  # MediaPipe EAR/MAR — CÓDIGO MUERTO (placeholders, no se instancia)
│   ├── logic/
│   │   ├── logic_worker.py      # Lógica de negocio, alarmas y captura de evidencia
│   │   └── leaky_bucket.py      # Algoritmo Leaky Bucket (no usado; la política T2/T3 está inline en logic_worker)
│   ├── controller.py            # Orquestador del sistema
│   ├── notification_service.py  # Dispatcher de notificaciones (Telegram)
│   └── worker.py                # BaseWorker (ciclo de vida de hilos)
├── data/
│   ├── db.py                    # DBManager SQLite (Singleton, thread-safe)
│   └── evidence/                # Capturas JPEG generadas automáticamente por alarma
├── services/
│   ├── telegram.py              # TelegramService — Bot API (sendMessage / sendPhoto)
│   └── whatsapp.py              # No usado (envío comentado, sin cablear)
├── ui/
│   ├── main_window.py           # Ventana principal, diálogos y dashboard
│   └── overlay.py               # Widget de superposición de video y ROI
├── yolo11m.pt · yolov8n-pose.pt # Modelos YOLO en la raíz del proyecto
├── main.py                      # Punto de entrada
├── check_environment.py         # Diagnóstico de entorno
└── setup_deepvision.ps1         # Instalación automática (Windows)
```

> **Nota:** la fatiga (cabeceo) se calcula con la heurística *chin-to-chest* sobre `yolov8n-pose`, **no** con MediaPipe. El módulo `biometric_worker.py` (EAR/MAR con MediaPipe) quedó como código muerto: sus cálculos devuelven valores fijos y no se instancia en el controlador.

---

## 🧭 Estado del proyecto

**Funciona end-to-end:** captura de video (webcam/RTSP) con reconexión básica, detección YOLO recortada por ROI, lógica de alarmas (aforo, celular en 3 políticas, armas, abandono, fatiga por pose, inactividad), sistema de advertencias con "vidas" y modal bloqueante, captura de evidencia JPEG, registro en SQLite y escalado a Telegram con foto.

**Deuda conocida / pendiente:**
- `core/ai/biometric_worker.py` (MediaPipe EAR/MAR): **código muerto**, no se usa. La fatiga real es por pose YOLO.
- `services/whatsapp.py`: el envío está comentado; no está cableado a las notificaciones.
- `core/logic/leaky_bucket.py`: importado pero no usado (la política acumulada está reimplementada inline).
- `Settings.sync_from_db()`: nunca se invoca → la configuración guardada en DB no se recarga al reiniciar (ver nota de Telegram).
- Cifrado de DB (SQLCipher): solo mencionado en comentarios; la base es SQLite **sin cifrar**.
- `requirements.txt` lista `argon2-cffi`, pero el hashing de la contraseña admin usa **SHA-256** (`hashlib`), no Argon2.
- `tests/verify_logic.py` está desactualizado: referencia atributos (`whatsapp_service`, `leaky_bucket`) que el `SystemController` actual ya no tiene.
- Versionado inconsistente: `config/settings.py` declara `1.0.0` mientras README/CHANGELOG van por `v0.9.0`.

## 🛡️ Licencia

Propiedad de **Félix Lezama**. Todos los derechos reservados.
