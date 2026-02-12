from __future__ import annotations

from django import forms

from .models import BreakSlot, FoodItem, PreOrder


class FoodItemChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} - {obj.stall_name} ({obj.location})"


class PreOrderForm(forms.Form):
    food_item = FoodItemChoiceField(queryset=FoodItem.objects.filter(is_active=True))
    slot = forms.ModelChoiceField(queryset=BreakSlot.objects.all())
    quantity = forms.ChoiceField(
        choices=[(str(i), str(i)) for i in range(1, 7)],
        initial="1",
    )


class CancelOrderForm(forms.Form):
    order_id = forms.IntegerField(min_value=1)
