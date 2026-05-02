from rest_framework import serializers
from .models import Ingredient, SavedRecipe, StockItem


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "unit"]


class StockItemReadSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = StockItem
        fields = ["id", "ingredient", "quantity", "expiry_date", "created_at", "updated_at"]


class StockItemWriteSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
    )

    class Meta:
        model = StockItem
        fields = ["id", "ingredient_id", "quantity", "expiry_date"]

    def validate(self, attrs):
        request = self.context.get("request")
        ingredient = attrs.get("ingredient")

        # On create, prevent duplicates. The User should use PATCH to update the existing item instead
        if self.instance is None and ingredient:
            if StockItem.objects.filter(user=request.user, ingredient=ingredient).exists():
                raise serializers.ValidationError(
                    {"ingredient_id": "This ingredient is already in your pantry. Use PATCH to update it."}
                )
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        return StockItemReadSerializer(instance, context=self.context).data


class SavedRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRecipe
        fields = ["id", "recipe_id", "title", "image", "saved_at"]
        read_only_fields = ["id", "saved_at"]

    def validate_recipe_id(self, value):
        request = self.context.get("request")
        if SavedRecipe.objects.filter(user=request.user, recipe_id=value).exists():
            raise serializers.ValidationError("This recipe is already in your favourites.")
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
