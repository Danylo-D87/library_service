from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("borrowing", "status", "type", "session_id", "session_url", "money_to_pay")
        read_only_fields = ("status", "session_id", "session_url")
