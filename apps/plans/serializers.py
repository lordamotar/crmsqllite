from rest_framework import serializers
from .models import Plan, PlanAssignment


class PlanAssignmentSerializer(serializers.ModelSerializer):
    """Сериализатор для назначения плана"""
    manager_name = serializers.CharField(
        source='manager.short_name',
        read_only=True
    )
    
    class Meta:
        model = PlanAssignment
        fields = [
            'id', 'manager', 'manager_name', 'target_count', 'target_sum',
            'criteria_operator', 'achieved_count', 'achieved_sum', 'is_achieved',
        ]
        read_only_fields = ['achieved_count', 'achieved_sum', 'is_achieved']


class PlanSerializer(serializers.ModelSerializer):
    """Сериализатор для плана с назначениями"""
    assignments = PlanAssignmentSerializer(many=True)
    created_by_name = serializers.CharField(
        source='created_by.short_name',
        read_only=True
    )
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'created_by', 'created_by_name', 'assignments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Создание плана с назначениями"""
        assignments_data = validated_data.pop('assignments', [])
        request = self.context.get('request')
        plan = Plan.objects.create(
            created_by=request.user if request else None,
            **validated_data
        )
        for assignment_data in assignments_data:
            PlanAssignment.objects.create(plan=plan, **assignment_data)
        return plan
    
    def update(self, instance, validated_data):
        """Обновление плана с назначениями"""
        assignments_data = validated_data.pop('assignments', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        
        if assignments_data is not None:
            # Удаляем все назначения и создаем заново
            instance.assignments.all().delete()
            for assignment_data in assignments_data:
                PlanAssignment.objects.create(plan=instance, **assignment_data)
        
        return instance


class PlanListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка планов"""
    created_by_name = serializers.CharField(
        source='created_by.short_name',
        read_only=True
    )
    assignments_count = serializers.IntegerField(
        source='assignments.count',
        read_only=True
    )
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'start_date', 'end_date',
            'created_by_name', 'assignments_count', 'created_at'
        ]

