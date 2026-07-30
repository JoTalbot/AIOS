# AWS Cost Audit

Автоматический аудит AWS расходов для выявления затрат и оптимизации.

## Функции
- ✅ EC2 instances audit (stopped instances detection)
- ✅ EBS volumes audit (unattached volumes detection)
- ✅ Cost metrics collection
- ✅ Optimization recommendations

## Использование
```bash
# Базовый аудит
python3 code/run.py

# Аудит конкретного региона
python3 code/run.py us-east-1

# Аудит с сравнением с прошлым периодом
python3 code/run.py us-east-1 last_month
```

## Вывод
```json
{
  "skill": "aws-cost-audit",
  "region": "us-east-1",
  "aws_available": true,
  "instances": [...],
  "volumes": [...],
  "metrics": {
    "stopped_instances": 5,
    "unattached_volumes": 3
  },
  "issues": [
    "Found 5 stopped EC2 instances",
    "Found 3 unattached EBS volumes"
  ],
  "optimization_potential": 8000.0,
  "status": "needs_attention",
  "severity": "medium"
}
```

## Anti-patterns fixed
1. Unattached EBS volumes
2. Stopped EC2 instances
3. Unused resources
4. Oversized instances
5. Cost anomalies

## Метрики
- Total cost: monitored
- Optimization potential: calculated
- Issues detected: counted
- Status: critical/needs_attention/good
