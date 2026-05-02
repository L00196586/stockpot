from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import VALID_DIETARY_KEYS


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        label="Confirm password",
    )

    def validate_email(self, value):
        normalised = value.lower()
        if User.objects.filter(email__iexact=normalised).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalised

    def validate_password(self, value):
        # Runs Django's validators (minimum length, commonality, numeric-only, etc.)
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        # Use email as username. Slice to respect the 150-char username field limit
        username = email[:150]
        return User.objects.create_user(username=username, email=email, password=password)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs["email"].lower()
        password = attrs["password"]

        # Username is set to the email on registration
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        # Generic message to prevent user enumeration
        if user is None:
            raise serializers.ValidationError(
                {"non_field_errors": "Invalid email or password."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": "Invalid email or password."}
            )

        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.Serializer):
    """
    Handles GET and PATCH for /api/auth/profile/.
    Email and dietary_preferences are always editable.
    new_password / new_password2 are optional — only processed when non-empty.
    """
    email = serializers.EmailField(required=False)
    dietary_preferences = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    new_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        style={"input_type": "password"},
    )
    new_password2 = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        style={"input_type": "password"},
        label="Confirm new password",
    )

    def validate_email(self, value):
        normalised = value.lower()
        user = self.context["request"].user
        if User.objects.filter(email__iexact=normalised).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email address is already in use.")
        return normalised

    def validate_dietary_preferences(self, value):
        invalid = [v for v in value if v not in VALID_DIETARY_KEYS]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid dietary preference(s): {', '.join(invalid)}"
            )
        return list(set(value))

    def validate(self, attrs):
        new_password = attrs.get("new_password", "")
        new_password2 = attrs.get("new_password2", "")
        if new_password or new_password2:
            if new_password != new_password2:
                raise serializers.ValidationError({"new_password2": "Passwords do not match."})
            validate_password(new_password, self.context["request"].user)
        return attrs

    def update(self, instance, validated_data):
        if "email" in validated_data:
            instance.email = validated_data["email"]
            instance.username = validated_data["email"][:150]
        new_password = validated_data.get("new_password", "")
        if new_password:
            instance.set_password(new_password)
        instance.save()
        if "dietary_preferences" in validated_data:
            instance.profile.dietary_preferences = validated_data["dietary_preferences"]
            instance.profile.save()
        return instance
