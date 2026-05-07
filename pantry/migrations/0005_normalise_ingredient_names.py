"""
Manual migration to capitalise the first letter of every Ingredient name.

If a capitalised variant already exists (e.g. both "milk" and "Milk" are
stored), all StockItems that reference the lower-cased record are re-pointed
to the capitalised record, and the duplicate is then deleted.
"""

from django.db import migrations


def normalise_ingredient_names(apps, schema_editor):
    Ingredient = apps.get_model("pantry", "Ingredient")
    StockItem = apps.get_model("pantry", "StockItem")

    for ingredient in list(Ingredient.objects.all()):
        capitalised = ingredient.name.strip().capitalize()
        if capitalised == ingredient.name:
            continue

        try:
            existing = Ingredient.objects.get(name=capitalised)
            # Redirect all StockItems to the existing record, then remove the duplicate
            StockItem.objects.filter(ingredient=ingredient).update(ingredient=existing)
            ingredient.delete()
        except Ingredient.DoesNotExist:
            ingredient.name = capitalised
            ingredient.save()


class Migration(migrations.Migration):

    dependencies = [
        ("pantry", "0004_cachedrecipe"),
    ]

    operations = [
        migrations.RunPython(normalise_ingredient_names, reverse_code=migrations.RunPython.noop),
    ]
