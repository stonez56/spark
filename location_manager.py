import urllib.request
import json
import urllib.parse
import settings_manager

def get_location():
    """
    Read location settings from settings.json.
    """
    settings = settings_manager.load_settings()
    return {
        "city": settings.get("user_city", ""),
        "district": settings.get("user_district", ""),
        "latitude": settings.get("user_latitude", None),
        "longitude": settings.get("user_longitude", None)
    }

def save_location(city, district, latitude=None, longitude=None):
    """
    Save location settings to settings.json.
    Writes both user_city/user_district (canonical) and city/district (legacy)
    so all modules (brain.py etc.) always read consistent values.
    """
    settings = settings_manager.load_settings()
    clean_city = city.strip() if city else ""
    clean_district = district.strip() if district else ""
    settings["user_city"] = clean_city
    settings["user_district"] = clean_district
    # Keep legacy keys in sync for brain.py compatibility
    settings["city"] = clean_city
    settings["district"] = clean_district
    if latitude is not None:
        settings["user_latitude"] = float(latitude)
    if longitude is not None:
        settings["user_longitude"] = float(longitude)
    settings_manager.save_settings(settings)
    print(f"[LocationManager] Location saved: {clean_city} {clean_district} (Lat: {latitude}, Lon: {longitude})")
    return get_location()

ENG_TO_ZH_CITIES = {
    "taipei city": "台北市",
    "taipei": "台北市",
    "new taipei city": "新北市",
    "new taipei": "新北市",
    "taoyuan city": "桃園市",
    "taoyuan": "桃園市",
    "taichung city": "台中市",
    "taichung": "台中市",
    "tainan city": "台南市",
    "tainan": "台南市",
    "kaohsiung city": "高雄市",
    "kaohsiung": "高雄市",
    "hsinchu city": "新竹市",
    "hsinchu": "新竹市",
    "hsinchu county": "新竹縣",
    "miaoli county": "苗栗縣",
    "miaoli": "苗栗縣",
    "changhua county": "彰化縣",
    "changhua": "彰化縣",
    "nantou county": "南投縣",
    "nantou": "南投縣",
    "yunlin county": "雲林縣",
    "yunlin": "雲林縣",
    "chiayi city": "嘉義市",
    "chiayi county": "嘉義縣",
    "chiayi": "嘉義市",
    "pingtung county": "屏東縣",
    "pingtung": "屏東縣",
    "yilan county": "宜蘭縣",
    "yilan": "宜蘭縣",
    "hualien county": "花蓮縣",
    "hualien": "花蓮縣",
    "taitung county": "台東縣",
    "taitung": "台東縣",
    "penghu county": "澎湖縣",
    "penghu": "澎湖縣",
    "kinmen county": "金門縣",
    "kinmen": "金門縣",
    "lienchiang county": "連江縣",
    "matsu": "連江縣",
    "keelung city": "基隆市",
    "keelung": "基隆市"
}

def auto_detect_ip():
    """
    Detect approximate location using ip-api.com.
    """
    print("[LocationManager] Attempting IP-based geolocation...")
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/?lang=zh-TW",
            headers={"User-Agent": "MimoAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "success":
                city = data.get("city", "")
                region_name = data.get("regionName", "")
                lat = data.get("lat", None)
                lon = data.get("lon", None)
                
                # In Taiwan, ip-api regionName often is 'Taipei City' or 'New Taipei City'
                resolved_city = region_name if region_name else city
                
                # Map English city name to Traditional Chinese if matches
                mapped_city = ENG_TO_ZH_CITIES.get(resolved_city.lower())
                if mapped_city:
                    resolved_city = mapped_city
                
                print(f"[LocationManager] IP Geolocation Success: {resolved_city} (Lat: {lat}, Lon: {lon})")
                return {
                    "city": resolved_city,
                    "district": "",  # IP geolocation rarely gives accurate district
                    "latitude": lat,
                    "longitude": lon
                }
    except Exception as e:
        print(f"[LocationManager] IP Geolocation failed: {e}")
    return None

def reverse_geocode(lat, lon):
    """
    Perform reverse geocoding via BigDataCloud API with OSM Nominatim fallback.
    """
    print(f"[LocationManager] Reverse geocoding Lat: {lat}, Lon: {lon}...")
    
    # 1. Primary: BigDataCloud reverse geocode client (very fast, free, no auth)
    try:
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=zh"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            city = data.get("principalSubdivision") or data.get("city") or ""
            district = data.get("locality") or ""
            
            # Clean up
            city = city.strip()
            district = district.strip()
            
            if city:
                print(f"[LocationManager] BigDataCloud Success: {city} {district}")
                return city, district
    except Exception as e:
        print(f"[LocationManager] BigDataCloud API failed, trying Nominatim fallback: {e}")

    # 2. Fallback: OSM Nominatim API
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=14&addressdetails=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            address = data.get("address", {})
            
            # Extract city / county
            city = address.get("city") or address.get("county") or address.get("state") or ""
            # Extract district / suburb / town
            district = address.get("suburb") or address.get("town") or address.get("village") or address.get("city_district") or address.get("district") or ""
            
            # Clean up names (remove redundant parts if any)
            city = city.strip()
            district = district.strip()
            
            print(f"[LocationManager] Nominatim Fallback Success: {city} {district}")
            return city, district
    except Exception as e:
        print(f"[LocationManager] Nominatim Fallback failed: {e}")
        
    return "", ""
