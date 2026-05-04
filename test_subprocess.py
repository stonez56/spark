import subprocess
try:
    result = subprocess.run(
        ["ollama", "run", "moondream", "Describe ./1.jpg"],
        capture_output=True, text=True, check=True
    )
    print("Success:", result.stdout)
except subprocess.CalledProcessError as e:
    print("Error output:", e.stderr)
except Exception as e:
    print("Exception:", e)
