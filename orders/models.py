from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

from catalog.models import Product


class  CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'
        ordering = ('-update_at', )

    def get_total_price(self):
        return self.qty * self.price_at_add

    def __str__(self):
        return f"{self.product} x {self.qty}"


class OrderStatus(models.TextChoices):
    NEW = 'new', 'Новый'
    PROCESSING = 'processing', 'В Обработке'
    PAID = 'paid', 'Оплачен'
    SHIPPED = 'shipped', 'Отгружен'
    COMPLETED = 'completed', 'Завершён'
    CANCELED = 'canceled', 'Отменён'


class Order(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE,
        verbose_name='Пользователь',
        help_text='Если оформляет авторизованный пользователь'
    )
    session_key = models.CharField(
        max_length=40, db_index=True, blank=True, null=True,
        verbose_name='Ключ сессии',
        help_text='Если оформляет гость (без авторизации)'
    )

    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    phone = models.CharField(max_length=50, verbose_name='Телефон')
    email = models.EmailField(verbose_name='E-mail')
    address = models.TextField(verbose_name='Адрес доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')

    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2 ,
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='Сумма заказа'
    )


    status = models.CharField(
        max_length=20 ,
        choices=OrderStatus.choices,
        default=OrderStatus.NEW,
        db_index=True,
        verbose_name='Статус'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        ordering = ('-created_at', )
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


    def __str__(self):
        return f'Заказ #{self.id} - ({self.get_status_display()})'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='Товар'
    )
    qty = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)],
        verbose_name='Кол-во'
    )
    price_at_order = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена в заказе'
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='uniq_product_per_order'
            )
        ]

    def __str__(self):
        return f'{self.product} × {self.qty}'

    @property
    def amount(self):
        if self.price_at_order is None or self.qty in (None, 0):
            return None
        return self.qty * self.price_at_order

