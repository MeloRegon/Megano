from django.urls import path
from .views import (
    CategoryListView, ProductListView, ProductFiltersView,
    LimitedProductsView, PopularProductsView,
    ProductDetailByIdView, ProductReviewCreateView,
    TagListView, BannersView,
)

urlpatterns = [
    path("categories", CategoryListView.as_view(), name="category-list"),
    path("catalog", ProductListView.as_view(), name="product-list"),
    path("products/filters", ProductFiltersView.as_view(), name="product-filters"),
    path("products/limited", LimitedProductsView.as_view(), name="product-limited"),
    path("products/popular", PopularProductsView.as_view(), name="product-popular"),
    path("banners", BannersView.as_view(), name="banners"),


    path("product/<int:pk>/review", ProductReviewCreateView.as_view(), name="product-review"),

    path("product/<int:pk>", ProductDetailByIdView.as_view(), name="product-detail-by-id"),
    path("tags", TagListView.as_view(), name="tag-list"),
]