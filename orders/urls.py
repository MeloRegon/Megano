from django.urls import path
from .views import (
    CartView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
    ClearCartView,
    CheckoutView,
    MyOrdersView,
    OrderDetailView,
    BasketView,
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:pk>/', UpdateCartItemView.as_view(), name='cart-item'),
    path('cart/items/<int:pk>/delete/', RemoveCartItemView.as_view(), name='cart-item-delete'),
    path('cart/clear/', ClearCartView.as_view(), name='cart-clear'),
    path('orders/checkout/', CheckoutView.as_view(), name='order-checkout'),
    path('orders/', MyOrdersView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),

    # basket endpoint: фронт может дергать и со слешем, и без
    path('basket',  BasketView.as_view(), name='basket-no-slash'),  # для POST без слеша
    path('basket/', BasketView.as_view(), name='basket'),           # для GET со слешем
]