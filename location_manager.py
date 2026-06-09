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
    """
    settings = settings_manager.load_settings()
    settings["user_city"] = city.strip() if city else ""
    settings["user_district"] = district.strip() if district else ""
    if latitude is not None:
        settings["user_latitude"] = float(latitude)
    if longitude is not None:
        settings["user_longitude"] = float(longitude)
    settings_manager.save_settings(settings)
    print(f"[LocationManager] Location saved: {city} {district} (Lat: {latitude}, Lon: {longitude})")
    return get_location()

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
                # Let's clean it up to Chinese if needed, though lang=zh-TW usually returns Chinese already.
                resolved_city = region_name if region_name else city
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
