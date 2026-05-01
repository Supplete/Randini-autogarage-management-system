from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('randini', '0005_alter_booking_vehicle_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
