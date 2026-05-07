import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import xgboost as xgb

print("=" * 70)
print("ML MODEL EGITIMI v4 – YUKSEK PERFORMANS")
print("=" * 70)

# Veriyi yükle
df = pd.read_csv("ml_veri_v3.csv", sep=";", encoding="utf-8-sig")
hedef = "ilk3_mi"
bilgi_kolonlar = [c for c in df.columns if c.startswith("_")]
ozellikler = [c for c in df.columns if c not in bilgi_kolonlar + [hedef, "birinci_mi"]]

X = df[ozellikler].fillna(0)
y = df[hedef]

print(f"Veri: {len(X)} satır, {len(ozellikler)} özellik")
print(f"İlk3 oranı: %{y.mean()*100:.1f}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale pos weight
scale_pos = (y_train == 0).sum() / (y_train == 1).sum()

model = xgb.XGBClassifier(
    n_estimators=800,
    max_depth=10,
    learning_rate=0.03,
    subsample=0.9,
    colsample_bytree=0.9,
    min_child_weight=5,
    gamma=0.2,
    scale_pos_weight=scale_pos,
    objective='binary:logistic',
    eval_metric='logloss',
    early_stopping_rounds=30,
    random_state=42,
    n_jobs=-1,
    tree_method='hist'
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print(f"\nTest Doğruluğu (Accuracy): %{acc*100:.2f}")
print(f"Test AUC: {auc:.4f}")
print("\nRapor:")
print(classification_report(y_test, y_pred, target_names=["İlk3 Değil", "İlk3"]))

# Kaydet
with open("ml_model.pkl", "wb") as f:
    pickle.dump({
        "model": model,
        "features": ozellikler,
        "test_acc": acc,
        "test_auc": auc
    }, f)

print("\nYeni model 'ml_model.pkl' olarak kaydedildi.")