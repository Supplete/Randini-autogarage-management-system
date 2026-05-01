"""
Context processors for Randini Auto Garage.
Makes cart count available to all templates.
"""


def cart_count(request):
    """
    Adds cart item count to template context for all requests.
    This makes the cart count available in the header navbar.
    """
    cart = request.session.get('cart', {})
    count = sum(item.get('quantity', 0) for item in cart.values())
    return {'cart_count': count}
