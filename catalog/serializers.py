from rest_framework import serializers
from .models import (Category,  ProductImage,
                     Features, FeatureValue,
                     Review, Product, Tag)


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source='parent_id', read_only=True)
    image = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'is_active', 'parent', 'image', 'subcategories']

    def get_image(self, obj):
        """
        Фронт ждёт объект {src, alt}. Даже если иконки нет — src=None.
        """
        url = None
        # есть ли у объекта поле icon и файл?
        icon = getattr(obj, 'icon', None)
        if icon:
            try:
                url = icon.url
                # если нужно абсолютный урл:
                req = self.context.get('request')
                if req is not None:
                    url = req.build_absolute_uri(url)
            except Exception:
                url = None
        return {'src': url, 'alt': obj.name}

    def get_subcategories(self, obj):
        """
        Возвращаем список активных дочерних категорий в формате:
        [{id, name, slug, image: {src, alt} | null}, ...]
        Если детей нет — []
        """
        children_mgr = getattr(obj, 'children', None) or getattr(obj, 'category_set', None)
        if not children_mgr:
            return []

        result = []
        for child in children_mgr.filter(is_active=True):
            if getattr(child, 'icon', None):
                url = child.icon.url
                req = self.context.get('request')
                if req is not None:
                    url = req.build_absolute_uri(url)
                image = {'src': url, 'alt': child.name}
            else:
                image = {'src': None, 'alt': None}

            result.append({
                'id': child.id,
                'name': child.name,
                'slug': child.slug,
                'image': image,
            })
        return result

class ProductImageSerializer(serializers.ModelSerializer):
    src = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['src', 'alt']

    def get_src(self, obj):
        # 1) пробуем field ImageField "image"
        url = None
        image_field = getattr(obj, 'image', None)
        if image_field:
            # если это ImageField/File — берём .url
            url = getattr(image_field, 'url', None)

        # 2) если нет — пробуем строковый путь "src"
        if not url:
            url = getattr(obj, 'src', None)

        if not url:
            return None

        req = self.context.get('request')
        return req.build_absolute_uri(url) if req else url


class FeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Features
        fields = ['name', 'category']


class FeaturesValueSerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(source='feature.name', read_only=True)
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = FeatureValue
        fields = ['product', 'features', 'value', 'feature_name', 'product_id']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ['product', 'user', 'rating', 'text', 'created_at', 'user_id']
        extra_kwargs = {
            'product': {'write_only': True}  # продукт мы проставим во view
        }

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Рейтинг должен быть от 1 до 5.')
        return value

    def validate(self, attrs):
        """
        Запрещаем оставлять второй отзыв на тот же товар одним и тем же пользователем.
        Продукт прокинем в контексте из view.
        """
        request = self.context.get('request')
        product = self.context.get('product')
        if request and request.method == 'POST':
            user = request.user
            if not user.is_authenticated:
                raise serializers.ValidationError('Требуется авторизация.')
            from .models import Review  # локальный импорт, чтобы избежать циклов
            if Review.objects.filter(product=product, user=user).exists():
                raise serializers.ValidationError('Вы уже оставляли отзыв на этот товар.')
        return attrs



class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source='brand.name', read_only=True)
    category = serializers.SlugField(source='category.slug', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    feature_values = FeaturesValueSerializer(many=True, read_only=True, source='feature_value')
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug',
                  'price', 'short_description',
                  'description', 'is_limited',
                  'purchases_count', 'created_at',
                  'brand', 'category', 'images',
                  'feature_values', 'tags']


class BrandOptionSerializer(serializers.Serializer):
    name = serializers.CharField()
    products_count = serializers.IntegerField()


class ProductFiltersSerializer(serializers.Serializer):
    brands = BrandOptionSerializer(many=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2)



class CategoryMiniSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "image")

    def get_image(self, obj):
        """
        Всегда возвращаем объект с ключами src/alt.
        Если у категории нет картинки — подставляем заглушку из статики,
        чтобы фронт не падал.
        """
        # если в модели Category есть ImageField/URL на картинку
        img = getattr(obj, "image", None)
        if img:
            try:
                return {"src": img.url, "alt": obj.name}
            except Exception:
                pass

        # безопасная заглушка (пусть даже файла нет — фронт не упадёт)
        return {"src": "/static/frontend/assets/img/placeholder.svg", "alt": obj.name}


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")