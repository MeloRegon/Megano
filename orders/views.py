

# ==============================
# views.py — финальная версия под Swagger
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
# Вспомогательная функция для корзины
# ==============================
def get_cart_qs(request):
    """
    Возвращает QuerySet корзины для текущего пользователя или сессии.
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
# /api/basket — основная корзина
# ==============================
class BasketView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        items = []
        for ci in get_cart_qs(request):
            p = ci.product

            # --- собираем изображения безопасно ---
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

            # --- безопасно приводим цену и количество ---
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
        # фронт шлёт {"id": 123, "count": 2}
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

        # вернуть обновлённую корзину
        return self.get(request)

    # DELETE /api/basket
    def delete(self, request):
        # фронт шлёт {"id": 123, "count": 1}
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

        # вернуть обновлённую корзину
        return self.get(request)

# ==============================
# /api/checkout — оформление заказа
# ==============================
class CheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Оформляет заказ из корзины.
        """
        qs = get_cart_qs(request)
        if not qs.exists():
            return Response({'detail': 'Корзина пуста'}, status=400)

        # Данные из формы (учитываем «кривой» JSON)
        if len(request.POST.keys()) == 1:
            try:
                only_key = next(iter(request.POST.keys()))
                payload = json.loads(only_key)
                request.data.update(payload)
            except Exception:
                pass

        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        agg = qs.aggregate(total=Sum(F('qty') * F('price_at_add')))
        total_amount = agg['total'] or 0

        payload = ser.validated_data | {'total_amount': total_amount}

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

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)


# ==============================
# /api/orders — список заказов
# ==============================
class MyOrdersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Возвращает список заказов текущего пользователя или сессии.
        """
        if request.user.is_authenticated:
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
        else:
            if not request.session.session_key:
                request.session.save()
            sk = request.session.session_key
            orders = Order.objects.filter(session_key=sk).order_by('-created_at')

        return Response(OrderDetailSerializer(orders, many=True).data, status=200)


# ==============================
# /api/orders/{id} — детали заказа
# ==============================
class OrderDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        """
        Возвращает детали конкретного заказа.
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
            return Response({'detail': 'Заказ не найден'}, status=404)

        return Response(OrderDetailSerializer(order).data, status=200)