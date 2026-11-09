
from django.contrib import admin
from .models import Product, ProductVariant, Order, OrderItem


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 2


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'size',
        'price',
        'stock',
        'is_available',
    )
    list_filter = ('size', 'is_available')
    search_fields = ('product__name',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False

    fields = (
        'product',
        'size',
        'quantity',
        'price',
        'subtotal',
    )

    readonly_fields = (
        'product',
        'size',
        'quantity',
        'price',
        'subtotal',
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'customer_name',
        'mobile',
        'city',
        'total_amount',
        'payment_method',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at',
    )

    search_fields = (
        'customer_name',
        'mobile',
        'city',
    )

    list_editable = ('status',)

    readonly_fields = ('created_at',)

    ordering = ('-created_at',)

    fieldsets = (
        ('Customer Information', {
            'fields': (
                'customer_name',
                'mobile',
                'address',
                'city',
            )
        }),

        ('Order Information', {
            'fields': (
                'total_amount',
                'payment_method',
                'status',
                'created_at',
            )
        }),
    )

    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'product',
        'size',
        'quantity',
        'price',
        'subtotal',
    )

    search_fields = (
        'order__customer_name',
        'product__name',
    )
