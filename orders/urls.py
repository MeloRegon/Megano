from django.urls import path
from .views import BasketView, MyOrdersView, OrderDetailView, CheckoutView

urlpatterns = [
    path('basket', BasketView.as_view(), name='basket'),

    # orders
    path('orders', MyOrdersView.as_view(), name='order-list'),
    path('orders/<int:pk>', OrderDetailView.as_view(), name='order-detail'),
    path('orders/checkout', CheckoutView.as_view(), name='order-checkout'),
    path('order/<int:pk>', OrderDetailView.as_view(), name='order-detail-legacy'),
]