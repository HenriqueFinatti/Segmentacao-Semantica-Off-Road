import time
import runpy

if __name__ == '__main__':
    start = time.perf_counter()
    
    scripts = [
        "scripts/download_manager.py",
        "scripts/clean_organize.py",
        "scripts/gerador_mask.py",
    ]

    for script in scripts:
        runpy.run_path(script, run_name="__main__")
    
    end = time.perf_counter()

    print(f"Tempo total: {end - start:.4f} segundos")