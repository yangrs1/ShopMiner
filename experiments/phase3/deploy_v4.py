"""Phase 3 Optuna v4 deploy: backup v3, deploy v4."""
import os, shutil, pickle
ROOT = r"C:\Users\35027\Desktop\数据挖掘\ShopMiner"
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase3")
BACKUP = os.path.join(ROOT, "experiments", "back_up")

src_pkl = os.path.join(PREP, "phase3_clusters_v3.pkl")
with open(src_pkl, "rb") as f:
    cur = pickle.load(f)
print(f"Current pkl version: {cur.get('version', cur.get('method', 'unknown'))}")
print(f"Current Sil: {cur.get('silhouette', 'N/A')}")

# Backup v3 (the original tuned model)
v3_back = os.path.join(BACKUP, "phase3_clusters_v3_v3_pre_optuna.pkl")
if not os.path.exists(v3_back):
    shutil.copy2(src_pkl, v3_back)
    print(f"Backed up v3 to: {v3_back}")
else:
    print(f"v3 backup already exists: {v3_back}")

# Deploy v4
new_src = os.path.join(EXP, "phase3_clusters_winner.pkl")
with open(new_src, "rb") as f:
    new = pickle.load(f)
print(f"\nNew version: {new.get('version', new.get('method', 'unknown'))}")
print(f"New Sil: {new.get('silhouette', 'N/A')}")
print(f"New K: {new.get('K', 'N/A')}")

shutil.copy2(new_src, src_pkl)
print(f"\nDeployed to: {src_pkl}")

# Verify
with open(src_pkl, "rb") as f:
    verify = pickle.load(f)
print(f"Verify Sil: {verify.get('silhouette'):.4f}  K: {verify.get('K')}")
print("Deployment complete.")
