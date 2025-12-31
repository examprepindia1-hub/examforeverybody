import requests

def get_country_from_ip(ip_address):
    # 1. Handle Localhost / Internal IPs
    if ip_address == '127.0.0.1' or ip_address.startswith('192.168') or ip_address.startswith('10.'):
        print(f"[DEBUG] Localhost IP detected ({ip_address}). Defaulting to India.")
        return 'IN'
        
    try:
        # 2. Use 'api.country.is' (Free & Supports HTTPS)
        # It returns simple JSON: {"ip": "...", "country": "US"}
        response = requests.get(f'https://api.country.is/{ip_address}', timeout=5)
        data = response.json()
        
        country = data.get('country', 'IN')
        
        print(f"[DEBUG] IP: {ip_address} | Detected Country: {country}")
        return country

    except Exception as e:
        print(f"[DEBUG] API Error: {e}")
        # If API fails, default to India so the site doesn't crash
        return 'IN'

def get_client_ip(request):
    """
    Retrieves the real IP, handling Ngrok and Proxy headers.
    """
    # 1. Check for the standard 'X-Forwarded-For' header (Used by Ngrok)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        # The header often looks like: "203.0.113.195, 127.0.0.1"
        # We want the FIRST IP (the original user), not the last one.
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Fallback to standard Remote Address (will be 127.0.0.1 on Ngrok)
        ip = request.META.get('REMOTE_ADDR')
        
    return ip