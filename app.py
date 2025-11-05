import subprocess
import sys

# This file serves as the main entry point for hosting platforms
if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dash1.py", "--server.port", "8501", "--server.address", "0.0.0.0"])
