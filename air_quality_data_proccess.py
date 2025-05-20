import requests
import json
from datetime import datetime

API_BASE_URL = "https://api.ibb.gov.tr/havakalitesi/OpenDataPortalHandler/"

def get_stations():
    """Hava kalitesi ölçüm istasyonlarının listesini İBB API'sinden alır."""
    url = API_BASE_URL + "GetAQIStations"
    print(f"İstasyon listesi şu adresten alınıyor: {url}")
    try:
        response = requests.get(url, timeout=10) # 10 saniye timeout
        response.raise_for_status()  # HTTP hataları için (4xx veya 5xx) exception fırlatır
        return response.json()
    except requests.exceptions.Timeout:
        print("İstek zaman aşımına uğradı. Lütfen internet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"İstasyonlar getirilirken bir hata oluştu: {e}")
        return None
    except json.JSONDecodeError:
        print("API'den gelen istasyon verisi JSON formatında değil. Yanıt:")
        print(response.text if 'response' in locals() else "Yanıt alınamadı.")
        return None

def display_stations(stations):
    """İstasyon listesini kullanıcıya gösterir."""
    if not stations:
        print("Görüntülenecek istasyon bulunamadı.")
        return False # İstasyon bulunamadığını belirtmek için False döndür
    print("\n Mevcut Hava Kalitesi İstasyonları ")
    print("------------------------------------")
    for station in stations:
        # Bazı istasyon adları None olabilir, bunları kontrol edelim
        station_name = station.get('Name', 'İsim Yok')
        station_id = station.get('Id')
        if station_id: # Sadece ID'si olanları gösterelim
             print(f"ID: {station_id} - İsim: {station_name}")
    print("------------------------------------")
    return True # İstasyonlar başarıyla gösterildi

def get_air_quality_data(station_id, start_date_str, end_date_str):
    """Belirli bir istasyon ve zaman aralığı için hava kalitesi verilerini alır."""
    url = API_BASE_URL + "GetAQIByStationId"
    
    params = {
        'StationId': station_id,
        'StartDate': start_date_str, # API'nin beklediği format: dd.MM.yyyy HH:mm:ss
        'EndDate': end_date_str
    }
    
    print(f"\n{station_id} ID'li istasyon için '{start_date_str}' ile '{end_date_str}' tarihleri arasında veri alınıyor...")
    print(f"İstek atılan URL (parametreler ile): {requests.Request('GET', url, params=params).prepare().url}")

    try:
        response = requests.get(url, params=params, timeout=30) # Veri sorgusu için daha uzun timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Veri isteği zaman aşımına uğradı. Lütfen internet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Hava kalitesi verileri getirilirken bir hata oluştu: {e}")
        if response is not None:
            print(f"Sunucu Hatası Detayı: {response.status_code} - {response.text}")
        return None
    except json.JSONDecodeError:
        print("API'den gelen hava kalitesi verisi JSON formatında değil. Yanıt:")
        print(response.text if 'response' in locals() else "Yanıt alınamadı.")
        return None

def is_valid_station_id(station_id, stations):
    """Verilen station_id'nin geçerli (listede var olan) bir ID olup olmadığını kontrol eder."""
    if not stations:
        return False
    for station in stations:
        if station.get('Id') == station_id:
            return True
    return False

def main():
    """Ana uygulama fonksiyonu."""
    stations = get_stations()
    
    if not stations or not display_stations(stations):
        print("Program sonlandırılıyor.")
        return

    while True:
        station_id = input("Lütfen hava kalitesi verilerini almak istediğiniz istasyonun ID'sini girin: ").strip()
        if is_valid_station_id(station_id, stations):
            break
        else:
            print("Geçersiz istasyon ID'si. Lütfen yukarıdaki listeden geçerli bir ID girin.")

    print("\nLütfen başlangıç ve bitiş tarihlerini 'gg.AA.yyyy SS:dd:ss' formatında girin.")
    date_format = "%d.%m.%Y %H:%M:%S"
    example_date = "01.01.2023 00:00:00"
    print(f"Örnek: {example_date}")
    
    while True:
        start_date_str = input(f"Başlangıç Tarihi ({example_date}): ").strip()
        try:
            dt_start = datetime.strptime(start_date_str, date_format)
            break
        except ValueError:
            print(f"Geçersiz tarih formatı. Lütfen '{date_format.replace('%d','gg').replace('%m','AA').replace('%Y','yyyy').replace('%H','SS').replace('%M','dd').replace('%S','ss')}' formatında girin.")
            
    while True:
        end_date_str = input(f"Bitiş Tarihi ({example_date}): ").strip()
        try:
            dt_end = datetime.strptime(end_date_str, date_format)
            if dt_end < dt_start:
                print("Bitiş tarihi, başlangıç tarihinden önce olamaz. Lütfen geçerli bir tarih girin.")
                continue
            break
        except ValueError:
            print(f"Geçersiz tarih formatı. Lütfen '{date_format.replace('%d','gg').replace('%m','AA').replace('%Y','yyyy').replace('%H','SS').replace('%M','dd').replace('%S','ss')}' formatında girin.")
    
    air_quality_data = get_air_quality_data(station_id, start_date_str, end_date_str)
    
    if air_quality_data:
        print("\n Alınan Hava Kalitesi Verileri ")
        print("----------------------------------")
        # JSON verisini daha okunaklı bir şekilde yazdır
        print(json.dumps(air_quality_data, indent=4, ensure_ascii=False))
        
        # Örnek: Veri bir liste ise içindeki bazı önemli alanları yazdırma
        # if isinstance(air_quality_data, list) and air_quality_data:
        #     print("\nDetaylı Veri Özeti:")
        #     for record in air_quality_data:
        #         read_time = record.get('ReadTime', 'N/A')
        #         print(f"\nOkuma Zamanı: {read_time}")
        #         concentration = record.get('Concentration')
        #         if concentration:
        #             print("  Konsantrasyonlar:")
        #             for key, value in concentration.items():
        #                 print(f"    {key}: {value}")
        #         aqi = record.get('AQI')
        #         if aqi:
        #             print("  Hava Kalitesi İndeksleri (AQI):")
        #             for key, value in aqi.items():
        #                 print(f"    {key}: {value}")
        # else:
        #     print("\nVeri formatı beklenenden farklı veya boş.")

    else:
        print("Belirtilen kriterler için hava kalitesi verisi bulunamadı veya bir hata oluştu.")

if __name__ == "__main__":
    main()