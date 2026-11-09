
from decimal import Decimal
from urllib.parse import quote

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Product, ProductVariant, Order, OrderItem
from .cart import Cart


# WhatsApp Payment
WHATSAPP_NUMBER = "923302217274"


# HOME PAGE
def home(request):
    products = Product.objects.filter(
        is_available=True
    ).prefetch_related('variants')

    cart = Cart(request)

    cart_count = sum(
        item['quantity'] for item in cart.cart.values()
    )

    return render(request, 'store/home.html', {
        'products': products,
        'cart_count': cart_count
    })


# PRODUCT DETAILS
def product_detail(request, id):
    product = get_object_or_404(
        Product.objects.prefetch_related('variants'),
        id=id,
        is_available=True
    )

    return render(request, 'store/product_detail.html', {
        'product': product
    })


# ADD TO CART
def add_to_cart(request):
    is_ajax = request.headers.get(
        'X-Requested-With'
    ) == 'XMLHttpRequest'

    if request.method != 'POST':
        return redirect('home')

    variant_id = request.POST.get('variant_id')

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity.'
            }, status=400)
        return redirect('home')

    if not variant_id or quantity < 1 or quantity > 99:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Invalid product or quantity.'
            }, status=400)
        return redirect('home')

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        is_available=True,
        product__is_available=True
    )

    cart = Cart(request)

    current_quantity = cart.cart.get(
        str(variant.id), {}
    ).get('quantity', 0)

    if current_quantity + quantity > variant.stock:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Not enough stock available.'
            }, status=400)

        return redirect('product_detail', id=variant.product.id)

    cart.add(variant, quantity)

    if is_ajax:
        cart_count = sum(
            item['quantity'] for item in cart.cart.values()
        )

        return JsonResponse({
            'success': True,
            'cart_count': cart_count
        })

    return redirect('view_cart')


# VIEW CART
def view_cart(request):
    cart = Cart(request)
    items = []
    total = Decimal('0.00')

    for variant_id, item in list(cart.cart.items()):
        variant = get_object_or_404(
            ProductVariant,
            id=variant_id
        )

        subtotal = Decimal(str(item['price'])) * item['quantity']
        total += subtotal

        items.append({
            'variant': variant,
            'quantity': item['quantity'],
            'subtotal': subtotal
        })

    return render(request, 'store/cart.html', {
        'items': items,
        'total': total
    })


# UPDATE CART QUANTITY
def update_cart_quantity(request, variant_id, action):
    if request.method == 'POST':
        cart = Cart(request)
        variant_key = str(variant_id)

        if variant_key in cart.cart:
            variant = get_object_or_404(
                ProductVariant,
                id=variant_id
            )

            current_quantity = cart.cart[variant_key]['quantity']

            if action == 'increase':
                if current_quantity < variant.stock:
                    cart.cart[variant_key]['quantity'] += 1

            elif action == 'decrease':
                if current_quantity > 1:
                    cart.cart[variant_key]['quantity'] -= 1

            cart.save()

    return redirect('view_cart')


# REMOVE FROM CART
def remove_from_cart(request, variant_id):
    if request.method == 'POST':
        cart = Cart(request)
        cart.cart.pop(str(variant_id), None)
        cart.save()

    return redirect('view_cart')


