import geopandas as gpd
import pandas as pd

def assign_points_to_mahalle(points_filepath, points_name_col_hint, mahalle_filepath):
    """
    Nokta verilerini (istasyon, durak vb.), sağlanan mahalle poligonlarına göre mahallelere atar.

    Parametreler:
        points_filepath (str): Nokta verilerini içeren GeoJSON dosyasının yolu.
        points_name_col_hint (str): Nokta adını içeren sütun için bir ipucu/beklenen ad.
                                     Bu, özellikle çıktı için kullanılır. Join işlemi geometri tabanlıdır.
        mahalle_filepath (str): Mahalle sınırlarını içeren GeoJSON dosyasının yolu.

    Döndürür:
        gpd.GeoDataFrame: Her nokta için atanmış mahalle bilgilerini içeren GeoDataFrame.
                          Eğer bir nokta hiçbir mahalleye atanamazsa, mahalle bilgisi
                          NaN (veya None) olacaktır.
    """
    try:
        # 1. Veri Yükleme
        print(f"Nokta verisi (örn: duraklar/istasyonlar) yükleniyor: {points_filepath}")
        gdf_points = gpd.read_file(points_filepath)
        if gdf_points.empty:
            print("UYARI: Nokta verisi boş veya yüklenemedi.")
            return None
        print(f"Yüklenen nokta sayısı: {len(gdf_points)}")
        print(f"Nokta verisi CRS: {gdf_points.crs}")
        # print(f"Nokta verisi sütunları: {gdf_points.columns.tolist()}")
        # if points_name_col_hint not in gdf_points.columns:
        #     print(f"UYARI: Belirtilen nokta adı sütunu '{points_name_col_hint}' veride bulunamadı. Mevcut sütunlar: {gdf_points.columns.tolist()}")


        print(f"\nMahalle sınırları verisi yükleniyor: {mahalle_filepath}")
        gdf_mahalleler = gpd.read_file(mahalle_filepath)
        if gdf_mahalleler.empty:
            print("UYARI: Mahalle verisi boş veya yüklenemedi.")
            return None
        print(f"Yüklenen mahalle poligonu sayısı: {len(gdf_mahalleler)}")
        print(f"Mahalle verisi CRS: {gdf_mahalleler.crs}")
        
        # Mahalle adı sütununu belirleme (bir önceki script'teki gibi)
        mahalle_adı_sütunu = None
        olası_mahalle_sütunları = [
            'MAHALLE_AD', 'MAHALLEADI', 'mahalle_ad', 'mahalleadi', 
            'name', 'NAME', 'AD', 'MAH_AD', 'address.city', 'display_name'
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
                    print("\n'address' sütunu içinde 'city' anahtarı bulundu. Yeni bir sütun ('extracted_mahalle_adi') oluşturuluyor.")
                    gdf_mahalleler['extracted_mahalle_adi'] = gdf_mahalleler['address'].apply(lambda x: x.get('city') if isinstance(x, dict) else None)
                    mahalle_adı_sütunu = 'extracted_mahalle_adi'
                    if not gdf_mahalleler.empty:
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
                return None
        
        # 2. CRS Kontrolü ve Dönüşümü
        if gdf_points.crs != gdf_mahalleler.crs:
            print(f"\nCRS'ler farklı. Nokta verisi ({gdf_points.crs}) mahalle verisi CRS'ine ({gdf_mahalleler.crs}) dönüştürülüyor.")
            try:
                gdf_points = gdf_points.to_crs(gdf_mahalleler.crs)
                print(f"Nokta verisi başarıyla {gdf_mahalleler.crs} CRS'ine dönüştürüldü.")
            except Exception as e:
                print(f"CRS dönüşüm hatası: {e}. Lütfen CRS'leri manuel olarak kontrol edin.")
                return None
        else:
            print(f"\nCRS'ler aynı: {gdf_points.crs}")

        # 3. Mekansal Birleştirme (Spatial Join)
        print("\nMekansal birleştirme (spatial join) yapılıyor ('within' predicate ile)...")
        gdf_mahalleler_simplified = gdf_mahalleler[[mahalle_adı_sütunu, 'geometry']].copy()
        
        joined_gdf = gpd.sjoin(gdf_points, gdf_mahalleler_simplified, how='left', predicate='within')
        
        if 'index_right' in joined_gdf.columns:
            joined_gdf = joined_gdf.drop(columns=['index_right'])
            
        print("\nEşleştirme tamamlandı.")
        return joined_gdf, mahalle_adı_sütunu # Mahalle adı sütununu da döndür

    except FileNotFoundError as e:
        print(f"HATA: Dosya bulunamadı - {e}")
        return None, None
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        return None, None
# Script'in ana çalıştırma bloğu (Minibüs durakları için güncellenmiş)
if __name__ == "__main__":
    # Minibüs durakları için dosya adı ve durak adı sütunu ipucu
    points_data_file = "minibus_station.json"
    point_name_column_hint = "DURAK_ADI" # minibus_station.json içindeki durak adı sütunu
    output_prefix = "minibus_duraklari"

    # Mahalle sınırları dosyası (bu değişmiyor)
    mahalle_boundaries_file = "mahalle_geojson.json"

    # Fonksiyonu çağır (assign_points_to_mahalle fonksiyonunun yukarıda tanımlı olduğunu varsayıyoruz)
    points_with_mahalle_gdf, assigned_mahalle_col_name = assign_points_to_mahalle(
        points_data_file,
        point_name_column_hint,
        mahalle_boundaries_file
    )

    if points_with_mahalle_gdf is not None and not points_with_mahalle_gdf.empty:
        print(f"\n--- {output_prefix.replace('_', ' ').title()} ve Atanmış Mahalleler (İlk 20) ---")
        display_cols = []
        if point_name_column_hint in points_with_mahalle_gdf.columns:
            display_cols.append(point_name_column_hint)
        if assigned_mahalle_col_name and assigned_mahalle_col_name in points_with_mahalle_gdf.columns:
            display_cols.append(assigned_mahalle_col_name)

        if display_cols:
            print(points_with_mahalle_gdf[display_cols].head(20).to_string())
        else:
            print(points_with_mahalle_gdf.head(20).to_string())

        if assigned_mahalle_col_name and assigned_mahalle_col_name in points_with_mahalle_gdf.columns:
            unassigned_points_count = points_with_mahalle_gdf[assigned_mahalle_col_name].isnull().sum()
            print(f"\nToplam {unassigned_points_count} nokta (durak) herhangi bir mahalleye atanamadı (mahalle bilgisi boş).")
        else:
            print("\nMahalle adı sütunu çıktıda bulunamadı, atanamayan nokta sayısı kontrol edilemiyor.")

        output_csv_filename = f"{output_prefix}_mahalle_eslesmis.csv"
        output_geojson_filename = f"{output_prefix}_mahalle_eslesmis.geojson"

        try:
            cols_to_save_csv = [col for col in points_with_mahalle_gdf.columns if col != 'geometry']
            points_with_mahalle_gdf[cols_to_save_csv].to_csv(output_csv_filename, index=False, encoding='utf-8-sig')
            print(f"\nSonuçlar (geometrisiz) '{output_csv_filename}' dosyasına kaydedildi.")

            points_with_mahalle_gdf.to_file(output_geojson_filename, driver="GeoJSON")
            print(f"Sonuçlar (geometrili) '{output_geojson_filename}' dosyasına kaydedildi.")

        except Exception as e:
            print(f"Dosya kaydı sırasında hata: {e}")

    elif points_with_mahalle_gdf is not None and points_with_mahalle_gdf.empty:
        print("\nEşleştirme sonucu boş bir GeoDataFrame üretti.")
    else:
        print("\nİşlem sırasında bir hata oluştu veya fonksiyon None döndürdü, sonuç üretilemedi.")