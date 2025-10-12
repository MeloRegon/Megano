from django.db.models import Sum, F
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from .models import CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderItemSerializer,
)


def get_cart_qs(request):
    if request.user.is_authenticated:
        return (CartItem.objects
                .select_related('product', 'user')
                .filter(user=request.user)
                .order_by('-update_at'))

    if not request.session.session_key:
        request.session.save()
    sk = request.session.session_key

    return (CartItem.objects
            .select_related('product')
            .filter(session_key=sk)
            .order_by('-update_at'))


class CartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = get_cart_qs(request)

        total_qty = qs.aggregate(total=Sum('qty'))['total'] or 0
        total_amount = qs.aggregate(total=Sum(F('qty') * F('price_at_add')))['total'] or 0

        # сериализуем позиции корзины
        items = CartItemSerializer(qs, many=True).data

        # отдадим все популярные варианты ключей, чтобы фронт «попал» в нужный
        payload = {
            "items": items,

            # количество
            "total_qty": int(total_qty),
            "totalQty": int(total_qty),
            "count": int(total_qty),

            # сумма
            "total_amount": float(total_amount),
            "totalAmount": float(total_amount),
            "total": float(total_amount),
            "amount": float(total_amount),
        }
        return Response(payload)


class AddToCartView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # принимаем и "product_id"/"qty", и "id"/"count" (как в swagger фронта)
        product_id = request.data.get('product_id') or request.data.get('id')
        qty_raw = request.data.get('qty', request.data.get('count', 1))

        try:
            qty = int(qty_raw)
        except (TypeError, ValueError):
            return Response({'detail': 'qty/count must be integer'}, status=400)

        if qty <= 0:
            return Response({'detail': 'qty must be >= 1'}, status=400)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=404)

        qs = get_cart_qs(request)

        defaults = {'price_at_add': product.price}
        if request.user.is_authenticated:
            item, created = CartItem.objects.get_or_create(
                user=request.user, product=product, defaults=defaults
            )
        else:
            sk = request.session.session_key  # гарантирован в get_cart_qs
            item, created = CartItem.objects.get_or_create(
                session_key=sk, product=product, defaults=defaults
            )

        item.qty = (item.qty + qty) if not created else qty
        item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class UpdateCartItemView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, pk):
        qs = get_cart_qs(request)
        try:
            item = qs.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=404)

        qty = int(request.data.get('qty', item.qty))
        if qty <= 0:
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        item.qty = qty
        item.save()
        return Response(CartItemSerializer(item).data)


class RemoveCartItemView(APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, pk):
        qs = get_cart_qs(request)
        deleted, _ = qs.filter(pk=pk).delete()
        if not deleted:
            return Response({'detail': 'Item not found'}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClearCartView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        qs = get_cart_qs(request)
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 1) Корзина
        qs = get_cart_qs(request)
        if not qs.exists():
            return Response({'detail': 'Корзина пуста'}, status=400)

        # 2) Данные от пользователя
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # 3) Итого по корзине
        agg = qs.aggregate(total=Sum(F('qty') * F('price_at_add')))
        total_amount = agg['total'] or 0

        # 4) Создаём заказ
        payload = ser.validated_data | {'total_amount': total_amount}
        if request.user.is_authenticated:
            order = Order.objects.create(user=request.user, **payload)
        else:
            # session_key у нас уже гарантирован в get_cart_qs
            order = Order.objects.create(session_key=request.session.session_key, **payload)

        # 5) Переносим строки корзины в позиции заказа
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

        # 6) Чистим корзину
        qs.delete()

        # 7) Ответ
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

# Список моих заказов
class MyOrdersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
        else:
            # гарантируем ключ сессии (как и в корзине)
            if not request.session.session_key:
                request.session.save()
            sk = request.session.session_key
            orders = Order.objects.filter(session_key=sk).order_by('-created_at')

        data = OrderDetailSerializer(orders, many=True).data
        return Response(data)

# Детальная карточка заказа
class OrderDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        qs = Order.objects.all()

        # отдаём только «свои» заказы
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

        return Response(OrderDetailSerializer(order).data)


# orders/views.py
from django.db.models import Sum, F
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from .models import CartItem

def get_cart_qs(request):
    if request.user.is_authenticated:
        return (CartItem.objects
                .select_related('product', 'user')
                .filter(user=request.user)
                .order_by('-update_at'))
    if not request.session.session_key:
        request.session.save()
    sk = request.session.session_key
    return (CartItem.objects
            .select_related('product')
            .filter(session_key=sk)
            .order_by('-update_at'))

class BasketView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = get_cart_qs(request)

        items = []
        for ci in qs:
            p = ci.product
            # соберём картинки в формате swagger: [{src, alt}]
            imgs = []
            for img in getattr(p, 'images', []).all() if hasattr(p, 'images') else []:
                # предполагаю поля image.url и alt (подправь, если у тебя иначе)
                src = getattr(img, 'image', None)
                src = src.url if src and hasattr(src, 'url') else ''
                alt = getattr(img, 'alt', p.title)
                imgs.append({'src': src, 'alt': alt})

            items.append({
                # минимальный набор, который фронту точно нужен:
                'id': int(p.id),
                'price': float(getattr(ci, 'price_at_add', p.price)),
                'count': int(ci.qty),

                # полезные поля (фронт их терпит, в swagger они есть):
                'title': getattr(p, 'title', ''),
                'images': imgs,
            })

        return Response(items)

    def post(self, request):
        # принимает и {product_id, qty}, и {id, count} – как в swagger
        product_id = request.data.get('product_id') or request.data.get('id')
        qty_raw = request.data.get('qty', request.data.get('count', 1))

        try:
            qty = int(qty_raw)
        except (TypeError, ValueError):
            return Response({'detail': 'qty/count must be integer'}, status=400)
        if qty <= 0:
            return Response({'detail': 'qty must be >= 1'}, status=400)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=404)

        defaults = {'price_at_add': product.price}
        if request.user.is_authenticated:
            item, created = CartItem.objects.get_or_create(
                user=request.user, product=product, defaults=defaults
            )
        else:
            if not request.session.session_key:
                request.session.save()
            sk = request.session.session_key
            item, created = CartItem.objects.get_or_create(
                session_key=sk, product=product, defaults=defaults
            )

        item.qty = (item.qty + qty) if not created else qty
        item.save()

        # отвечаем кратко – фронт всё равно делает потом GET /basket
        return Response({'id': item.id}, status=status.HTTP_201_CREATED)