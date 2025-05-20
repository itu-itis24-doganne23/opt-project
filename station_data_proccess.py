import pandas as pd
import geopandas as gpd

def match_stations_to_neighborhoods_from_green_spaces(
    gdf_stations: gpd.GeoDataFrame,
    gdf_green_areas_with_mahalle: gpd.GeoDataFrame,
    station_name_col: str,
    mahalle_col_in_green_areas: str,
    max_nearest_distance: float = 2000  # Metre cinsinden varsayılan maksimum arama mesafesi
) -> pd.DataFrame:
    """
    İstasyonları, yeşil alanların 'MAHALLE' özelliğini kullanarak mahallelerle eşleştirir.

    Öncelik Sırası:
    1. İstasyon bir yeşil alan poligonunun 'içinde' mi? -> Poligonun 'MAHALLE'si atanır.
    2. Eğer içinde değilse, en yakın yeşil alan poligonu bulunur (belirtilen max_distance içinde)
       -> O poligonun 'MAHALLE'si atanır.

    Parametreler:
        gdf_stations: GeoDataFrame - istasyonların geometri ve bilgileri.
        gdf_green_areas_with_mahalle: GeoDataFrame - mahalle bilgisi içeren yeşil alan poligonları.
        station_name_col: str - gdf_stations'daki istasyon adı sütunu.
        mahalle_col_in_green_areas: str - gdf_green_areas_with_mahalle'deki mahalle adı sütunu.
        max_nearest_distance: float - en yakın eşleşme için maksimum arama mesafesi (metre).

    Döndürür:
        pd.DataFrame - her istasyon için atanan mahalle ve eşleşme türünü içeren sonuçlar.
    """
    results = []

    # CRS (Koordinat Referans Sistemi) kontrolü ve dönüşümü
    # Coğrafi veriler için genellikle WGS84 (EPSG:4326) kullanılır.
    # Mesafe bazlı işlemler için (sjoin_nearest gibi) yansıtılmış bir CRS'ye (örn: EPSG:32635 for Istanbul)
    # dönüştürmek daha doğrudur.

    # Gelen GeoDataFrame'lerin CRS'lerini kontrol et
    if gdf_stations.crs is None:
        print("UYARI: İstasyon GeoDataFrame'inde CRS tanımlı değil. EPSG:4326 (WGS84) varsayılıyor.")
        gdf_stations = gdf_stations.set_crs("EPSG:4326", allow_override=True)
    if gdf_green_areas_with_mahalle.crs is None:
        print("UYARI: Yeşil Alan GeoDataFrame'inde CRS tanımlı değil. EPSG:4326 (WGS84) varsayılıyor.")
        gdf_green_areas_with_mahalle = gdf_green_areas_with_mahalle.set_crs("EPSG:4326", allow_override=True)

    # İstanbul için uygun bir yansıtılmış CRS (UTM Zone 35N)
    target_crs = "EPSG:32635"
    try:
        gdf_stations_proj = gdf_stations.to_crs(target_crs)
        gdf_green_areas_proj = gdf_green_areas_with_mahalle.to_crs(target_crs)
    except Exception as e:
        print(f"CRS'leri {target_crs}'ye dönüştürürken hata: {e}. Orijinal CRS'ler ile devam ediliyor.")
        print("Mesafe bazlı eşleştirmeler hatalı olabilir.")
        gdf_stations_proj = gdf_stations.copy() # Kopyalarını kullan
        gdf_green_areas_proj = gdf_green_areas_with_mahalle.copy()


    # 1. ADIM: Yeşil alan poligonlarının 'içinde' olan istasyonları bul
    print("\n1. Adım: İstasyonlar yeşil alan poligonlarının 'içinde' mi kontrol ediliyor...")
    # `sjoin` için sağ GeoDataFrame'den sadece gerekli sütunları alalım ve index adını değiştirelim
    green_areas_simplified = gdf_green_areas_proj[[mahalle_col_in_green_areas, 'geometry']].copy()
    # Olası index adı çakışmasını önlemek için sağ taraftaki index adını değiştirebiliriz.
    # Ancak geopandas >0.7.0 için bu genellikle otomatik yönetilir.
    # green_areas_simplified.index.name = 'index_green_space'

    # `op` yerine `predicate` kullanılması güncel geopandas versiyonlarında önerilir.
    joined_within = gpd.sjoin(
        gdf_stations_proj, # Projeksiyonlu istasyonlar
        green_areas_simplified, # Projeksiyonlu ve sadeleştirilmiş yeşil alanlar
        how="left",
        predicate="within"
    )

    stations_processed_indices = set()

    for original_index, row in joined_within.iterrows(): # original_index, gdf_stations_proj'un index'idir
        station_name_val = gdf_stations.loc[original_index, station_name_col] # Orijinal GDF'den adı al
        # `sjoin` sonrası eşleşen poligonun bilgileri (mahalle_col_in_green_areas) eklenir.
        # Eğer eşleşme yoksa bu sütun NaN olur.
        assigned_mahalle_val = row.get(mahalle_col_in_green_areas)

        if pd.notna(assigned_mahalle_val):
            results.append({
                'station_name': station_name_val,
                'assigned_mahalle': assigned_mahalle_val,
                'assignment_type': 'İçinde (Yeşil Alan Poligonu)'
            })
            stations_processed_indices.add(original_index)

    print(f"{len(stations_processed_indices)} istasyon bir yeşil alan poligonu içinde bulundu.")

    # 2. ADIM: 'İçinde' eşleşmesi olmayan istasyonlar için en yakın yeşil alan poligonunu bul
    # Orijinal gdf_stations_proj DataFrame'inden işlenmemiş istasyonları al (orijinal index'lerine göre)
    remaining_stations_indices = gdf_stations_proj.index.difference(stations_processed_indices)
    remaining_stations_proj = gdf_stations_proj.loc[remaining_stations_indices]

    if not remaining_stations_proj.empty:
        print(f"\n2. Adım: Kalan {len(remaining_stations_proj)} istasyon için en yakın yeşil alan poligonu (mahalle bilgisiyle) bulunuyor (max_distance={max_nearest_distance}m)...")

        joined_nearest = gpd.sjoin_nearest(
            remaining_stations_proj, # Kalan projeksiyonlu istasyonlar
            green_areas_simplified,  # Projeksiyonlu ve sadeleştirilmiş yeşil alanlar
            how="left",
            max_distance=max_nearest_distance # Metre cinsinden
        )

        for original_index, row in joined_nearest.iterrows(): # original_index, remaining_stations_proj'un index'idir
            station_name_val = gdf_stations.loc[original_index, station_name_col] # Orijinal GDF'den adı al
            assigned_mahalle_val = row.get(mahalle_col_in_green_areas)

            if pd.notna(assigned_mahalle_val):
                results.append({
                    'station_name': station_name_val,
                    'assigned_mahalle': assigned_mahalle_val,
                    'assignment_type': f'En Yakın (Yeşil Alan Poligonu, <= {max_nearest_distance}m)'
                })
            else:
                results.append({
                    'station_name': station_name_val,
                    'assigned_mahalle': "Eşleşen Mahalle Yok (Mesafe Dışı veya Yakın Poligon Yok)",
                    'assignment_type': 'Eşleşme Yok (Mesafe Dışı)'
                })
            stations_processed_indices.add(original_index) # Bu istasyon da işlendi.
    
    # Eğer herhangi bir sebeple (örn: CRS sorunları veya boş girdi) hiçbir şekilde işlenemeyen istasyon kaldıysa
    # Bu durumun oluşmaması beklenir.
    # all_original_indices = set(gdf_stations_proj.index)
    # final_unprocessed_indices = all_original_indices.difference(stations_processed_indices)
    # if final_unprocessed_indices:
    #     for original_index in final_unprocessed_indices:
    #         station_name_val = gdf_stations.loc[original_index, station_name_col]
    #         results.append({
    #             'station_name': station_name_val,
    #             'assigned_mahalle': "İşlenemedi/Bilinmeyen Hata",
    #             'assignment_type': 'Hata'
    #         })

    return pd.DataFrame(results)

