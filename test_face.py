import cv2
import mediapipe as mp
import time

print("--- INICIANDO DIAGNÓSTICO DE CÁMARA Y MEDIAPIPE ---")

# 1. Probar importación
try:
    print("[1/4] Importando MediaPipe...")
    mp_face_mesh = mp.solutions.face_mesh
    # BAJAR UMBRALES A 0.2 PARA MAYOR SENSIBILIDAD
    face_mesh = mp_face_mesh.FaceMesh(
        refine_landmarks=True, 
        min_detection_confidence=0.2, 
        min_tracking_confidence=0.2
    )
    print("      -> MediaPipe importado CORRECTAMENTE.")
except Exception as e:
    print(f"      -> ERROR CRÍTICO importando MediaPipe: {e}")
    exit()

# 2. Conectar a Cámara RTSP
RTSP_URL = "rtsp://admin:Aa15728488@192.168.0.54:554/Streaming/Channels/101"
print(f"[2/4] Conectando a cámara IP: {RTSP_URL} ...")
print("      -> Esto puede tardar unos segundos...")

# Para RTSP usamos el backend predeterminado o FFMPEG, NO DSHOW.
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("      -> ERROR FATAL: No se pudo conectar al stream RTSP.")
    print("      -> Verifica: 1. Que la IP sea correcta y alcanzable (ping).")
    print("      -> Verifica: 2. Usuario/Contraseña.")
    print("      -> Verifica: 3. Que VLC pueda abrir este link.")
    exit()
else:
    print("      -> ¡Conexión RTSP existosa!")

# 3. Leer un frame
print("[3/4] Intentando leer primer frame...")
ret, frame = cap.read()
if not ret:
    print("      -> ERROR: La cámara se abrió, pero no devolvió imagen (frame vacío).")
    print("      -> Posible fallo de hardware o driver.")
    cap.release()
    exit()
else:
    print(f"      -> Frame capturado correctamente. Resolución: {frame.shape[1]}x{frame.shape[0]}")

# 4. Bucle principal
print("[4/4] Iniciando bucle de visualización. Presiona 'ESC' para salir.")
print("      -> Se abrirá una ventana llamada 'PRUEBA DE VIDA'")

frame_count = 0
while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Error: Frame vacío.")
        break

    # Procesar imagen
    image.flags.writeable = False
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)

    # Dibujar resultados
    image.flags.writeable = True
    image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR) # Convertir de nuevo a BGR para mostrar correctamente
    
    if results.multi_face_landmarks:
        # Dibujar malla facial básica
        for face_landmarks in results.multi_face_landmarks:
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * image.shape[1])
                y = int(landmark.y * image.shape[0])
                cv2.circle(image, (x, y), 1, (0, 255, 0), -1)
        
        # Feedback visual en texto
        cv2.putText(image, f"ROSTRO DETECTADO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(image, "Buscando rostro...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow('PRUEBA DE VIDA - MediaPipe (ESC para salir)', image)
    
    # Manejo de teclas
    key = cv2.waitKey(5) & 0xFF
    if key == 27: # ESC
        print("Cierre solicitado por usuario.")
        break

cap.release()
cv2.destroyAllWindows()
print("--- FIN DEL DIAGNÓSTICO ---")