
from django.contrib import admin
from .models import UserProfile, SparePart, Service, Booking, Order, OrderItem, ContactMessage

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone_number', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']

admin.site.register(SparePart)
admin.site.register(Service)
admin.site.register(Booking)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ContactMessage)