# --- Ana Script Mantığı ---
if __name__ == "__main__":
    try:
        print("İstasyon verisi yükleniyor: station_data.txt")
        gdf_stations = gpd.read_file("station_data.txt")
        if gdf_stations.empty:
            print("UYARI: İstasyon verisi (station_data.txt) boş veya yüklenemedi.")
            exit()
        print(f"Yüklenen istasyon sayısı: {len(gdf_stations)}")
        # print(f"İstasyon verisi CRS (yükleme sonrası): {gdf_stations.crs}")
        # print(f"İstasyon verisi sütunları: {gdf_stations.columns.tolist()}")


        print("\nYeşil alan (mahalle bilgisi içeren) verisi yükleniyor: green_space.txt")
        gdf_green_spaces = gpd.read_file("green_space.txt")
        if gdf_green_spaces.empty:
            print("UYARI: Yeşil alan verisi (green_space.txt) boş veya yüklenemedi.")
            exit()
        print(f"Yüklenen yeşil alan poligon sayısı: {len(gdf_green_spaces)}")
        # print(f"Yeşil alan verisi CRS (yükleme sonrası): {gdf_green_spaces.crs}")
        # print(f"Yeşil alan verisi sütunları: {gdf_green_spaces.columns.tolist()}")


        station_column = "ISTASYON"  # station_data.txt'deki istasyon adı sütunu
        mahalle_column_in_green_space = "MAHALLE"  # green_space.txt'deki mahalle adı sütunu

        if station_column not in gdf_stations.columns:
            print(f"HATA: İstasyon verisinde '{station_column}' sütunu bulunamadı. Mevcut sütunlar: {gdf_stations.columns.tolist()}")
            exit()
        if mahalle_column_in_green_space not in gdf_green_spaces.columns:
            print(f"HATA: Yeşil alan verisinde '{mahalle_column_in_green_space}' sütunu bulunamadı. Mevcut sütunlar: {gdf_green_spaces.columns.tolist()}")
            exit()
        if 'geometry' not in gdf_green_spaces.columns or 'geometry' not in gdf_stations.columns:
            print("HATA: Gerekli 'geometry' sütunu GeoDataFrame'lerden birinde veya her ikisinde eksik.")
            exit()


        results_df = match_stations_to_neighborhoods_from_green_spaces(
            gdf_stations=gdf_stations,
            gdf_green_areas_with_mahalle=gdf_green_spaces,
            station_name_col=station_column,
            mahalle_col_in_green_areas=mahalle_column_in_green_space,
            max_nearest_distance=2000  # En yakın arama için maksimum mesafe (metre), örn: 2 km
        )

        print("\n--- Eşleştirme Sonuçları ---")
        if not results_df.empty:
            print(results_df.head())
            print(f"\nToplam {len(results_df)} istasyon işlendi.")
            print("\nEşleşme Türlerine Göre Dağılım:")
            print(results_df['assignment_type'].value_counts(dropna=False))

            output_filename = "stations_with_assigned_mahalle.csv"
            results_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"\nSonuçlar '{output_filename}' dosyasına kaydedildi.")
        else:
            print("Eşleştirme sonucu üretilemedi veya sonuç boş.")

    except FileNotFoundError as e:
        print(f"HATA: Dosya bulunamadı - {e}. Lütfen 'station_data.txt' ve 'green_space.txt' dosyalarının doğru yolda olduğundan emin olun.")
    except Exception as e:
        print(f"Beklenmeyen bir genel hata oluştu: {e}")
        import traceback
        traceback.print_exc()