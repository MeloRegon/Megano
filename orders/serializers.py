from rest_framework import serializers
from catalog.models import Product, ProductImage
from .models import CartItem, Order, OrderItem


class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'price', 'slug']

class CartProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['src', 'alt']

# Короткий товар для карточки в корзине
class CartProductSerializer(serializers.ModelSerializer):
    images = CartProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'price', 'images']

# Позиция корзины
from rest_framework import serializers

class CartItemSerializer(serializers.ModelSerializer):
    price_at_add = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'qty', 'price_at_add', 'total', 'product')

    def get_total(self, obj):
        return float(obj.qty * obj.price_at_add)  # число, не строка

# Вся корзина целиком
class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    total_qty = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'qty', 'price_at_order', 'amount']

    def get_amount(self, obj):
        return obj.qty * obj.price_at_order


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'full_name', 'phone', 'email', 'address', 'comment',
            'status', 'total_amount', 'created_at', 'items'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'email', 'address', 'comment']


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'status', 'total_amount', 'created_at']

