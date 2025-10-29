
import subprocess
import time

# Wait for the application to load
time.sleep(5)

# Take a screenshot using scrot
subprocess.run(["scrot", "jules-scratch/verification/verification.png"])
