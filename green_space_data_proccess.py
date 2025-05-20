import geopandas as gpd

# Dosya adını belirtin
file_path = 'green_space.txt' # Yüklediğiniz dosyanın adı

# 1. GeoJSON dosyasını GeoDataFrame olarak yükle
try:
    gdf = gpd.read_file(file_path)
except Exception as e:
    print(f"Dosya okunurken bir hata oluştu: {e}")
    exit()

# 2. Veri hakkında bilgi edinme ve mahalle adı sütununu belirleme
print("Veri hakkında bilgiler:")
gdf.info()
print("\nİlk birkaç satır:")
print(gdf.head())
print("\nSütun adları:")
print(gdf.columns)

# LÜTFEN DİKKAT:
# Yukarıdaki çıktılardan (özellikle gdf.columns ve gdf.head() çıktıları)
# mahalle adlarını içeren sütunun adını belirlemeniz gerekmektedir.
# Örneğin, bu sütun 'MAHALLE_ADI', 'mahalle', 'name' gibi bir isimde olabilir.
# Aşağıdaki 'NEIGHBORHOOD_COLUMN_NAME_PLACEHOLDER' kısmını bu sütun adıyla değiştirin.
neighborhood_column = 'MAHALLE' # Örnek: 'MAHALLE_ADI'

# Kontrol: Belirtilen mahalle sütunu DataFrame'de var mı?
if neighborhood_column == 'NEIGHBORHOOD_COLUMN_NAME_PLACEHOLDER':
    print(f"\nLÜTFEN KOD İÇERİSİNDEKİ 'NEIGHBORHOOD_COLUMN_NAME_PLACEHOLDER' DEĞERİNİ")
    print(f"GERÇEK MAHALLE ADI SÜTUNUNUZLA DEĞİŞTİRİN.")
    print(f"Mevcut sütunlar: {list(gdf.columns)}")
    # Eğer sütun adı belirlenemiyorsa, örnek olarak ilk uygun görüneni kullanmaya çalışalım
    # Genellikle 'name', 'NAME', 'AD', 'adi' gibi isimler kullanılır.
    # Bu kısım, kullanıcıya bir başlangıç noktası vermek içindir.
    potential_cols = [col for col in gdf.columns if isinstance(gdf[col].iloc[0], str)]
    if potential_cols:
        print(f"Potansiyel mahalle adı sütunları olabilir: {potential_cols}")
        # neighborhood_column = potential_cols[0] # Otomatik seçimi aktif etmek için bu satırı açabilirsiniz
        # print(f"'{neighborhood_column}' sütunu mahalle adı olarak varsayılıyor. Yanlışsa düzeltin.")
    exit() # Kullanıcının sütun adını girmesi için burada durdurulur.

if neighborhood_column not in gdf.columns:
    print(f"\nHata: Belirtilen '{neighborhood_column}' sütunu veri setinde bulunamadı.")
    print(f"Lütfen geçerli bir sütun adı girin. Mevcut sütunlar: {list(gdf.columns)}")
    exit()

# 3. Projeksiyonu alan hesabı için uygun bir CRS'ye dönüştürme
# Genellikle GeoJSON dosyaları WGS84 (EPSG:4326) koordinat sistemindedir.
# Alanı metrekare cinsinden hesaplamak için yerel bir projeksiyon sistemi (örneğin İstanbul için UTM Zone 35N - EPSG:32635) kullanılır.
# Eğer verinizin CRS'si başlangıçta tanımlı değilse, onu ayarlamanız gerekebilir (örn: gdf.set_crs("EPSG:4326", inplace=True))
if gdf.crs is None:
    print("\nUyarı: Verinin Koordinat Referans Sistemi (CRS) tanımlı değil. EPSG:4326 (WGS84) varsayılıyor.")
    gdf = gdf.set_crs("EPSG:4326", allow_override=False) # allow_override=False daha güvenli
elif gdf.crs.to_string() != "EPSG:4326" and not gdf.crs.is_projected:
     print(f"\nUyarı: Verinin mevcut CRS'si {gdf.crs.to_string()} ve coğrafi bir sistem. Alan hesabı için dönüştürülüyor.")

# İstanbul için UTM Zone 35N (EPSG:32635) veya Türkiye için uygun bir projeksiyon (EPSG:5255 - TUREF TM 30)
# Daha genel bir yaklaşım olarak, verinin merkezine göre bir UTM zonu seçilebilir.
# Ancak, İstanbul için EPSG:32635 yaygın bir seçimdir.
try:
    gdf_projected = gdf.to_crs(epsg=32635) # İstanbul için UTM Zone 35N
except Exception as e:
    print(f"CRS dönüştürme sırasında hata: {e}")
    print("Lütfen verinizin geçerli bir coğrafi CRS'ye sahip olduğundan emin olun.")
    exit()

# 4. Her mahallenin alanını hesaplama (metrekare cinsinden)
gdf_projected['alan_metrekare'] = gdf_projected.geometry.area

# Alanı kilometrekareye çevirme
gdf_projected['alan_kilometrekare'] = gdf_projected['alan_metrekare'] / 1_000_000

# 5. Sonuçları gösterme
print(f"\nMahalleler ve Yüzölçümleri ({neighborhood_column} sütununa göre):")
results = gdf_projected[[neighborhood_column, 'alan_metrekare', 'alan_kilometrekare']]

# Eğer aynı mahalle adı birden fazla geometriye sahipse (multi-part features),
# ve bunları birleştirmek isterseniz, groupby kullanabilirsiniz.
# Genellikle her 'feature' tek bir mahalleyi temsil eder.
# aggregated_results = results.groupby(neighborhood_column).sum()
# print(aggregated_results.sort_values(by='alan_kilometrekare', ascending=False))

print(results.sort_values(by='alan_kilometrekare', ascending=False))

# Sonuçları bir CSV dosyasına kaydetmek isterseniz:
# output_csv_file = 'mahalle_yuzolcumu.csv'
# results.to_csv(output_csv_file, index=False, encoding='utf-8-sig')
# print(f"\nSonuçlar '{output_csv_file}' dosyasına kaydedildi.")