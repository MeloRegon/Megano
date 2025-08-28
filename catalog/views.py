from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView , RetrieveAPIView, ListCreateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from django.db.models import Q, Prefetch, F, Min, Max, Count

from .models import Category, Product, FeatureValue, Review, Tag
from .serializers import CategorySerializer, ProductSerializer, ReviewSerializer, ProductFiltersSerializer, TagSerializer


class SmallPagePagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = (Category.objects
                .filter(is_active=True)
                .select_related('parent'))



class ProductListView(ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = SmallPagePagination

    def get_queryset(self):
        qs = (Product.objects
              .select_related('category', 'brand')
              .prefetch_related(
    'images',
            'feature_value',
            'feature_value__features',
            'reviews',
            'reviews__user',
        )
              .filter(category__is_active=True)
              .order_by('-created_at'))
        p = self.request.query_params  # короткий доступ

        if cat := p.get('category'):
            qs = qs.filter(category__slug=cat)

        if brand := p.get('brand'):
            qs = qs.filter(brand__name=brand)

        if q := p.get('q'):
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        if mp := p.get('min_price'):
            qs = qs.filter(price__gte=mp)

        if mxp := p.get('max_price'):
            qs = qs.filter(price__lte=mxp)

        if limited := p.get('limited'):
            if limited.lower() in ('true', '1'):
                qs = qs.filter(is_limited=True)
            elif limited.lower() in ('false', '0'):
                qs = qs.filter(is_limited=False)

        ordering = p.get('ordering')
        mapping = {
            '-created': '-created_at',
            'price': 'price',
            '-price': '-price',
            'popular': '-purchases_count',
        }
        if ordering in mapping:
            qs = qs.order_by(mapping[ordering])

        return qs


class ProductFiltersView(APIView):
    """
    Возвращает бренды (с количеством товаров) и min/max цену
    с учётом таких же query-параметров, как в списке:
    category, brand, q, min_price, max_price, limited, ordering
    """
    def get(self, request):
        p = request.query_params
        qs = (Product.objects
              .filter(category__is_active=True))

        if cat := p.get('category'):
            qs = qs.filter(category__slug=cat)
        if brand := p.get('brand'):
            qs = qs.filter(brand__name=brand)
        if q := p.get('q'):
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if mp := p.get('min_price'):
            qs = qs.filter(price__gte=mp)
        if mxp := p.get('max_price'):
            qs = qs.filter(price__lte=mxp)
        if limited := p.get('limited'):
            v = limited.lower()
            if v in ('true', '1'):
                qs = qs.filter(is_limited=True)
            elif v in ('false', '0'):
                qs = qs.filter(is_limited=False)

        agg = qs.aggregate(min_price=Min('price'), max_price=Max('price'))
        brands_qs = (qs
            .values('brand__name')
            .annotate(products_count=Count('id'))
            .order_by('brand__name'))

        data = {
            'brands': [{'name': b['brand__name'] or '', 'products_count': b['products_count']} for b in brands_qs],
            'min_price': agg['min_price'] or 0,
            'max_price': agg['max_price'] or 0,
        }
        return Response(ProductFiltersSerializer(data).data)


class ProductDetailView(RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        qs = (Product.objects
              .select_related('brand', 'category')
              .prefetch_related('images',
                                Prefetch('feature_value',
                                         queryset=FeatureValue.objects.select_related('features')
                                         ),
                                'feature_value__features',
                                Prefetch('reviews',
                                         queryset=Review.objects.select_related('user').order_by('-created_at')
                                         ),
                                'reviews__user')
              )
        return qs

class ReviewPagination(PageNumberPagination):
    page_size = 5   # сколько отзывов на страницу


class ProductReviewListCreateView(ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    pagination_class = ReviewPagination

    def get_queryset(self):
        slug = self.kwargs['slug']
        return (Review.objects
                .filter(product__slug=slug)
                .select_related('user')
                .order_by('-created_at'))

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['product'] = get_object_or_404(Product, slug=self.kwargs['slug'])
        return ctx

    def perform_create(self, serializer):
        # Создание только для авторизованных
        if not self.request.user.is_authenticated:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Требуется авторизация.')
        product = self.get_serializer_context()['product']
        serializer.save(product=product, user=self.request.user)


class TagListView(ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


from catalog.models import Category

class BannersView(APIView):
    """
    GET /api/banners/ – список баннеров для главной
    """
    def _banner(self, category_id, img_src, alt):
        slug = Category.objects.filter(pk=category_id, is_active=True) \
                               .values_list('slug', flat=True).first()
        return {
            'images': [{'src': img_src, 'alt': alt}],
            'category': category_id,     # можно оставить для информации
            'slug': slug,                # фронт может читать это поле
            'link': f'/catalog/{slug}/' if slug else '/catalog/'
        }

    def get(self, request):
        data = [
            self._banner(1, '/static/frontend/assets/img/content/home/banner-1.jpg', 'banner 1'),
            self._banner(2, '/static/frontend/assets/img/content/home/banner-2.jpg', 'banner 2'),
            self._banner(3, '/static/frontend/assets/img/content/home/banner-3.jpg', 'banner 3'),
        ]
        return Response(data)

class LimitedProductsView(ListAPIView):
    """
    GET /api/products/limited/ -> лимитированные товары (is_limited=True)
    """
    serializer_class = ProductSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects
            .select_related('category', 'brand')
            .prefetch_related('images', 'feature_value', 'feature_value__features', 'reviews', 'reviews__user')
            .filter(is_limited=True, category__is_active=True)
            .order_by('-created_at')[:8]   # возьмем до 8 штук для главной
        )


class PopularProductsView(ListAPIView):
    """
    GET /api/products/popular/ -> популярные товары (по purchases_count)
    """
    serializer_class = ProductSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects
            .select_related('category', 'brand')
            .prefetch_related('images', 'feature_value', 'feature_value__features', 'reviews', 'reviews__user')
            .filter(category__is_active=True)
            .order_by('-purchases_count', '-created_at')[:8]
        )


class ProductDetailByIdView(RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return (Product.objects
                .select_related('brand', 'category')
                .prefetch_related(
                    'images',
                    Prefetch('feature_value', queryset=FeatureValue.objects.select_related('features')),
                    Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at')),
                ))