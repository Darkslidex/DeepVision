try:
    import mediapipe as mp
    print(f"MediaPipe file: {mp.__file__}")
    
    try:
        from mediapipe.python import solutions
        print("Successfully imported mediapipe.python.solutions")
    except ImportError:
        print("Failed to import mediapipe.python.solutions")

    try:
        import mediapipe.python as mp_python
        print(f"Dir mp_python: {dir(mp_python)}")
        if hasattr(mp_python, 'solutions'):
            print("Found solutions in mp_python")
    except ImportError:
        print("Failed to import mediapipe.python")

    print(f"MediaPipe version: {mp.__version__}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
