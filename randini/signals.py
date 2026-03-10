from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, SparePart
from django.contrib import messages

@receiver(post_save, sender=Order)
def reduce_inventory_on_completion(sender, instance, created, **kwargs):
    # We only act if the order status is changed to 'Completed'
    if instance.status == 'Completed':
        # Loop through the items in this order
        # Assuming you have an OrderItem model or a JSON field for items
        for item in instance.items.all(): 
            spare_part = item.spare_part
            if spare_part.stock_quantity >= item.quantity:
                spare_part.stock_quantity -= item.quantity
                spare_part.save()
            else:
                # This handles cases where someone buys more than what's left
                # before the staff can update the stock.
                pass