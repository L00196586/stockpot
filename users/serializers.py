from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


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
