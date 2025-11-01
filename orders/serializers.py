from rest_framework import serializers
from catalog.models import Product, ProductImage
from .models import CartItem, Order, OrderItem


# ============================================
#  1. PRODUCT IMAGES SERIALIZER
# ============================================
class ProductImageSerializer(serializers.ModelSerializer):
    """Represents product images with src and alt fields."""
    class Meta:
        model = ProductImage
        fields = ['src', 'alt']


# ============================================
#  2. MAIN PRODUCT SERIALIZER
# ============================================
class ProductSerializer(serializers.ModelSerializer):
    """Main product serializer with image list."""
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'price', 'images']

    def get_images(self, obj):
        """Safely returns a list of product images or an empty list."""
        qs = getattr(obj, 'images', None)
        if qs is None:
            return []
        try:
            return ProductImageSerializer(qs.all(), many=True).data
        except Exception:
            return []


# ============================================
#  3. CART SERIALIZERS
# ============================================
class CartProductSerializer(ProductSerializer):
    """Uses the same fields as ProductSerializer"""
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields


class CartItemSerializer(serializers.ModelSerializer):
    """Represents a single product item inside the cart."""
    product = CartProductSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'qty', 'price_at_add', 'total', 'product']

    def get_total(self, obj):
        """Returns the total price for this cart item."""
        return float(obj.qty * obj.price_at_add)


class CartSerializer(serializers.Serializer):
    """Represents the entire cart with summary fields."""
    items = CartItemSerializer(many=True)
    total_qty = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)


# ============================================
#  4. ORDER SERIALIZERS
# ============================================
class OrderItemSerializer(serializers.ModelSerializer):
    """Represents a single item in an order."""
    product = ProductSerializer(read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'qty', 'price_at_order', 'amount']

    def get_amount(self, obj):
        """Calculates the total amount for a specific items."""
        return float(obj.qty * obj.price_at_order)


class OrderDetailSerializer(serializers.ModelSerializer):
    """Represent detailed information about a specific arder."""
    items = OrderItemSerializer(many=True, read_only=True)
    products = serializers.SerializerMethodField()
    totalCost = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'full_name', 'phone', 'email', 'address', 'comment',
            'status', 'totalCost', 'created_at', 'items', 'products'
        ]

    def get_totalCost(self, obj):
        """Represent the order total as a float value."""
        try:
            return float(obj.total_amount or 0)
        except (TypeError, ValueError):
            return 0.0

    def get_products(self, obj):
        """Returns a detailed product list for this order."""
        products_data = []
        for item in obj.items.all():
            product = item.product
            images = ProductImageSerializer(
                getattr(product, "images", []).all() if hasattr(product, "images") else [],
                many=True
            ).data

            products_data.append({
                "id": product.id,
                "title": product.title,
                "slug": product.slug,
                "price": float(item.price_at_order),
                "qty": item.qty,
                "images": images,
            })
        return products_data


class OrderCreateSerializer(serializers.ModelSerializer):
    """Used when creating a new order."""
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'email', 'address', 'comment']


class OrderListSerializer(serializers.ModelSerializer):
    """Represents short order info for the profile page."""
    class Meta:
        model = Order
        fields = ['id', 'status', 'total_amount', 'created_at']
