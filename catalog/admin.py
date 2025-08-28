from django.contrib import admin

from .models import Category, Brand, Product, ProductImage, Features, FeatureValue, Review, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    search_fields = ('name', 'slug')
    list_filter = ('is_active', )
    prepopulated_fields = {'slug': ('name',)}



@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class PhotoInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('src', 'alt')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('category', 'brand',
                    'title', 'short_description',
                    'description', 'price',
                    'is_limited', 'sort_index',
                    'purchases_count', 'created_at'
                    )
    search_fields = ('title', 'description')
    list_filter = ('category', 'brand', 'is_limited')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('purchases_count', 'created_at')
    ordering = ('-created_at',)
    inlines = [PhotoInline]


@admin.register(Features)
class FeaturesAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name', )
    list_filter = ('category',)


@admin.register(FeatureValue)
class FeatureValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'features', 'value')
    list_filter = ('features', 'product')
    search_fields = ('value',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'product')
    search_fields = ('text', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}