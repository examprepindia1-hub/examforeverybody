from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('item', 'price_at_purchase')
    can_delete = False
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # 'id' is the database PK. 'created' is from TimeStampedModel.
    list_display = ('id', 'user', 'total_amount', 'status', 'created')
    list_filter = ('status', 'created')
    search_fields = ('id', 'user__email', 'transaction_id')
    readonly_fields = ('total_amount', 'transaction_id', 'payment_method')
    inlines = [OrderItemInline]