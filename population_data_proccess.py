import pandas as pd
import json
import re

# --- Nüfus Verisini Yükle ---
try:
    # İlk 4 satır başlık/boş olduğundan atla, 5. satırı ilk veri satırı olarak kullan.
    # Dosya | ile ayrılmış durumda.
    population_df = pd.read_csv("population.csv", delimiter="|", skiprows=4, header=None)
    # Gözlemlenen yapıya göre sütun adlarını ata
    # Sütun 0: Yıl (tutarsız görünüyor, düşürülebilir veya doğrulanabilir)
    # Sütun 1: Ham Bilgi metni (örn: "İstanbul(Adalar/Adalar Bel./Burgazada Mah.)-40139")
    # Sütun 2: Nüfus
    # Sütun 3: Tamamen NaN (düşürülecek)
    population_df.columns = ['Year_or_Index', 'RawMahalleInfo', 'Population', 'EmptyCol']

    print("--- Ham Nüfus Verisi (atlanan satırlardan sonraki ilk 5 satır) ---")
    print(population_df.head())

except Exception as e:
    print(f"population.csv yüklenirken veya başlangıçta işlenirken hata: {e}")
    population_df = None

# --- Nüfus Verisini Temizle ---
if population_df is not None:
    # Boş sütunu ve indeks veya tutarsız yıl gibi görünen ilk sütunu düşür
    population_df = population_df.drop(columns=['EmptyCol', 'Year_or_Index'], errors='ignore')

    # 'RawMahalleInfo' veya 'Population' NaN olan satırları düşür (bunlar sonda kalan boş/özet satırları olabilir)
    population_df.dropna(subset=['RawMahalleInfo', 'Population'], inplace=True)
    
    # Nüfus sütununu sayısal tipe dönüştür, hataları NaN yap (sonra bunları düşürebiliriz)
    population_df['Population'] = pd.to_numeric(population_df['Population'], errors='coerce')
    population_df.dropna(subset=['Population'], inplace=True) # Sayısala dönüştürülemeyenleri (NaN) düşür
    population_df['Population'] = population_df['Population'].astype(int)

    # İlçe ve Mahalle bilgilerini çıkaran fonksiyon
    def extract_info(raw_info):
        if not isinstance(raw_info, str):
            return None, None
        
        ilce, mahalle = None, None
        # Parantez içindeki içeriği daha sağlam yakala: (içerik)?(?:-|$)
        inner_content_match = re.search(r'\((.*?)\)?(?:-|$)', raw_info) 
        if inner_content_match:
            inner_content = inner_content_match.group(1)
            path_parts = inner_content.split('/') # Parantez içindeki metni '/' ile böl
            
            if path_parts: # Eğer parçalar varsa
                ilce = path_parts[0].strip() # İlk parça İlçe'dir
            
            # Mahalle adını bul: ' Mah.' ile biten kısım
            for part in reversed(path_parts): # Parçaları sondan başlayarak kontrol et
                if ' Mah.' in part:
                    mahalle = part.replace(' Mah.', '').strip() # ' Mah.' kısmını temizle
                    break
                # Mahalle adının " Mah." içermediği ancak son kısım olduğu durumlar için fallback
                # Bu temel bir fallback olup, uç durumlar için iyileştirme gerekebilir.
                elif part == path_parts[-1] and not mahalle: # Eğer son parça ise ve henüz mahalle bulunmadıysa
                    # "Bel." gibi ifadelerin mahalle olarak alınmasını engelle
                    if " Bel." not in part:
                         mahalle = part.strip() # Olduğu gibi al, ancak bu riskli olabilir

        return ilce, mahalle

    # 'RawMahalleInfo' sütununa fonksiyonu uygula ve yeni sütunlar oluştur
    extracted_info = population_df['RawMahalleInfo'].apply(lambda x: pd.Series(extract_info(x)))
    population_df['Ilce'] = extracted_info[0]
    population_df['Mahalle'] = extracted_info[1]

    # İlçe adlarını normalleştir: büyük harf.
    # Düzeltildi: .str.upper() argüman almaz.
    population_df['Ilce_Normalized'] = population_df['Ilce'].str.upper() if population_df['Ilce'].notna().any() else None
    
    # İlçe veya Mahalle çıkarılamayan satırları düşür
    population_df.dropna(subset=['Ilce', 'Mahalle', 'Ilce_Normalized'], inplace=True)
    
    # Son sütunları seç ve yeniden adlandır
    population_df_cleaned = population_df[['Ilce', 'Mahalle', 'Population', 'Ilce_Normalized']].copy()

    print("\n--- Temizlenmiş Nüfus Verisi (ilk 5 satır) ---")
    print(population_df_cleaned.head())
    print(f"\nNüfus verisindeki benzersiz ilçe adları (örnek): {population_df_cleaned['Ilce_Normalized'].unique()[:5]}")

