# catalog/serializers.py

from django.conf import settings
from urllib.parse import urljoin
from rest_framework import serializers

from .models import (
    Category, ProductImage, Features, FeatureValue,
    Review, Product, Tag
)

# --------------------------
# ВСПОМОГАТЕЛЬНЫЕ СЕРИАЛИЗАТОРЫ
# --------------------------

class ProductImageSerializer(serializers.ModelSerializer):
    """
    Возвращает объект с абсолютным URL:
    { "src": "http://127.0.0.1:8000/media/…", "alt": "…" }
    Работает как с ImageField, так и со строковым путём.
    """
    src = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["src", "alt"]

    def get_src(self, obj):
        url = None

        # 1) если в объекте есть поле image (ImageField/File)
        image_field = getattr(obj, "image", None)
        if image_field:
            try:
                url = image_field.url
            except Exception:
                url = None

        # 2) иначе берём поле src (в твоей модели это ImageField)
        if not url:
            raw = getattr(obj, "src", None)
            if raw is None:
                return None
            # raw может быть ImageFieldFile или строка
            try:
                url = raw.url  # если это файл
            except Exception:
                url = str(raw)  # если это строка

        # 3) делаем абсолютный URL при наличии request
        if not url:
            return None
        req = self.context.get("request")
        if req and url.startswith("/"):
            return req.build_absolute_uri(url)
        return url


class FeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Features
        fields = ["name", "category"]


class FeaturesValueSerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(source="features.name", read_only=True)
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = FeatureValue
        fields = ["product", "features", "value", "feature_name", "product_id"]


# Публичный формат отзыва (как в Swagger, read-only)
class ReviewPublicSerializer(serializers.Serializer):
    author = serializers.CharField()
    email = serializers.EmailField()
    text = serializers.CharField()
    rate = serializers.IntegerField()
    date = serializers.DateTimeField()


# Сериализатор для создания отзыва (POST /product/{id}/review)
class ReviewCreateSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ["product", "user", "rating", "text", "created_at", "user_id"]
        extra_kwargs = {"product": {"write_only": True}}

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        product = self.context.get("product")
        if request and request.method == "POST":
            user = request.user
            if not user.is_authenticated:
                raise serializers.ValidationError("Требуется авторизация.")
            if Review.objects.filter(product=product, user=user).exists():
                raise serializers.ValidationError("Вы уже оставляли отзыв на этот товар.")
        return attrs


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


# --------------------------
# КАТЕГОРИИ
# --------------------------

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source='parent_id', read_only=True)
    image = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'is_active', 'parent', 'image', 'subcategories',]


    def get_image(self, obj):
        pic = getattr(obj, 'icon', None) or getattr(obj, 'image', None)
        url = None
        if pic:
            try:
                url = pic.url
                req = self.context.get('request')
                if req:
                    url = req.build_absolute_uri(url)
            except Exception:
                url = None
        # ВСЕГДА возвращаем объект
        return {'src': url, 'alt': obj.name or ''}

    def get_subcategories(self, obj):
        mgr = getattr(obj, 'children', None) or getattr(obj, 'category_set', None)
        if not mgr:
            return []
        out = []
        for child in mgr.filter(is_active=True):
            pic = getattr(child, 'icon', None) or getattr(child, 'image', None)
            url = None
            if pic:
                try:
                    url = pic.url
                    req = self.context.get('request')
                    if req:
                        url = req.build_absolute_uri(url)
                except Exception:
                    url = None
            out.append({
                'id': child.id,
                'name': child.name,
                'slug': child.slug,
                'image': {'src': url, 'alt': child.name or ''},  # ВСЕГДА объект
            })
        return out

# --------------------------
# ТОВАРЫ ПО SWAGGER
# --------------------------

# Спецификация {name, value} для полной карточки
class SpecificationSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.CharField()


def _spec_from_feature_value(fv: FeatureValue):
    return {"name": getattr(fv.features, "name", ""), "value": fv.value}


def _review_to_public(r: Review):
    return {
        "author": getattr(r.user, "username", "Anonymous"),
        "email": getattr(r.user, "email", "") or "no-reply@mail.ru",
        "text": r.text,
        "rate": r.rating,
        "date": r.created_at,
    }


class ProductShortSerializer(serializers.ModelSerializer):
    """
    Короткая карточка для списков (Swagger: ProductShort):
    id, category (int), price, count, date, title, images[], tags[], rating
    """
    category = serializers.IntegerField(source="category_id", read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    # Swagger ждёт массив строк, поэтому даём имена тегов
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Product
        fields = [
            "id", "category", "price", "count", "date", "title",
            "images", "tags", "rating",
        ]


class ProductFullSerializer(ProductShortSerializer):
    description = serializers.CharField()
    fullDescription = serializers.CharField(source="full_description")
    freeDelivery = serializers.BooleanField(source="free_delivery")
    specifications = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta(ProductShortSerializer.Meta):
        fields = ProductShortSerializer.Meta.fields + [
            "description", "fullDescription", "freeDelivery",
            "specifications", "reviews",
        ]

    def get_specifications(self, obj):
        return [{"name": fv.features.name, "value": fv.value} for fv in obj.feature_value.all()]

    def get_reviews(self, obj):
        # обратная связь может называться reviews или review_set
        if hasattr(obj, "reviews"):
            qs = obj.reviews.all()
        else:
            qs = obj.review_set.all()
        qs = qs.select_related("user").order_by("-created_at")
        # используем публичный сериализатор для нужного формата
        return [
            {
                "author": (r.user.username if r.user_id else "Anonymous"),
                "email": (r.user.email if r.user_id and r.user.email else "no-reply@mail.ru"),
                "text": r.text,
                "rate": r.rating,
                "date": r.created_at,
            }
            for r in qs
        ]

