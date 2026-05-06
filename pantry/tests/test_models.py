import datetime
import time

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from pantry.models import Ingredient, StockItem, SavedRecipe


class IngredientModelTest(TestCase):

    def test_str_representation(self):
        ingredient = Ingredient(name="Flour")
        self.assertEqual(str(ingredient), "Flour")

    def test_name_is_unique(self):
        Ingredient.objects.create(name="Flour")
        with self.assertRaises(IntegrityError):
            Ingredient.objects.create(name="Flour")

    def test_ordering_is_alphabetical_by_name(self):
        Ingredient.objects.create(name="Zucchini")
        Ingredient.objects.create(name="Apple")
        Ingredient.objects.create(name="Milk")
        names = list(Ingredient.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Apple", "Milk", "Zucchini"])


class StockItemModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.ingredient = Ingredient.objects.create(name="Flour")

    def test_str_representation(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=500, unit="g"
        )
        self.assertEqual(str(stock), "testuser – Flour: 500g")

    def test_default_unit_is_grams(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100
        )
        self.assertEqual(stock.unit, StockItem.Unit.GRAMS)

    def test_all_unit_choices_are_valid(self):
        valid_units = ["g", "kg", "ml", "L", "pcs", "tbsp", "tsp", "cup"]
        for i, unit in enumerate(valid_units):
            ing = Ingredient.objects.create(name=f"Ingredient {i}")
            stock = StockItem.objects.create(user=self.user, ingredient=ing, quantity=1, unit=unit)
            self.assertEqual(stock.unit, unit)

    def test_expiry_date_is_optional(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100
        )
        self.assertIsNone(stock.expiry_date)

    def test_expiry_date_can_be_set(self):
        expiry = datetime.date(2026, 12, 31)
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100, expiry_date=expiry
        )
        self.assertEqual(stock.expiry_date, expiry)

    def test_timestamps_are_set_on_create(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100
        )
        self.assertIsNotNone(stock.created_at)
        self.assertIsNotNone(stock.updated_at)

    def test_unique_together_prevents_duplicate_user_ingredient(self):
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100)
        with self.assertRaises(IntegrityError):
            StockItem.objects.create(
                user=self.user, ingredient=self.ingredient, quantity=200
            )

    def test_different_users_can_stock_same_ingredient_with_different_units(self):
        user2 = User.objects.create_user(username="user2", password="pass")
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100, unit="g")
        stock2 = StockItem.objects.create(
            user=user2, ingredient=self.ingredient, quantity=2, unit="kg"
        )
        self.assertEqual(stock2.unit, "kg")

    def test_deleting_user_cascades_to_stock_items(self):
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100)
        self.user.delete()
        self.assertEqual(StockItem.objects.count(), 0)

    def test_deleting_ingredient_cascades_to_stock_items(self):
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100)
        self.ingredient.delete()
        self.assertEqual(StockItem.objects.count(), 0)

    def test_ordering_is_alphabetical_by_ingredient_name(self):
        apple = Ingredient.objects.create(name="Apple")
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100)
        StockItem.objects.create(user=self.user, ingredient=apple, quantity=5)
        names = list(
            StockItem.objects.filter(user=self.user).values_list("ingredient__name", flat=True)
        )
        self.assertEqual(names, ["Apple", "Flour"])


class SavedRecipeModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")

    def test_str_representation(self):
        saved = SavedRecipe.objects.create(user=self.user, recipe_id=42, title="Pancakes")
        self.assertEqual(str(saved), "testuser – Pancakes")

    def test_unique_together_prevents_duplicated_user_recipe(self):
        SavedRecipe.objects.create(user=self.user, recipe_id=42, title="Pancakes")
        with self.assertRaises(IntegrityError):
            SavedRecipe.objects.create(user=self.user, recipe_id=42, title="Pancakes again")

    def test_two_users_can_save_same_recipe(self):
        SavedRecipe.objects.create(user=self.user, recipe_id=42, title="Pancakes")
        saved = SavedRecipe.objects.create(user=self.other_user, recipe_id=42, title="Pancakes")
        self.assertEqual(saved.recipe_id, 42)

    def test_image_defaults_to_empty_string(self):
        saved = SavedRecipe.objects.create(user=self.user, recipe_id=42, title="Pancakes")
        self.assertEqual(saved.image, "")

    def test_ordering_is_newest_first(self):
        SavedRecipe.objects.create(user=self.user, recipe_id=1, title="First")
        time.sleep(0.01)
        newest = SavedRecipe.objects.create(user=self.user, recipe_id=2, title="Second")
        qs = list(SavedRecipe.objects.filter(user=self.user))
        self.assertEqual(qs[0].pk, newest.pk)
