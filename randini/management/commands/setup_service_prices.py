from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from randini.models import Service


class Command(BaseCommand):
    help = 'Setup fixed prices for garage services'

    def handle(self, *args, **options):
        """Create service pricing for all service types and vehicle types"""
        
        # Define service prices (in KES)
        service_prices = {
            'engine': {
                'sedan': Decimal('15000.00'),
                'suv': Decimal('18000.00'),
                'truck': Decimal('25000.00'),
                'van': Decimal('20000.00'),
                'other': Decimal('16000.00'),
            },
            'body': {
                'sedan': Decimal('25000.00'),
                'suv': Decimal('30000.00'),
                'truck': Decimal('35000.00'),
                'van': Decimal('28000.00'),
                'other': Decimal('27000.00'),
            },
            'painting': {
                'sedan': Decimal('20000.00'),
                'suv': Decimal('25000.00'),
                'truck': Decimal('30000.00'),
                'van': Decimal('22000.00'),
                'other': Decimal('21000.00'),
            },
            'oil': {
                'sedan': Decimal('3000.00'),
                'suv': Decimal('4000.00'),
                'truck': Decimal('5000.00'),
                'van': Decimal('3500.00'),
                'other': Decimal('3200.00'),
            },
            'diagnostic': {
                'sedan': Decimal('5000.00'),
                'suv': Decimal('6000.00'),
                'truck': Decimal('7000.00'),
                'van': Decimal('5500.00'),
                'other': Decimal('5200.00'),
            },
            'other': {
                'sedan': Decimal('10000.00'),
                'suv': Decimal('12000.00'),
                'truck': Decimal('15000.00'),
                'van': Decimal('11000.00'),
                'other': Decimal('10500.00'),
            },
        }
        
        # Service descriptions
        service_descriptions = {
            'engine': 'Complete engine diagnostics and repair including parts replacement',
            'body': 'Body work including dent removal, panel beating, and structural repairs',
            'painting': 'Full vehicle painting with premium paint and clear coat protection',
            'oil': 'Complete oil change service with oil filter replacement and fluid check',
            'diagnostic': 'Comprehensive vehicle diagnostic using modern scanning equipment',
            'other': 'Custom service as per customer requirements and vehicle condition',
        }

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for service_type, vehicle_prices in service_prices.items():
                for vehicle_type, price in vehicle_prices.items():
                    service, created = Service.objects.update_or_create(
                        service_type=service_type,
                        vehicle_type=vehicle_type,
                        defaults={
                            'base_price': price,
                            'description': service_descriptions.get(service_type, ''),
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created: {service.get_service_type_display()} - '
                                f'{service.get_vehicle_type_display()} - KSh {price}'
                            )
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'Updated: {service.get_service_type_display()} - '
                                f'{service.get_vehicle_type_display()} - KSh {price}'
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nService pricing setup complete!\n'
                f'Created: {created_count} new services\n'
                f'Updated: {updated_count} existing services\n'
                f'Total: {created_count + updated_count} service prices configured'
            )
        )
