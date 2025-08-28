
from django.urls import path
from .views import (
    CategoryListView,
    ProductListView,
    ProductDetailView,
    ProductReviewListCreateView,
    ProductFiltersView,
    TagListView,
    BannersView,
    LimitedProductsView,
    PopularProductsView,
    ProductDetailByIdView,
)

urlpatterns = [
    # базовые
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/filters/', ProductFiltersView.as_view(), name='product-filters'),

    path('products/limited/', LimitedProductsView.as_view(), name='product-limited'),
    path('products/popular/', PopularProductsView.as_view(), name='product-popular'),
    path('banners/', BannersView.as_view(), name='banners'),

    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:slug>/reviews/', ProductReviewListCreateView.as_view(), name='product-reviews'),
    path('product/<int:pk>/', ProductDetailByIdView.as_view(), name='product-detail-by-id'),  # /api/product/2
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),         # /api/products/macbook-air

    path('tags/', TagListView.as_view(), name='tag-list'),


    path('catalog/', ProductListView.as_view(), name='catalog'),                 # /api/catalog -> список товаров
    path('catalog/filters/', ProductFiltersView.as_view(), name='catalog-filters'),
]