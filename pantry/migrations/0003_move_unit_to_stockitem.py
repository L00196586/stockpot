"""
Manual migration to move the `unit` field from Ingredient to StockItem.

- Adds `unit` field to StockItem (populated from the Ingredient's existing unit).
- Removes `unit` field from Ingredient.
"""

from django.db import migrations, models


def copy_units_from_ingredient(apps, schema_editor):
    """Copies Ingredient.unit into StockItem.unit before the field is removed."""
    StockItem = apps.get_model("pantry", "StockItem")
    for stock in StockItem.objects.select_related("ingredient").all():
        stock.unit = stock.ingredient.unit
        stock.save(update_fields=["unit"])


class Migration(migrations.Migration):

    dependencies = [
        ("pantry", "0002_savedrecipe"),
    ]

    operations = [
        # Unit field in StockItem as nullable so the data migration can run first
        migrations.AddField(
            model_name="stockitem",
            name="unit",
            field=models.CharField(
                blank=True,
                max_length=10,
                choices=[
                    ("g", "Grams"),
                    ("kg", "Kilograms"),
                    ("ml", "Millilitres"),
                    ("L", "Litres"),
                    ("pcs", "Pieces"),
                    ("tbsp", "Tablespoons"),
                    ("tsp", "Teaspoons"),
                    ("cup", "Cups"),
                ],
                default="",
            ),
        ),
        # Copy the unit value from each StockItem's Ingredient
        migrations.RunPython(copy_units_from_ingredient, migrations.RunPython.noop),
        # After migrating the values, the field can be made non-blank
        migrations.AlterField(
            model_name="stockitem",
            name="unit",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("g", "Grams"),
                    ("kg", "Kilograms"),
                    ("ml", "Millilitres"),
                    ("L", "Litres"),
                    ("pcs", "Pieces"),
                    ("tbsp", "Tablespoons"),
                    ("tsp", "Teaspoons"),
                    ("cup", "Cups"),
                ],
                default="g",
            ),
        ),
        # Remove unit from Ingredient after it's been copied to StockItem
        migrations.RemoveField(
            model_name="ingredient",
            name="unit",
        ),
    ]
