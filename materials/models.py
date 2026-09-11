from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Material(models.Model):
    owner_user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='materials')
    name=models.CharField(max_length=200)
    E_MPa=models.DecimalField(max_digits=18,decimal_places=6,validators=[MinValueValidator(Decimal('0.000001'))])
    density_g_per_mm3=models.DecimalField(max_digits=18,decimal_places=9,validators=[MinValueValidator(Decimal('0'))],null=True,blank=True)
    tensile_strength_MPa=models.DecimalField(max_digits=18,decimal_places=6,null=True,blank=True)
    compressive_strength_MPa=models.DecimalField(max_digits=18,decimal_places=6,null=True,blank=True)
    source_type=models.CharField(max_length=64)
    note=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)


class Strip(models.Model):
    owner_user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='strips')
    material=models.ForeignKey(Material,on_delete=models.PROTECT,related_name='strips')
    name=models.CharField(max_length=200)
    width_mm=models.DecimalField(max_digits=18,decimal_places=6,validators=[MinValueValidator(Decimal('0.000001'))])
    thickness_mm=models.DecimalField(max_digits=18,decimal_places=6,validators=[MinValueValidator(Decimal('0.000001'))])
    note=models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.material_id and self.owner_user_id and self.material.owner_user_id!=self.owner_user_id:
            raise ValidationError({'material':'条材只能引用所属用户自己的材料。'})
