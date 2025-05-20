import geopandas as gpd
import pandas as pd

def assign_stations_to_mahalle(stations_filepath, mahalle_filepath):
    """
    İstasyon noktalarını, sağlanan mahalle poligonlarına göre mahallelere atar.

    Parametreler:
        stations_filepath (str): İstasyon verilerini içeren GeoJSON dosyasının yolu.
        mahalle_filepath (str): Mahalle sınırlarını içeren GeoJSON dosyasının yolu.

    Döndürür:
        tuple: (gpd.GeoDataFrame, str) - Her istasyon için atanmış mahalle bilgilerini içeren GeoDataFrame
               ve mahalle adı sütununun adı. Eğer bir istasyon hiçbir mahalleye atanamazsa, mahalle bilgisi
               NaN (veya None) olacaktır.
    """
    try:
        # 1. Veri Yükleme
        print(f"İstasyon verisi yükleniyor: {stations_filepath}")
        gdf_stations = gpd.read_file(stations_filepath)
        if gdf_stations.empty:
            print("UYARI: İstasyon verisi boş veya yüklenemedi.")
            return None, None
        print(f"Yüklenen istasyon sayısı: {len(gdf_stations)}")
        print(f"İstasyon verisi CRS: {gdf_stations.crs}")

        print(f"\nMahalle sınırları verisi yükleniyor: {mahalle_filepath}")
        gdf_mahalleler = gpd.read_file(mahalle_filepath)
        if gdf_mahalleler.empty:
            print("UYARI: Mahalle verisi boş veya yüklenemedi.")
            return None, None
        print(f"Yüklenen mahalle poligonu sayısı: {len(gdf_mahalleler)}")
        print(f"Mahalle verisi CRS: {gdf_mahalleler.crs}")
        
        print("\nMahalle verisindeki ilk birkaç satırın 'properties' sütunu (veya tüm sütunlar):")
        print(gdf_mahalleler.head().to_string())
        
        mahalle_adı_sütunu = None
        olası_mahalle_sütunları = [
            'MAHALLE_AD', 'MAHALLEADI', 'mahalle_ad', 'mahalleadi', 
            'name', 'NAME', 'AD', 'MAH_AD', 
            'address.city',
            'display_name'
        ] 
        
        found_col = False
        for col in olası_mahalle_sütunları:
            if col in gdf_mahalleler.columns:
                mahalle_adı_sütunu = col
                print(f"\nOtomatik olarak '{mahalle_adı_sütunu}' mahalle adı sütunu olarak bulundu.")
                if not gdf_mahalleler.empty and mahalle_adı_sütunu in gdf_mahalleler.columns:
                    print(f"Örnek mahalle adı ('{mahalle_adı_sütunu}' sütunundan): {gdf_mahalleler[mahalle_adı_sütunu].iloc[0]}")
                found_col = True
                break
        
        if not found_col:
            if 'address' in gdf_mahalleler.columns and isinstance(gdf_mahalleler['address'].iloc[0], dict):
                if 'city' in gdf_mahalleler['address'].iloc[0]:
                    print("\n'address' sütunu içinde 'city' anahtarı bulundu. Yeni bir sütun oluşturuluyor.")
                    gdf_mahalleler['extracted_mahalle_adi'] = gdf_mahalleler['address'].apply(lambda x: x.get('city') if isinstance(x, dict) else None)
                    mahalle_adı_sütunu = 'extracted_mahalle_adi'
                    print(f"Örnek mahalle adı ('{mahalle_adı_sütunu}' sütunundan): {gdf_mahalleler[mahalle_adı_sütunu].iloc[0]}")
                    found_col = True

        if not found_col:
            print("\nUYARI: Mahalle adı sütunu otomatik olarak bulunamadı.")
            print(f"Lütfen gdf_mahalleler.columns çıktısını kontrol edin: {gdf_mahalleler.columns.tolist()}")
            user_mahalle_col = input("Lütfen mahalle adlarını içeren sütunun adını manuel olarak girin: ")
            if user_mahalle_col in gdf_mahalleler.columns:
                mahalle_adı_sütunu = user_mahalle_col
            else:
                print(f"HATA: Girdiğiniz '{user_mahalle_col}' sütunu mahalle verisinde bulunamadı.")
                return None, None
        
        # 2. CRS Kontrolü ve Dönüşümü
        if gdf_stations.crs != gdf_mahalleler.crs:
            print(f"\nCRS'ler farklı. İstasyon verisi ({gdf_stations.crs}) mahalle verisi CRS'ine ({gdf_mahalleler.crs}) dönüştürülüyor.")
            try:
                gdf_stations = gdf_stations.to_crs(gdf_mahalleler.crs)
                print(f"İstasyon verisi başarıyla {gdf_mahalleler.crs} CRS'ine dönüştürüldü.")
            except Exception as e:
                print(f"CRS dönüşüm hatası: {e}. Lütfen CRS'leri manuel olarak kontrol edin.")
                return None, None
        else:
            print(f"\nCRS'ler aynı: {gdf_stations.crs}")

        # 3. Mekansal Birleştirme (Spatial Join)
        print("\nMekansal birleştirme (spatial join) yapılıyor ('within' predicate ile)...")
        gdf_mahalleler_simplified = gdf_mahalleler[[mahalle_adı_sütunu, 'geometry']].copy()
        joined_gdf = gpd.sjoin(gdf_stations, gdf_mahalleler_simplified, how='left', predicate='within')

        if 'index_right' in joined_gdf.columns:
            joined_gdf = joined_gdf.drop(columns=['index_right'])
            
        print("\nEşleştirme tamamlandı.")
        return joined_gdf, mahalle_adı_sütunu

    except FileNotFoundError as e:
        print(f"HATA: Dosya bulunamadı - {e}")
        return None, None
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# --- Script'i Çalıştırma ---
if __name__ == "__main__":
    stations_file = "station_data.txt"  # İstasyon dosyanızın adı
    mahalle_boundaries_file = "mahalle_geojson.json"  # Yeni mahalle sınırı dosyanızın adı

    # Fonksiyonu çağır
    stations_with_mahalle = assign_stations_to_mahalle(stations_file, mahalle_boundaries_file)

    if stations_with_mahalle is not None and not stations_with_mahalle:
        print("\n--- İstasyonlar ve Atanmış Mahalleler (İlk 20) ---")
        print(stations_with_mahalle.head(20).to_string())

        # Hangi istasyonların mahalle bulamadığını kontrol et
        unassigned_stations_count = stations_with_mahalle[stations_with_mahalle.columns[-1]].isnull().sum() # Son eklenen mahalle sütununa bakar
        # Veya eğer mahalle adı sütununu biliyorsak:
        # Örneğin, eğer mahalle adı sütunu 'extracted_mahalle_adi' ise:
        # unassigned_stations_count = stations_with_mahalle['extracted_mahalle_adi'].isnull().sum()
        # Bunu daha genel yapmak için, sjoin'dan sonra eklenen ve mahalle adını içeren sütunu bulmamız gerek.
        # Bu genellikle gdf_mahalleler_simplified'dan gelen sütundur.
        
        # Mahalle adı sütununu (dinamik olarak belirlenen) kullanarak kontrol edelim
        mahalle_sutun_adi_son_hal = None
        # `assign_stations_to_mahalle` fonksiyonunda belirlenen `mahalle_adı_sütunu` nu burada tekrar belirlemek yerine,
        # çıktıyı inceleyerek hangi sütunun mahalle adını taşıdığını görebiliriz.
        # Genellikle bu, `gdf_mahalleler_simplified` dan gelen sütundur.
        # Geçici olarak, en sağdaki geometri olmayan sütunun mahalle adı olduğunu varsayabiliriz,
        # veya script'in başında belirlenen `mahalle_adı_sütunu` adını bir şekilde alabiliriz.
        # Şimdilik, sütun adını bilerek yazalım (örneğin yukarıda 'extracted_mahalle_adi' veya 'display_name' gibi)
    # Fonksiyonu çağır
    stations_with_mahalle, mahalle_adı_sütunu = assign_stations_to_mahalle(stations_file, mahalle_boundaries_file)

    if stations_with_mahalle is not None and not stations_with_mahalle.empty:
        print("\n--- İstasyonlar ve Atanmış Mahalleler (İlk 20) ---")
        print(stations_with_mahalle.head(20).to_string())

        # Hangi istasyonların mahalle bulamadığını kontrol et
        if mahalle_adı_sütunu is not None and mahalle_adı_sütunu in stations_with_mahalle.columns:
            unassigned_stations_count = stations_with_mahalle[mahalle_adı_sütunu].isnull().sum()
            print(f"\nToplam {unassigned_stations_count} istasyon herhangi bir mahalleye atanamadı (mahalle bilgisi boş).")
        else:
            print("\nMahalle adı sütunu çıktıda bulunamadı, atanamayan istasyon sayısı kontrol edilemiyor.")

        output_filename = "stations_assigned_to_mahalle_boundaries.csv"
        try:
            stations_with_mahalle.drop(columns=['geometry']).to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"\nSonuçlar (geometrisiz) '{output_filename}' dosyasına kaydedildi.")
            
            output_geojson_filename = "stations_assigned_to_mahalle_boundaries.geojson"
            stations_with_mahalle.to_file(output_geojson_filename, driver="GeoJSON")
            print(f"Sonuçlar (geometrili) '{output_geojson_filename}' dosyasına kaydedildi.")

        except Exception as e:
            print(f"Dosya kaydı sırasında hata: {e}")
            
    elif stations_with_mahalle is not None and stations_with_mahalle.empty:
        print("\nEşleştirme sonucu boş bir GeoDataFrame üretti.")
    else:
        print("\nİşlem sırasında bir hata oluştu, sonuç üretilemedi.")
