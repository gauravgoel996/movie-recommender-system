import subprocess
import time
import sys

def kill_port(port):
    """Finds and forcefully kills any process using the specified port on Windows."""
    try:
        # Find the process ID (PID) listening on the port
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        lines = output.strip().split('\n')
        for line in lines:
            if "LISTENING" in line:
                pid = line.strip().split()[-1]
                print(f"🧹 Clearing port {port} (Killing PID: {pid})...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # If the command fails, it means the port is already free.
        pass

# --- 1. CLEANUP OLD PROCESSES ---
print("Checking for zombie processes...")
kill_port(8000)  # FastAPI Port
kill_port(8501)  # Streamlit Port

# --- 2. START SERVICES ---
print("\nStarting FastAPI Backend...")
backend_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"])

print("Starting Streamlit Web App...")
web_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py"])

# Give the servers 3 seconds to spin up completely
time.sleep(3)

print("Starting Flutter Android App...")
flutter_process = subprocess.Popen("flutter run", cwd="my_app", shell=True)

# --- 3. WAIT AND GRACEFUL SHUTDOWN ---
try:
    # Keep the script running so all processes stay alive
    backend_process.wait()
    web_process.wait()
    flutter_process.wait()
except KeyboardInterrupt:
    print("\n\nShutting down all processes...")
    backend_process.terminate()
    web_process.terminate()
    flutter_process.terminate()
    
    # Run the cleanup one last time just to be absolutely sure
    kill_port(8000)
    kill_port(8501)
    print("Cleanup complete. Goodbye!")