@echo off
cd /d C:\Users\Barış\Desktop\TJK_Proje
echo %date% %time% Otomasyon basliyor...
python tjk_cekici.py >> otomasyon_log.txt 2>&1
python gecmis_cekici.py >> otomasyon_log.txt 2>&1
python istatistik_motoru.py >> otomasyon_log.txt 2>&1
python agirlik_optimize.py >> otomasyon_log.txt 2>&1
echo %date% %time% Tamamlandi >> otomasyon_log.txt