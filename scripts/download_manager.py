import subprocess
import time

def run_script(script_name):
    subprocess.run(["python3", script_name])

if __name__ == "__main__":
    scripts_para_rodar = [
        "scripts/downloaders/freiburg_forest.py",
        "scripts/downloaders/kaggle.py"
    ]

    start = time.perf_counter()

    for script in scripts_para_rodar:
        run_script(script)

    end = time.perf_counter()
    print(f"Tempo de execução: {end - start:.4f} segundos")