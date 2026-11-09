
from django.urls import path
from . import views

urlpatterns = [
    # Home Page
    path('', views.home, name='home'),

    # Product Details
    path('product/<int:id>/', views.product_detail, name='product_detail'),

    # Shopping Cart
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),

    path(
        'cart/update/<int:variant_id>/<str:action>/',
        views.update_cart_quantity,
        name='update_cart_quantity'
    ),

    path(
        'cart/remove/<int:variant_id>/',
        views.remove_from_cart,
        name='remove_from_cart'
    ),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),

    # Order Success
    path(
        'order-success/<int:order_id>/',
        views.order_success,
        name='order_success'
    ),

    # Customer Order Tracking
    path(
        'track-order/',
        views.order_tracking,
        name='order_tracking'
    ),

    # Customer Signup
    path(
        'signup/',
        views.signup,
        name='signup'
    ),

    # Customer Login
    path(
        'login/',
        views.customer_login,
        name='customer_login'
    ),

    # Customer Logout
    path(
        'logout/',
        views.customer_logout,
        name='customer_logout'
    ),
]