# CHECKOUT
def checkout(request):
    cart = Cart(request)

    if not cart.cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')

    items = []
    total = Decimal('0.00')

    for variant_id, item in cart.cart.items():
        variant = get_object_or_404(
            ProductVariant,
            id=variant_id,
            is_available=True,
            product__is_available=True
        )

        quantity = item['quantity']

        if quantity < 1 or quantity > variant.stock:
            messages.error(
                request,
                f'Not enough stock for {variant.product.name}.'
            )
            return redirect('view_cart')

        price = variant.price
        subtotal = price * quantity
        total += subtotal

        items.append({
            'variant': variant,
            'quantity': quantity,
            'price': price,
            'subtotal': subtotal
        })

    if request.method == 'POST':
        customer_name = request.POST.get(
            'customer_name', ''
        ).strip()

        mobile = request.POST.get(
            'mobile', ''
        ).strip()

        address = request.POST.get(
            'address', ''
        ).strip()

        city = request.POST.get(
            'city', ''
        ).strip()

        payment_method = request.POST.get(
            'payment_method', 'COD'
        )

        if not all([customer_name, mobile, address, city]):
            messages.error(
                request,
                'Please fill in all customer details.'
            )

            return render(request, 'store/checkout.html', {
                'items': items,
                'total': total
            })

        if payment_method not in ['COD', 'WhatsApp']:
            messages.error(request, 'Invalid payment method.')
            return redirect('checkout')

        with transaction.atomic():

            for item in items:
                variant = ProductVariant.objects.select_for_update().get(
                    id=item['variant'].id
                )

                if (
                    not variant.is_available
                    or not variant.product.is_available
                    or variant.stock < item['quantity']
                ):
                    messages.error(
                        request,
                        f"Insufficient stock for {variant.product.name}."
                    )
                    return redirect('view_cart')

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                mobile=mobile,
                address=address,
                city=city,
                total_amount=total,
                payment_method=payment_method
            )

            for item in items:
                variant = ProductVariant.objects.select_for_update().get(
                    id=item['variant'].id
                )

                OrderItem.objects.create(
                    order=order,
                    product=variant.product,
                    size=variant.size,
                    quantity=item['quantity'],
                    price=item['price'],
                    subtotal=item['subtotal']
                )

                variant.stock -= item['quantity']
                variant.save(update_fields=['stock'])

            order_message = (
                f"New Order #{order.id}\n"
                f"Customer: {customer_name}\n"
                f"Mobile: {mobile}\n"
                f"Address: {address}\n"
                f"City: {city}\n\n"
                f"Products:\n"
            )

            for item in items:
                order_message += (
                    f"{item['variant'].product.name} "
                    f"({item['variant'].size}) x "
                    f"{item['quantity']} = "
                    f"Rs. {item['subtotal']}\n"
                )

            order_message += f"\nTotal: Rs. {total}"

            cart.clear()

        if payment_method == 'WhatsApp':
            whatsapp_url = (
                f"https://wa.me/{WHATSAPP_NUMBER}"
                f"?text={quote(order_message)}"
            )

            return redirect(whatsapp_url)

        messages.success(
            request,
            f'Your order #{order.id} has been placed successfully!'
        )

        return redirect('order_success', order_id=order.id)

    return render(request, 'store/checkout.html', {
        'items': items,
        'total': total
    })


# ORDER SUCCESS
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(request, 'store/order_success.html', {
        'order': order
    })


# CUSTOMER ORDER TRACKING
def order_tracking(request):
    order = None
    error = None

    if request.method == 'POST':
        order_id = request.POST.get('order_id', '').strip()
        mobile = request.POST.get('mobile', '').strip()

        if order_id and mobile:
            try:
                order = Order.objects.get(
                    id=order_id,
                    mobile=mobile
                )
            except (Order.DoesNotExist, ValueError):
                error = (
                    'Order not found. Please check your Order ID '
                    'and Mobile Number.'
                )
        else:
            error = 'Please enter Order ID and Mobile Number.'

    return render(request, 'store/order_tracking.html', {
        'order': order,
        'error': error
    })


# CUSTOMER SIGNUP
def signup(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not all([username, email, password, confirm_password]):
            messages.error(request, 'Please fill in all fields.')

        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')

        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already registered.')

        elif len(password) < 8:
            messages.error(
                request,
                'Password must be at least 8 characters.'
            )

        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            login(request, user)

            messages.success(
                request,
                'Your account has been created successfully!'
            )

            return redirect('home')

    return render(request, 'store/signup.html')


# CUSTOMER LOGIN
def customer_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            messages.success(
                request,
                'Login successful!'
            )

            return redirect('home')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(request, 'store/login.html')


# CUSTOMER LOGOUT
def customer_logout(request):
    if request.method == 'POST':
        logout(request)

        messages.success(
            request,
            'You have been logged out.'
        )

    return redirect('home')
