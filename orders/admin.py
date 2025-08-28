from django.contrib import admin

from .models import CartItem, Order, OrderItem

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    def amount(self, obj):
        return obj.qty * obj.price_at_add
    amount.short_description = "Total price"


    list_display = ('product', 'user',
                    'session_key', 'qty',
                    'created_at', 'update_at', 'amount')
    list_filter = ('user', 'session_key')
    list_select_related = ('user', 'product')
    search_fields = ('user__username', 'product__title', 'session_key')
    readonly_fields = ('price_at_add', 'created_at', 'update_at')
    ordering = ('-update_at',)
    list_per_page = 50


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product', 'qty', 'price_at_order', 'amount')
    readonly_fields = ('amount', )
    extra = 0
    autocomplete_fields = ('product', )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = ('id', 'full_name', 'phone',
                    'total_amount', 'status',
                    'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'email')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at', )
    autocomplete_fields = ('user', )
    inlines = (OrderItemInline, )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'qty', 'price_at_order', 'amount')
    readonly_fields = ('amount', )
    list_select_related = ('order', 'product')
    search_fields = ('order__id', 'product__title')
    list_filter = ('order__status', )
    ordering = ('-order__created_at', )
