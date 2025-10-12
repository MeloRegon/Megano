# catalog/views.py

from django.db.models import Q, Count, Min, Max, F, Prefetch
from django.db.models.functions import Coalesce
from django.templatetags.static import static

from rest_framework.response import Response
from rest_framework import permissions, generics
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView
from rest_framework.views import APIView

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

# --------- товары: список по Swagger (ProductShort) ---------
class ProductListView(ListAPIView):
    """
    GET /api/catalog/ — список товаров c фильтрами Swagger.
    """
    serializer_class = ProductShortSerializer
    permission_classes = [permissions.AllowAny]

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

        p = self.request.GET

        # фильтры (Swagger формулировка)
        cat = p.get("category")              # id категории (число)
        name = p.get("name")                 # строка поиска по названию
        min_price = p.get("minPrice")
        max_price = p.get("maxPrice")
        free_delivery = _parse_bool(p.get("freeDelivery"))
        available = _parse_bool(p.get("available"))

        if cat:
            qs = qs.filter(category_id=cat)

        if name:
            qs = qs.filter(Q(title__icontains=name))

        if min_price:
            qs = qs.filter(price__gte=min_price)

        if max_price:
            qs = qs.filter(price__lte=max_price)

        if free_delivery is True:
            qs = qs.filter(free_delivery=True)
        if available is True:
            qs = qs.filter(count__gt=0)

        # сортировка
        ordering = p.get("ordering")
        mapping = {
            "popularity": "-popularity",
            "price": "price",
            "-price": "-price",
            "reviews": "-reviews_count",
            "novelty": "-created_at",
        }
        if ordering in mapping:
            qs = qs.order_by(mapping[ordering], "-id")

        return qs


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
            img_path = static_imgs[i % len(static_imgs)]
            banners.append({
                "title": cat.name,
                "images": [{"src": static(img_path), "alt": cat.name}],
                # отдай сразу всё, чтобы фронт не падал
                "link": f"/catalog?category={cat.id}",  # на случай, если фронт ждёт готовый URL
                "category": cat.id,                     # на случай, если склеивает /catalog/<id>/
                "category_slug": getattr(cat, "slug", "") or "",  # на случай, если ждёт slug
            })

        return Response(banners)