else:
    population_df_cleaned = None

# --- Yeşil Alan Verisini Yükle ve İşle ---
green_space_df = None
districts_with_green_space = set()
try:
    with open("green_space.txt", 'r', encoding='utf-8') as f:
        green_space_data = json.load(f) # JSON dosyasını yükle

    if green_space_data and 'features' in green_space_data:
        features = green_space_data['features']
        park_data = []
        for feature in features: # Her bir coğrafi öğe için
            properties = feature.get('properties', {})
            park_name = properties.get('MAHALLE') # Bu parkın adıdır
            district = properties.get('ILCE')     # Bu ilçedir
            if park_name and district:
                park_data.append({'ParkAdi': park_name, 'Ilce': district})
        
        if park_data:
            green_space_df = pd.DataFrame(park_data)
            # Yeşil alan verisindeki ilçe adlarını normalleştir
            # Düzeltildi: .str.upper() argüman almaz.
            green_space_df['Ilce_Normalized'] = green_space_df['Ilce'].str.upper()
            
            # Yeşil alana sahip benzersiz ilçe adlarını bir sete al
            districts_with_green_space = set(green_space_df['Ilce_Normalized'].unique())
            print("\n--- Yeşil Alan Verisi (ilk 5 satır) ---")
            print(green_space_df.head())
            print(f"\nYeşil alana sahip benzersiz ilçe sayısı: {len(districts_with_green_space)}")
            print(f"Yeşil alana sahip örnek ilçeler: {list(districts_with_green_space)[:10]}")
        else:
            print("green_space.txt özelliklerinde geçerli park verisi bulunamadı.")
            
    else:
        print("Yeşil alan verisi boş veya beklenen GeoJSON formatında değil.")

except FileNotFoundError:
    print("Hata: green_space.txt bulunamadı.")
except json.JSONDecodeError as e:
    print(f"green_space.txt dosyasından JSON çözümlenirken hata: {e}")
except Exception as e:
    print(f"green_space.txt ile beklenmeyen bir hata oluştu: {e}")


# --- Nüfus Verisini Yeşil Alan Bilgisiyle Eşleştir ---
matched_df = None
if population_df_cleaned is not None and districts_with_green_space:
    # Nüfus verisini, ilçeleri yeşil alana sahip olanlarla filtrele
    population_in_green_districts = population_df_cleaned[
        population_df_cleaned['Ilce_Normalized'].isin(districts_with_green_space)
    ].copy() # SettingWithCopyWarning'den kaçınmak için .copy() kullan

    # Sütunları Türkçe adlarla yeniden adlandır
    population_in_green_districts.rename(columns={'Ilce': 'İlçe', 'Mahalle': 'Mahalle Adı', 'Population': 'Nüfus'}, inplace=True)
    
    # Sadece istenen sütunları seç
    matched_df = population_in_green_districts[['İlçe', 'Mahalle Adı', 'Nüfus']]
    
    print("\n--- Yeşil Alana Sahip İlçelerdeki Mahallelerin Nüfus Verisi (ilk 10) ---")
    print(matched_df.head(10))
    print(f"\nYeşil alana sahip ilçelerde bulunan toplam mahalle sayısı: {len(matched_df)}")

    # Sonucu CSV dosyasına kaydet (UTF-8 encoding ile Türkçe karakter sorunlarını önle)
    matched_df.to_csv("nufus_yesil_alanli_ilcelerde.csv", index=False, encoding='utf-8-sig')
    print("\nEşleştirilmiş veri 'nufus_yesil_alanli_ilcelerde.csv' dosyasına kaydedildi.")

elif population_df_cleaned is None:
    print("\nNüfus verisi işlenemedi. Eşleştirme yapılamıyor.")
else:
    print("\nYeşil alan ilçe bilgisi bulunamadı. Eşleştirme yapılamıyor.")