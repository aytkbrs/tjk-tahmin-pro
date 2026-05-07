import pickle
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

# Modeli yükle
with open("ml_model.pkl", "rb") as f:
    data = pickle.load(f)

model = data["model"]
features = data["features"]

# Veriyi yükle
df = pd.read_csv("ml_veri_v3.csv", sep=";", encoding="utf-8-sig")
X = df[features].fillna(0)
y = df["ilk3_mi"]

# Tahmin yap
y_pred = model.predict(X)
y_proba = model.predict_proba(X)[:, 1]

acc = accuracy_score(y, y_pred)
auc = roc_auc_score(y, y_proba)

print(f"Mevcut Model Doğruluğu (Accuracy): %{acc*100:.2f}")
print(f"Mevcut Model AUC: {auc:.4f}")
print("\nSınıflandırma Raporu:")
print(classification_report(y, y_pred, target_names=["İlk3 Değil", "İlk3"]))