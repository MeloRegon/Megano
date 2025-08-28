from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Слаг", max_length=200, unique=True)
    parent = models.ForeignKey(
        'self', verbose_name='Родитель',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children'
    )
    icon = models.ImageField("Иконка", upload_to='catalog/category-icons/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField("Название", max_length=128, unique=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = "Бренд"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, verbose_name="Категория",
                                 on_delete=models.PROTECT, related_name='products'
                                 )
    brand = models.ForeignKey(Brand, verbose_name="Бренд",
                              null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='products'
                             )
    tags = models.ManyToManyField('Tag', related_name='products', blank=True)
    title = models.CharField("Название",max_length=128)
    slug = models.SlugField("Слаг", max_length=200, unique=True)
    short_description = models.CharField("Краткое описание", max_length=300, blank=True, default='')
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0)])
    is_limited = models.BooleanField(verbose_name='Limited edition', default=False)
    sort_index = models.PositiveIntegerField("Индекс сортировки", default=0)
    purchases_count = models.PositiveIntegerField("Кол-во покупок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Продукт"

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name="Товар", related_name='images', on_delete=models.CASCADE)
    src = models.ImageField("Картинка", upload_to="catalog/product-images/")
    alt = models.CharField("Описание", blank=True, default='')

    class Meta:
        verbose_name = 'Изображения Продукта'
        verbose_name_plural = "Изображения Продукта"

    def __str__(self):
        return self.alt


class Features(models.Model):
    name = models.CharField("Название", max_length=128)
    category = models.ForeignKey(Category, verbose_name="Категория",
                                 on_delete=models.CASCADE, related_name='features')

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"

    def __str__(self):
        return self.name


class FeatureValue(models.Model):
    product = models.ForeignKey(Product, verbose_name="Товар",
                                on_delete=models.CASCADE, related_name='feature_value')
    features = models.ForeignKey(Features, verbose_name="Характеристика",
                                 on_delete=models.CASCADE, related_name='values')
    value = models.CharField("Значение", max_length=128)

    class Meta:
        verbose_name = 'Значение характеристики'
        verbose_name_plural = "Значения характеристики"
        constraints = [
            models.UniqueConstraint(fields=['product', 'features'], name='uniq_product_feature')
        ]


class Review(models.Model):
    product = models.ForeignKey(Product, verbose_name="Товар",
                                on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, verbose_name="Пользователь",
                             on_delete=models.CASCADE, related_name='reviews')
    rating = models.SmallIntegerField("Оценка",
                                      validators=[MinValueValidator(1),
                                                  MaxValueValidator(5)])
    text = models.TextField("Текст")
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = "Отзывы"
        constraints = [
            models.UniqueConstraint(fields=['product', 'user'], name='uniq_review_per_user')
        ]

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)


    def __str__(self):
        return self.name