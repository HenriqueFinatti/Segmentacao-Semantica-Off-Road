import runpy
import time

if __name__ == "__main__":
    scripts = [
        "scripts/downloaders/freiburg_forest.py",
        "scripts/downloaders/kaggle.py"
    ]

    start = time.perf_counter()
    for script in scripts:
        runpy.run_path(script, run_name="__main__")
    
    end = time.perf_counter()
    print(f"Tempo total: {end - start:.4f}s")