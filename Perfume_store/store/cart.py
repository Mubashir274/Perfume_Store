class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')

        if not cart:
            cart = self.session['cart'] = {}

        self.cart = cart

    def add(self, variant, quantity=1):
        variant_id = str(variant.id)

        if variant_id not in self.cart:
            self.cart[variant_id] = {
                'quantity': 0,
                'price': str(variant.price),
            }

        self.cart[variant_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session['cart'] = self.cart
        self.session.modified = True

    def remove(self, variant):
        variant_id = str(variant.id)

        if variant_id in self.cart:
            del self.cart[variant_id]
            self.save()

    def clear(self):
        self.session['cart'] = {}
        self.session.modified = True