from core.utils import get_client_ip, get_country_from_ip

def currency_processor(request):
    # 1. Get IP and Current Session Currency
    if 'currency' in request.session:
        # STOP HERE. Do not call the API.
        # Just return the data we already saved.
        return {
            'CURRENCY_CODE': request.session['currency'],
            'CURRENCY_SYMBOL': request.session['currency_symbol']
        }
    ip = get_client_ip(request)
    current_currency = request.session.get('currency')
    
    # 2. Logic: If no currency is set, force detection
    if not current_currency:
        country_code = get_country_from_ip(ip)
        print(f"[DEBUG] Country detected: {country_code}") # Verify this prints US
        
        if country_code == 'IN':
            current_currency = 'INR'
            symbol = '₹'
        else:
            current_currency = 'USD'
            symbol = '$'
            
        # Save to session
        request.session['currency'] = current_currency
        request.session['currency_symbol'] = symbol
    else:
        # If session exists, just grab the symbol
        symbol = request.session.get('currency_symbol', '₹')

    # 3. RETURN DIRECT VALUES (This fixes the lag)
    return {
        'CURRENCY_CODE': current_currency,   # Pass the variable directly
        'CURRENCY_SYMBOL': symbol
    }