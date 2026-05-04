import subprocess
try:
    win_path = subprocess.check_output(['wslpath', '-w', '1.jpg']).decode().strip()
    cmd = ['/mnt/c/Users/stone/AppData/Local/Programs/Ollama/ollama.exe', 'run', 'moondream', f'Describe this image {win_path}']
    print("Running:", cmd)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("Success:", result.stdout)
except Exception as e:
    print("Exception:", e)
