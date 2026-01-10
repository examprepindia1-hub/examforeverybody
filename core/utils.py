import requests
from django.db.models import Sum
from mocktests.models import UserTestAttempt

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

def get_leaderboard_data(test_slug=None):
    """
    Returns a sorted list of dictionaries representing the leaderboard.
    Format: [{'user_id': 1, 'display_name': 'Name', 'total_score': 100, ...}, ...]
    """
    """
    Returns a sorted list of dictionaries representing the leaderboard.
    Format: [{'user_id': 1, 'display_name': 'Name', 'total_score': 100, ...}, ...]
    """
    
    # ---------------------------------------------------------
    # SCENARIO A: Test-Specific Leaderboard (Legacy Logic)
    # ---------------------------------------------------------
    if test_slug:
        # Base Query
        attempts = UserTestAttempt.objects.filter(
            status='SUBMITTED', 
            score__isnull=False,
            test__item__slug=test_slug
        ).values(
            'user__id', 
            'user__username', 
            'user__first_name', 
            'user__last_name', 
            'score', 
            'created'
        )
        
        # Logic: Latest Attempt Only
        user_latest = {}
        for attempt in attempts:
            u_id = attempt['user__id']
            created = attempt['created']
            
            if u_id not in user_latest or created > user_latest[u_id]['created']:
                 # Construct Name
                first = attempt['user__first_name'] or ''
                last = attempt['user__last_name'] or ''
                display_name = f"{first} {last}".strip() or attempt['user__username']
                
                user_latest[u_id] = {
                    'user_id': u_id,
                    'display_name': display_name,
                    'total_score': float(attempt['score']),
                    'tests_taken': 1, # Specific test context
                    'created': created
                }
        
        # Convert to list
        leaderboard_data = list(user_latest.values())
        leaderboard_data.sort(key=lambda x: x['total_score'], reverse=True)

    # ---------------------------------------------------------
    # SCENARIO B: Global Leaderboard (Optimized via Signals)
    # ---------------------------------------------------------
    else:
        # Query the Denormalized Table (O(1) Speed)
        from mocktests.models import UserRankMetric
        
        metrics = UserRankMetric.objects.select_related('user').order_by('-total_xp')[:50] # Top 50
        
        leaderboard_data = []
        for m in metrics:
            first = m.user.first_name or ''
            last = m.user.last_name or ''
            display_name = f"{first} {last}".strip() or m.user.username
            
            leaderboard_data.append({
                'user_id': m.user.id,
                'display_name': display_name,
                'total_score': m.total_xp,
                'tests_taken': m.tests_taken_count
            })

    # ---------------------------------------------------------
    # Shared: Enrich with Rank & Analytics
    # ---------------------------------------------------------
    total_users = len(leaderboard_data)
    import random 
    
    for index, entry in enumerate(leaderboard_data):
        entry['rank'] = index + 1
        
        # Percentile
        if total_users > 1:
            percentile = ((total_users - index) / total_users) * 100
        else:
            percentile = 100.0
        entry['percentile'] = round(percentile, 1)
        
        # Mock Data (Frontend Visuals)
        entry['streak'] = random.randint(3, 45) 
        entry['improvement'] = random.randint(5, 25)
        
    return leaderboard_data

def get_user_rank(user_id, test_slug=None):
    """
    Returns (rank, total_score) for a specific user.
    """
    data = get_leaderboard_data(test_slug)
    for index, entry in enumerate(data):
        if entry['user_id'] == user_id:
            return index + 1, entry['total_score']
    return None, 0