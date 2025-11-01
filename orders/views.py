
# ==============================
# views.py — Final version for Swagger
# ==============================

import json
from django.db.models import Sum, F
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from .models import CartItem, Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
)


# ==============================
# Helper function for the cart
# ==============================
def get_cart_qs(request):
    """
    Returns the cart QuerySet for the current user or session.
    """
    if request.user.is_authenticated:
        return (
            CartItem.objects
            .select_related('product', 'user')
            .filter(user=request.user)
            .order_by('-update_at')
        )

    if not request.session.session_key:
        request.session.save()
    sk = request.session.session_key

    return (
        CartItem.objects
        .select_related('product')
        .filter(session_key=sk)
        .order_by('-update_at')
    )


# ==============================
# /api/basket — main cart
# ==============================
class BasketView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Returns all items currently in the basket.
        """
        items = []
        for ci in get_cart_qs(request):
            p = ci.product

            # Collect images safely
            images = []
            try:
                for img in p.images.all():
                    src = getattr(img, "src", "")
                    if hasattr(src, "url"):
                        src = src.url
                    alt = getattr(img, "alt", p.title)
                    images.append({"src": src, "alt": alt})
            except Exception:
                    images = []

            # Safe price and count conversion
            price = getattr(p, "price", 0)
            try:
                price = float(price)
            except Exception:
                price = 0.0

            count = getattr(ci, "qty", 1)
            try:
                count = int(count)
            except Exception:
                count = 1

            items.append({
                "id": int(p.id),
                "category": getattr(p.category, "id", None),
                "price": price,
                "count": count,
                "title": getattr(p, "title", ""),
                "images": images,  # ✅ обязательно есть, даже если пустой
            })

        return Response(items, status=200)

    # POST /api/basket
    def post(self, request):
        """
        Adds a  product to the basket.
        Expected data: {"id": product_id, "count": quantity}
        """
        payload = request.data or {}
        pid = payload.get("id")
        cnt = payload.get("count", 1)

        try:
            from catalog.models import Product
            product = Product.objects.get(id=pid)
        except Exception:
            return Response({"detail": "Product not found"}, status=404)

        try:
            cnt = int(cnt)
        except Exception:
            cnt = 1
        if cnt < 1:
            cnt = 1

        from orders.models import CartItem  # путь по твоему проекту
        defaults = {"price_at_add": getattr(product, "price", 0)}

        if request.user.is_authenticated:
            obj, created = CartItem.objects.get_or_create(
                user=request.user, product=product, defaults=defaults
            )
        else:
            if not request.session.session_key:
                request.session.save()
            sk = request.session.session_key
            obj, created = CartItem.objects.get_or_create(
                session_key=sk, product=product, defaults=defaults
            )

        obj.qty = (obj.qty + cnt) if not created else cnt
        obj.save()

        return self.get(request)

    def delete(self, request):
        """
        Removes or decreases an item from the basket.
        Expected data: {"id": product_id, "count": quantity_to_remove}
        """
        payload = request.data or {}
        pid = payload.get("id")
        dec = payload.get("count", 1)

        try:
            dec = int(dec)
        except Exception:
            dec = 1
        if dec < 1:
            dec = 1

        qs = get_cart_qs(request).filter(product_id=pid)
        if not qs.exists():
            return Response({"detail": "Item not found"}, status=404)

        item = qs.first()
        new_qty = int(getattr(item, "qty", 1)) - dec
        if new_qty > 0:
            item.qty = new_qty
            item.save()
        else:
            item.delete()

        return self.get(request)

# ==============================
# /api/checkout — order creation
# ==============================
class CheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Creates an order based on the current basket.
        """
        qs = get_cart_qs(request)
        # for item in qs:
        #     print(f"Product: {item.product}, Qty: {item.qty}, Price: {item.price_at_add}")
        # print("DEBUG CART:", qs)

        if not qs.exists():
            return Response({'detail': 'Your basket is empty'}, status=400)

        agg = qs.aggregate(total=Sum(F('qty') * F('price_at_add')))
        total_amount = agg['total'] or 0

        ser = OrderCreateSerializer(data={})
        ser.is_valid(raise_exception=False)

        payload = {'total_amount': total_amount}

        if request.user.is_authenticated:
            order = Order.objects.create(user=request.user, **payload)
        else:
            order = Order.objects.create(session_key=request.session.session_key, **payload)

        items = [
            OrderItem(
                order=order,
                product=ci.product,
                qty=ci.qty,
                price_at_order=ci.price_at_add
            )
            for ci in qs
        ]
        OrderItem.objects.bulk_create(items)

        qs.delete()

        return Response({'orderId': order.id}, status=status.HTTP_201_CREATED)


# ==============================
# /api/orders — orders list
# ==============================
class MyOrdersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Returns all orders for the current user or session
        """
        if request.user.is_authenticated:
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
        else:
            if not request.session.session_key:
                request.session.save()
            sk = request.session.session_key
            orders = Order.objects.filter(session_key=sk).order_by('-created_at')

        return Response(OrderDetailSerializer(orders, many=True).data, status=200)

    def post(self, request, *args, **kwargs):
        checkout_view = CheckoutView()
        return checkout_view.post(request)


# ==============================
# /api/orders/{id} — order details
# ==============================
class OrderDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        """
        Returns details of a specific order.
        """
        qs = Order.objects.all()
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        else:
            if not request.session.session_key:
                request.session.save()
            qs = qs.filter(session_key=request.session.session_key)

        try:
            order = qs.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found'}, status=404)

        return Response(OrderDetailSerializer(order).data, status=200)

    def post(self, request, pk):
        """
        Marks the order as paid and returns redirect URL.
        """
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'detail': 'Заказ не найден'}, status=404)

        order.status = 'paid'
        order.save(update_fields=['status'])
        return Response({
            'detail': 'Заказ успешно оплачен',
            'redirect_url': '/history-order/'
        }, status=200)