from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def show_price(context, item):
    request = context.get('request')
    currency = request.session.get('currency', 'INR')
    
    # --- DEBUG PRINT ---
    # This will show up in your terminal every time you refresh
    # It tells you exactly why the decision was made
    price_usd = getattr(item, 'price_usd', 0)
    
    # -------------------

    if currency == 'USD':
        if price_usd and price_usd > 0:
            return f"${price_usd}"
        else:
            return f"₹{item.price}"

    return f"₹{item.price}"