import cv2

print("--- ESCANER DE CÁMARAS DISPONIBLES ---")
available_cameras = []

for i in range(10):  # Probar índices del 0 al 9
    print(f"Probando índice {i} con DirectShow...", end=" ")
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) # FORZAR DIRECTSHOW
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print("OK (Cámara encontrada y lee imagen)")
            available_cameras.append(i)
        else:
            print("FALLO (Se abre, pero devuelve imagen vacía/negra)")
        cap.release()
    else:
        print("NO DISPONIBLE")

print("\n--- RESUMEN ---")
if available_cameras:
    print(f"Cámaras funcionales encontradas en los índices: {available_cameras}")
    print("Por favor, modifica tu script para usar uno de estos índices.")
else:
    print("NO SE ENCONTRÓ NINGUNA CÁMARA ACCESIBLE.")
    print("Posibles causas:")
    print("1. Otra aplicación (Zoom, Teams, Meet) está usando la cámara.")
    print("2. Permisos de privacidad de Windows bloquean el acceso a aplicaciones de escritorio.")
    print("3. Driver de cámara no instalado o defectuoso.") 
