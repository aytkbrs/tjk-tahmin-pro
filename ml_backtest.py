import pandas as pd
import numpy as np
import pickle
from collections import defaultdict
from sklearn.metrics import accuracy_score, roc_auc_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("ML BACKTEST (Zaman Serisi) - Gerçek Başarı")
print("=" * 70)

# Veriyi yükle
df = pd.read_csv("ml_veri_v3.csv", sep=";", encoding="utf-8-sig")
# Tarih sütununu al (satırlarda _tarih var)
df["_tarih"] = pd.to_datetime(df["_tarih"], format="%d.%m.%Y")
tarihler = sorted(df["_tarih"].unique())

hedef = "ilk3_mi"
bilgi_kolonlar = [c for c in df.columns if c.startswith("_")]
ozellikler = [c for c in df.columns if c not in bilgi_kolonlar + [hedef, "birinci_mi"]]

print(f"Toplam {len(tarihler)} farklı gün var.")
print(f"Özellik sayısı: {len(ozellikler)}")

# Minimum 30 günlük eğitim verisi istiyoruz
if len(tarihler) < 30:
    print("Yeterli gün yok.")
    exit()

tahminler, gercekler = [], []

# İlk 30 günden sonrası için backtest
for i, test_tarih in enumerate(tarihler[30:]):
    # Eğitim: test tarihinden önceki tüm veriler
    train_mask = df["_tarih"] < test_tarih
    test_mask = df["_tarih"] == test_tarih
    
    X_train = df.loc[train_mask, ozellikler].fillna(0)
    y_train = df.loc[train_mask, hedef]
    X_test = df.loc[test_mask, ozellikler].fillna(0)
    y_test = df.loc[test_mask, hedef]
    
    if len(y_test) < 4:  # en az 4 at olan yarışları say
        continue
    
    # Model eğit
    scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        scale_pos_weight=scale_pos,
        objective='binary:logistic', eval_metric='logloss',
        use_label_encoder=False, verbosity=0, tree_method='hist'
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    tahminler.extend(y_pred)
    gercekler.extend(y_test)

if len(gercekler) == 0:
    print("Test edilecek veri bulunamadı.")
    exit()

acc = accuracy_score(gercekler, tahminler)
auc = roc_auc_score(gercekler, tahminler)
print(f"\nGerçek Dünya Doğruluğu (Zaman Serisi): %{acc*100:.2f}")
print(f"Gerçek Dünya AUC: {auc:.4f}")
print(f"Toplam test edilen at sayısı: {len(gercekler)}")