import subprocess
import time

# 1. Start the FastAPI backend
print("Starting FastAPI Backend...")
backend_process = subprocess.Popen(["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"])

# 2. Start the Streamlit Web App
print("Starting Streamlit Web App...")
web_process = subprocess.Popen(["streamlit", "run", "app.py"])

# Give the servers a few seconds to start before launching the mobile app
time.sleep(3)

# 3. Start the Flutter Android app
print("Starting Flutter Android App...")
# This changes into the my_app directory to run the flutter command
flutter_process = subprocess.Popen(["flutter", "run"], cwd="my_app")

try:
    # Keep the script running so all processes stay alive
    backend_process.wait()
    web_process.wait()
    flutter_process.wait()
except KeyboardInterrupt:
    print("\nShutting down all processes...")
    backend_process.terminate()
    web_process.terminate()
    flutter_process.terminate()