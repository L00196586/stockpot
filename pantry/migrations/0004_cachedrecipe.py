from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pantry", "0003_move_unit_to_stockitem"),
    ]

    operations = [
        migrations.CreateModel(
            name="CachedRecipe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipe_id", models.IntegerField(unique=True)),
                ("title", models.CharField(max_length=500)),
                ("image", models.URLField(blank=True, default="")),
                ("ready_in_minutes", models.IntegerField(blank=True, null=True)),
                ("prep_minutes", models.IntegerField(blank=True, null=True)),
                ("cook_minutes", models.IntegerField(blank=True, null=True)),
                ("nutrition", models.JSONField(default=list)),
                ("instructions", models.JSONField(default=list)),
                ("cached_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["recipe_id"],
            },
        ),
    ]
