# catalog/views.py

import json
from django.db.models import Q, Count, Min, Max, F, Prefetch
from django.db.models.functions import Coalesce
from django.templatetags.static import static
from urllib.parse import urlparse, parse_qs

from rest_framework.response import Response
from rest_framework import permissions, generics
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from math import ceil


from .models import Product, Category, FeatureValue, Review, Tag
from .serializers import (
    CategorySerializer,
    ProductShortSerializer,
    ProductFullSerializer,
    ReviewCreateSerializer,
    TagSerializer,
    ProductImageSerializer,   # для префетча не нужен, но импорт не мешает
)

# --------- helpers ---------
def _parse_bool(val):
    if val is None:
        return None
    return str(val).lower() in ("1", "true", "yes", "y", "on")


# --------- категории ---------
class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # фронт ждёт простой массив

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related('children')
            .order_by('id')
        )

class CatalogPagination(PageNumberPagination):
    page_size_query_param = "limit"  # фронт передаёт параметр limit
    page_query_param = "currentPage"  # фронт передаёт currentPage
    page_size = 20  # значение по умолчанию

class ProductListView(ListAPIView):
    """
    GET /api/catalog — список товаров с фильтрами и пагинацией по Swagger.
    """
    serializer_class = ProductShortSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CatalogPagination

    import json

    def get_queryset(self):
        qs = (
            Product.objects
            .select_related("category", "brand")
            .prefetch_related("images", "tags", "feature_value")
            .annotate(
                reviews_count=Count("reviews", distinct=True),
                popularity=Coalesce(F("purchases_count"), 0),
            )
        )

        params = self.request.GET.copy()
        # Поддержка поиска по названию товара
        search_name = (
                params.get('filter[name]') or
                params.get('filter') or
                params.get('name')
        )

        if search_name:
            print("SEARCH:", search_name)  # временно, чтобы убедиться
            qs = qs.filter(title__icontains=search_name.strip())

        # 🔹 Преобразуем filter[name], filter[minPrice] и т.д. в обычный словарь
        filter_data = params.get('filter', {})
        # поддержка поиска по названию ?filter=Asus
        if isinstance(filter_data, str):
            qs = qs.filter(title__icontains=filter_data)

        for key, value in params.items():
            if key.startswith("filter[") and key.endswith("]"):
                field = key[len("filter["):-1]
                filter_data[field] = value

        # 🔹 Объединяем в один словарь для удобства
        params.update(filter_data)

        cat = params.get("category")
        name = params.get("name")
        min_price = params.get("minPrice")
        max_price = params.get("maxPrice")
        free_delivery = _parse_bool(params.get("freeDelivery"))
        available = _parse_bool(params.get("available"))

        if cat:
            qs = qs.filter(category_id=cat)
        if name:
            qs = qs.filter(title__icontains=name)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if free_delivery:
            qs = qs.filter(free_delivery=True)
        if available:
            qs = qs.filter(count__gt=0)
            # поддержка поиска по полю title (?filter=MacBook)
            search_text = params.get("filter")
            if search_text:
                qs = qs.filter(title__icontains=search_text)

        # 🔹 Сортировка
        sort_field = params.get("sort", "date")
        sort_type = params.get("sortType", "dec")

        mapping = {
            "rating": "rating",
            "price": "price",
            "reviews": "reviews_count",
            "date": "created_at",
        }

        if sort_field in mapping:
            field = mapping[sort_field]
            if sort_type == "dec":
                field = f"-{field}"
            qs = qs.order_by(field, "-id")

        print("FILTER DATA:", filter_data)
        print("FINAL PARAMS:", params)
        print("RESULT COUNT:", qs.count())
        print("ALL PRODUCTS COUNT:", Product.objects.count())
        print("ACTIVE PRODUCTS COUNT:", Product.objects.filter(count__gt=0).count())

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            pagination = self.paginator
            return Response({
                "items": serializer.data,
                "currentPage": pagination.page.number,
                "lastPage": pagination.page.paginator.num_pages,
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({"items": serializer.data})


# --------- фильтры каталога (минимум бренды/цены) ---------
class ProductFiltersView(APIView):
    """
    GET /api/products/filters/ — бренды и мин/макс цены (для фронта).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        agg = Product.objects.aggregate(
            min_price=Min("price"),
            max_price=Max("price"),
        )
        # бренды с количеством товаров
        brands_qs = (
            Product.objects.values("brand__name")
            .annotate(products_count=Count("id"))
            .order_by("brand__name")
        )
        brands = [
            {"name": b["brand__name"] or "", "products_count": b["products_count"]}
            for b in brands_qs
        ]
        data = {"brands": brands, "min_price": agg["min_price"] or 0, "max_price": agg["max_price"] or 0}
        return Response(data)


# --------- популярные/лимитированные (ProductShort) ---------
class LimitedProductsView(ListAPIView):
    serializer_class = ProductShortSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_limited=True, category__is_active=True)
            .select_related("category", "brand")
            .prefetch_related("images", "tags")
            .order_by("-id")[:12]
        )


class PopularProductsView(ListAPIView):
    serializer_class = ProductShortSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects
            .filter(category__is_active=True)
            .select_related("category", "brand")
            .prefetch_related("images", "tags")
            .order_by("-purchases_count")[:12]
        )


# --------- теги ---------
class TagListView(ListAPIView):
    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


# --------- детальная карточка (ProductFull) ---------
class ProductDetailByIdView(RetrieveAPIView):
    serializer_class = ProductFullSerializer
    lookup_field = "pk"
    permission_classes =  [permissions.AllowAny]

    def get_queryset(self):
        reviews_qs = Review.objects.select_related("user").order_by("-created_at")

        return (
            Product.objects
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch("feature_value", queryset=FeatureValue.objects.select_related("features")),
                Prefetch("reviews", queryset=reviews_qs),   # на случай если нет related_name
                "tags",
            )
        )


# --------- отзывы: список+создание ---------
class ReviewPagination:  # если нужна пагинация — DRF PageNumberPagination можно подключить
    page_size = 5

class ProductReviewCreateView(generics.CreateAPIView):
    """
    POST /api/product/<id>/review/
    Создать отзыв к товару.
    Требует авторизацию (user берётся из request.user).
    """
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_product(self):
        return Product.objects.get(pk=self.kwargs["pk"])

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["product"] = self.get_product()   # для валидации «один отзыв на товар»
        return ctx

    def perform_create(self, serializer):
        product = self.get_product()
        serializer.save(product=product, user=self.request.user)


# --------- баннеры для главной ---------
class BannersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        static_imgs = [
            "frontend/assets/img/content/home/slider.png",
            "frontend/assets/img/content/home/bigGoods.png",
            "frontend/assets/img/content/home/videoca.png",
        ]

        categories = (
            Category.objects
            .filter(is_active=True, parent__isnull=True)
            .order_by("id")[:3]
        )

        banners = []
        for i, cat in enumerate(categories):
            # находим минимальную цену среди всех товаров в категории
            products = Product.objects.filter(category=cat)
            min_price = products.aggregate(Min("price"))["price__min"]

            img_path = static_imgs[i % len(static_imgs)]
            banners.append({
                "id": cat.id,
                "title": cat.name,
                "price": min_price or 0,
                "images": [{"src": static(img_path), "alt": cat.name}],
                "link": f"/catalog?category={cat.id}",
                "category": cat.id,
                "category_slug": getattr(cat, "slug", "") or "",
            })

        return Response(banners)