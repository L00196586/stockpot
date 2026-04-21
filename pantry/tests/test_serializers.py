from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.test import TestCase

from pantry.models import Ingredient, StockItem
from pantry.serializers import (
    IngredientSerializer,
    StockItemReadSerializer,
    StockItemWriteSerializer,
)


class IngredientSerializerTest(TestCase):
    def test_serializes_all_expected_fields(self):
        ingredient = Ingredient.objects.create(name="Olive Oil", unit="ml")
        data = IngredientSerializer(ingredient).data
        self.assertEqual(set(data.keys()), {"id", "name", "unit"})
        self.assertEqual(data["name"], "Olive Oil")
        self.assertEqual(data["unit"], "ml")

    def test_creates_ingredient_from_valid_data(self):
        serializer = IngredientSerializer(data={"name": "Butter", "unit": "g"})
        self.assertTrue(serializer.is_valid())
        ingredient = serializer.save()
        self.assertEqual(ingredient.name, "Butter")

    def test_unit_defaults_to_grams_when_no_value_provided(self):
        serializer = IngredientSerializer(data={"name": "Salt"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ingredient = serializer.save()
        self.assertEqual(ingredient.unit, "g")

    def test_rejects_invalid_unit_choice(self):
        serializer = IngredientSerializer(data={"name": "Wrong unit", "unit": "xyz"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("unit", serializer.errors)

    def test_rejects_duplicate_ingredient_name(self):
        Ingredient.objects.create(name="Salt", unit="g")
        serializer = IngredientSerializer(data={"name": "Salt", "unit": "kg"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_rejects_missing_name(self):
        serializer = IngredientSerializer(data={"unit": "g"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


class StockItemReadSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reader", password="pass")
        self.ingredient = Ingredient.objects.create(name="Eggs", unit="pcs")
        self.stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=12
        )

    def test_includes_all_expected_fields(self):
        data = StockItemReadSerializer(self.stock).data
        self.assertEqual(
            set(data.keys()),
            {"id", "ingredient", "quantity", "expiry_date", "created_at", "updated_at"},
        )

    def test_nests_full_ingredient_object(self):
        data = StockItemReadSerializer(self.stock).data
        self.assertIsInstance(data["ingredient"], dict)
        self.assertEqual(data["ingredient"]["name"], "Eggs")
        self.assertEqual(data["ingredient"]["unit"], "pcs")

    def test_expiry_date_is_null_when_not_set(self):
        data = StockItemReadSerializer(self.stock).data
        self.assertIsNone(data["expiry_date"])


class StockItemWriteSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="pass")
        self.ingredient = Ingredient.objects.create(name="Flour", unit="g")

    def _context(self):
        request = MagicMock()
        request.user = self.user
        return {"request": request}

    def test_creates_stock_item_with_valid_data(self):
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": self.ingredient.pk, "quantity": "500.00"},
            context=self._context(),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        stock = serializer.save()
        self.assertEqual(stock.user, self.user)
        self.assertEqual(stock.ingredient, self.ingredient)
        self.assertEqual(stock.quantity, 500)

    def test_assigns_requesting_user_on_create(self):
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": self.ingredient.pk, "quantity": "100.00"},
            context=self._context(),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        stock = serializer.save()
        self.assertEqual(stock.user, self.user)

    def test_expiry_date_is_optional(self):
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": self.ingredient.pk, "quantity": "100.00"},
            context=self._context(),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_expiry_date_is_accepted_when_provided(self):
        serializer = StockItemWriteSerializer(
            data={
                "ingredient_id": self.ingredient.pk,
                "quantity": "100.00",
                "expiry_date": "2027-01-01",
            },
            context=self._context(),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        stock = serializer.save()
        self.assertEqual(str(stock.expiry_date), "2027-01-01")

    def test_duplicate_ingredient_for_same_user_is_rejected(self):
        StockItem.objects.create(user=self.user, ingredient=self.ingredient, quantity=100)
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": self.ingredient.pk, "quantity": "200.00"},
            context=self._context(),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("ingredient_id", serializer.errors)

    def test_duplicate_check_is_skipped_on_update(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100
        )
        serializer = StockItemWriteSerializer(
            instance=stock,
            data={"ingredient_id": self.ingredient.pk, "quantity": "999.00"},
            context=self._context(),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_to_representation_returns_nested_ingredient_shape(self):
        stock = StockItem.objects.create(
            user=self.user, ingredient=self.ingredient, quantity=100
        )
        serializer = StockItemWriteSerializer(
            instance=stock,
            data={"ingredient_id": self.ingredient.pk, "quantity": "100.00"},
            context=self._context(),
        )
        serializer.is_valid()
        representation = serializer.to_representation(stock)
        self.assertIn("ingredient", representation)
        self.assertEqual(representation["ingredient"]["name"], "Flour")
        self.assertNotIn("ingredient_id", representation)

    def test_invalid_ingredient_id_is_rejected(self):
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": 9999, "quantity": "100.00"},
            context=self._context(),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("ingredient_id", serializer.errors)

    def test_missing_quantity_is_rejected(self):
        serializer = StockItemWriteSerializer(
            data={"ingredient_id": self.ingredient.pk},
            context=self._context(),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("quantity", serializer.errors)
