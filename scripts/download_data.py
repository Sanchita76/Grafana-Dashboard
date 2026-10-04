"""Download the Kaggle 'Web Server Access Logs' dataset (Apache combined format) into data/.
Kaggle page: https://www.kaggle.com/datasets/eliasdabbas/web-server-access-logs   (file access.log - VERY large, ~3+ GB)
Needs a Kaggle API token (see README). Manual alternative: download on the website and put access.log in data/.
"""
import os, subprocess, sys
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(DATA, exist_ok=True)
try:
    subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download", "-d", "eliasdabbas/web-server-access-logs",
                    "-f", "access.log", "-p", DATA, "--unzip"], check=True)
    print("Done. Next: python scripts/load_logs.py --file data/access.log --limit 500000")
except Exception as e:
    sys.exit(f"Kaggle download failed ({e}). Download manually from the Kaggle page, or use "
             "python scripts/generate_sample_logs.py for synthetic logs.")
