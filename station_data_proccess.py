import pandas as pd
import geopandas as gpd

def match_stations_to_green_spaces(
    gdf_stations: gpd.GeoDataFrame,
    gdf_green_spaces: gpd.GeoDataFrame,
    station_name_col: str,
    gs_mahalle_col: str,
    max_nearest_distance: float = 5000
) -> pd.DataFrame:
    """
    İstasyonları ilgili yeşil alanlara göre mahallelerle eşleştirir.
    
    1. Adım: İstasyon yeşil alanın içinde mi? -> varsa mahalle atanır.
    2. Adım: Eğer değilse, en yakın yeşil alan bulunur -> mahalle atanır.

    Parametreler:
        gdf_stations: GeoDataFrame - istasyonların geometri ve bilgileri.
        gdf_green_spaces: GeoDataFrame - yeşil alanların geometri ve mahalle bilgileri.
        station_name_col: str - istasyon adı sütunu.
        gs_mahalle_col: str - yeşil alanların bağlı olduğu mahalle sütunu.
        max_nearest_distance: float - en yakın eşleşme için maksimum mesafe (metre).
    
    Döndürür:
        pd.DataFrame - her istasyon için mahalle ve eşleşme türünü içeren sonuçlar.
    """
    results = []

    # 1. ADIM: Yeşil alanların içinde olan istasyonları bul
    print("\n1. Adım: İstasyonlar yeşil alanların 'içinde' mi kontrol ediliyor...")
    rsuffix_within = '_gs_w'
    joined_within = gpd.sjoin(
        gdf_stations, gdf_green_spaces,
        how='left',
        predicate='within',
        rsuffix=rsuffix_within
    )

    processed_station_indices = set()
    gs_mahalle_col_from_join_within = f'{gs_mahalle_col}{rsuffix_within}'

    for idx, row in joined_within.iterrows():
        mahalle = row.get(gs_mahalle_col_from_join_within)
        station_name_val = row.get(station_name_col, f"İstasyon {idx}")
        if pd.notna(mahalle):
            results.append({
                'station_name': station_name_val,
                'assigned_mahalle': mahalle,
                'assignment_type': 'İçinde Yer Alan Yeşil Alan'
            })
            processed_station_indices.add(idx)

    # 2. ADIM: İçinde olmayanlar için en yakın yeşil alanı bul
    stations_outside_indices = gdf_stations.index.difference(processed_station_indices)
    stations_outside = gdf_stations.loc[stations_outside_indices]

    if not stations_outside.empty:
        print(f"\n2. Adım: {len(stations_outside)} istasyon için en yakın yeşil alan bulunuyor...")
        rsuffix_nearest = '_gs_n'
        # CRS dönüşümü: derece yerine metre bazlı sistem
        gdf_stations = gdf_stations.to_crs(epsg=3857)
        gdf_green_spaces = gdf_green_spaces.to_crs(epsg=3857)

        # En yakın yeşil alanla eşleştirme
        joined_nearest = gpd.sjoin_nearest(
            gdf_stations, 
            gdf_green_spaces, 
            how="left", 
            distance_col="distance"
        )

        gs_mahalle_col_from_join_nearest = f'{gs_mahalle_col}{rsuffix_nearest}'
        right_index_col_name_in_joined = f'index{rsuffix_nearest}'

        for idx, row in joined_nearest.iterrows():
            station_name_val = row.get(station_name_col, f"İstasyon {idx}")
            index_gs_n_value = row.get(right_index_col_name_in_joined)

            if pd.notna(index_gs_n_value):
                mahalle = row.get(gs_mahalle_col_from_join_nearest)
                if pd.notna(mahalle):
                    results.append({
                        'station_name': station_name_val,
                        'assigned_mahalle': mahalle,
                        'assignment_type': 'En Yakın Yeşil Alan'
                    })
                else:
                    results.append({
                        'station_name': station_name_val,
                        'assigned_mahalle': "En Yakın Yeşil Alan (Mahalle Bilgisi Eksik)",
                        'assignment_type': 'En Yakın Yeşil Alan - Bilgi Eksik'
                    })
            else:
                results.append({
                    'station_name': station_name_val,
                    'assigned_mahalle': "Yakın yeşil alan bulunamadı",
                    'assignment_type': 'Hata/Bağlantı Yok'
                })

    return pd.DataFrame(results)


# GeoDataFrame'leri yükle
gdf_stations = gpd.read_file("station_data.txt")
gdf_green_spaces = gpd.read_file("green_space.txt")

# Fonksiyonu çağır
results_df = match_stations_to_green_spaces(
    gdf_stations=gdf_stations,
    gdf_green_spaces=gdf_green_spaces,
    station_name_col='station_name',
    gs_mahalle_col='mahalle_adi'
)

# Sonuçları gör
print(results_df.head())
results_df.to_csv("mahalle_eşleşmeleri.csv", index=False)