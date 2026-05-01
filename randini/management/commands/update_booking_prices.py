from django.core.management.base import BaseCommand
from django.db import transaction
from randini.models import Booking


class Command(BaseCommand):
    help = 'Update existing booking prices with fixed service pricing'

    def handle(self, *args, **options):
        """Update all bookings with price 0.00 to use fixed service pricing"""
        
        updated_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            bookings = Booking.objects.filter(price=0.00)
            
            for booking in bookings:
                try:
                    calculated_price = booking.calculate_service_price()
                    booking.price = calculated_price
                    booking.save()
                    updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated Booking #{booking.id}: {booking.get_service_type_display()} '
                            f'({booking.get_vehicle_type_display()}) - KSh {calculated_price}'
                        )
                    )
                    
                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to update Booking #{booking.id}: {str(e)}'
                        )
                    )

        # Also count bookings that already have prices
        existing_prices = Booking.objects.exclude(price=0.00).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nBooking price update complete!\n'
                f'Updated: {updated_count} bookings\n'
                f'Skipped: {skipped_count} bookings\n'
                f'Existing prices: {existing_prices} bookings\n'
                f'Total processed: {updated_count + skipped_count + existing_prices}'
            )
        )
