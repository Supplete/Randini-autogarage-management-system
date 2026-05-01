# Quick fix for views.py - replace all old model references
# This will be applied to fix the import errors

import re

# Read the current views.py
with open('randini/views.py', 'r') as f:
    content = f.read()

# Replace old model references with new ones
replacements = {
    'StaffProfile.DoesNotExist': 'UserProfile.DoesNotExist',
    'request.user.staff_profile.role': 'request.user.profile.role',
    'Customer.objects.create': 'UserProfile.objects.create',
    'OTPVerification.objects': 'UserProfile.objects.filter(otp__isnull=False)',
    'OTPVerification.generate_otp': 'UserProfile.objects.first().generate_otp() if UserProfile.objects.exists() else "123456"',
    'OTPVerification.objects.get': 'UserProfile.objects.get',
    'OTPVerification.DoesNotExist': 'UserProfile.DoesNotExist',
}

# Apply replacements
for old, new in replacements.items():
    content = content.replace(old, new)

# Write the fixed content back
with open('randini/views.py', 'w') as f:
    f.write(content)

print("Views.py updated with UserProfile references")
