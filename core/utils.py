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
    # 1. Base Query
    attempts = UserTestAttempt.objects.filter(
        status='SUBMITTED', 
        score__isnull=False
    )
    
    if test_slug:
        attempts = attempts.filter(test__item__slug=test_slug)

    attempts = attempts.values(
        'user__id', 
        'user__username', 
        'user__first_name', 
        'user__last_name', 
        'test__item__title', 
        'test__item__id', 
        'test__item__slug',
        'score', 
        'created'
    )

    # 2. Process in Python (Most Recent Logic)
    # user_id -> { test_id -> {score, date} }
    user_latest_attempts = {}

    for attempt in attempts:
        u_id = attempt['user__id']
        t_id = attempt['test__item__id']
        t_slug = attempt['test__item__slug']
        t_title = attempt['test__item__title']
        score = float(attempt['score'])
        created = attempt['created']

        if u_id not in user_latest_attempts:
            # Construct Privacy-Friendly Name
            first = attempt['user__first_name']
            last = attempt['user__last_name']
            if first or last:
                 display_name = f"{first} {last}".strip()
            else:
                 display_name = attempt['user__username'] # Fallback
            
            user_latest_attempts[u_id] = {
                'display_name': display_name, 
                'tests': {}
            }

        # Logic: Update if this attempt is newer than what we have stored
        current_stored = user_latest_attempts[u_id]['tests'].get(t_id)
        
        if not current_stored or created > current_stored['created']:
            user_latest_attempts[u_id]['tests'][t_id] = {
                'score': score, 
                'created': created,
                'title': t_title,
                'slug': t_slug
            }

    # 3. Calculate Totals
    leaderboard_data = []
    for u_id, data in user_latest_attempts.items():
        total_score = sum(item['score'] for item in data['tests'].values())
        tests_taken = len(data['tests'])
        leaderboard_data.append({
            'user_id': u_id,
            'display_name': data['display_name'],
            'total_score': total_score,
            'tests_taken': tests_taken
        })

    # 4. Sort by Score Descending
    leaderboard_data.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 5. Enrich with Rank, Percentile, Streak (Mock), Improvement (Mock)
    total_users = len(leaderboard_data)
    import random # Imported here for mock logic, move to top if preferred or keep local
    
    for index, entry in enumerate(leaderboard_data):
        rank = index + 1
        entry['rank'] = rank
        
        # Percentile Calculation (Higher is better)
        # Formula: (Total - Rank) / Total * 100
        if total_users > 1:
            percentile = ((total_users - index) / total_users) * 100
        else:
            percentile = 100.0
        entry['percentile'] = round(percentile, 1)
        
        # MOCK DATA for Visuals (as per plan limitations)
        # In a real app, this would query historical daily activity
        entry['streak'] = random.randint(3, 45) 
        entry['improvement'] = random.randint(5, 25) # e.g. 12%
        
    
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