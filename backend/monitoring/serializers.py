from rest_framework import serializers
from .models import SensorData, SiteVisibility, Site, SensorReading


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'


class SiteVisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteVisibility
        fields = ['device_id', 'is_hidden']

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = [
            'id',
            'device_id',
            'timestamp',
            'wind_speed',
            'wind_speed_ms',
            'pitch',
            'roll',
            'tilt_rate',
            'sway',
            'total_tilt',
            'indikator',
        ]
        read_only_fields = ['id', 'timestamp']


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']

