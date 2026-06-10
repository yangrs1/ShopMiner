"""Phase 4 Optuna v7 deploy: backup v6 pkl, deploy v7."""
import os, shutil, pickle
ROOT = r"C:\Users\35027\Desktop\数据挖掘\ShopMiner"
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase4")
BACKUP = os.path.join(ROOT, "experiments", "back_up")

# 1. Backup current v6 pkl (if not already backed up)
src_pkl = os.path.join(PREP, "phase4_churn_v5.pkl")
back_pkl = os.path.join(BACKUP, "phase4_churn_v5.pkl")
# Check if backup is older (current v6 vs original v5)
with open(src_pkl, "rb") as f:
    cur = pickle.load(f)
print(f"Current pkl version: {cur.get('version', 'unknown')}")
print(f"Current OOT: {cur.get('oot_mean_auc', 'N/A')}")

# Make a v6 backup (before overwriting with v7)
v6_back = os.path.join(BACKUP, "phase4_churn_v5_v6_pre_optuna.pkl")
if not os.path.exists(v6_back):
    shutil.copy2(src_pkl, v6_back)
    print(f"Backed up v6 to: {v6_back}")
else:
    print(f"v6 backup already exists: {v6_back}")

# 2. Load new v7 pkl from experiments/phase4
new_src = os.path.join(EXP, "phase4_churn_winner.pkl")
with open(new_src, "rb") as f:
    new = pickle.load(f)
print(f"\nNew pkl version: {new.get('version', 'unknown')}")
print(f"New OOT: {new.get('oot_mean_auc', 'N/A')}")
print(f"Optuna best params: {new.get('optuna_best_params', {})}")

# 3. Replace
shutil.copy2(new_src, src_pkl)
print(f"\nDeployed v7 to: {src_pkl}")

# 4. Verify
with open(src_pkl, "rb") as f:
    verify = pickle.load(f)
print(f"Verify version: {verify['version']}, OOT: {verify['oot_mean_auc']:.4f}")
print(f"Model type: {type(verify['churn_model']).__name__}")
print("\n✓ Deployment complete")
