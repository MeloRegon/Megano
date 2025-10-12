from django.urls import path
from .views import BasketView, MyOrdersView, OrderDetailView, CheckoutView

urlpatterns = [
    # basket — один путь, три метода (GET/POST/DELETE реализуются во view)
    path('basket', BasketView.as_view(), name='basket'),

    # orders
    path('orders', MyOrdersView.as_view(), name='order-list'),
    path('orders/<int:pk>', OrderDetailView.as_view(), name='order-detail'),

    # если фронт дергает POST /orders — повесь CheckoutView сюда:
    path('orders', CheckoutView.as_view(), name='order-create'),     # без слеша — чтобы /api/orders (POST)
    # а если фронт дергает /orders/checkout — оставь такой маршрут:
    path('orders/checkout', CheckoutView.as_view(), name='order-checkout'),
]