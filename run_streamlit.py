import subprocess
import sys

# Streamlit を実行
result = subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'Weather_Analysis_Power_Prediction.py', '--client.showErrorDetails=true'], 
                       capture_output=True, text=True, timeout=20)

print("STDOUT:")
print(result.stdout[:3000])
print("\nSTDERR:")
print(result.stderr[:3000])
print(f"\nReturn code: {result.returncode}")
