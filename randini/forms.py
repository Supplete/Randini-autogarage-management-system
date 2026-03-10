from django import forms
from .models import Booking, SparePart


class SparePartForm(forms.ModelForm):
    class Meta:
        model = SparePart
        fields = ['name', 'price', 'stock', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }



class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        # Specify ONLY the fields the customer should fill
        # Do NOT include 'status' or 'user' here
        fields = [
            'full_name', 'email', 'phone', 'location', 
            'preferred_time', 'vehicle_type', 'service_type', 'vehicle_image'
        ]
        widgets = {
            'preferred_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    # This MUST be indented inside the BookingForm class
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # This automatically adds Bootstrap styling to every field
            field.widget.attrs.update({'class': 'form-control'})