# AIOS K8s operator (deploy/k8s) — alpha.23

CRD-модель флота AIOS-платформ и базовые манифесты. Контроллер —
тонкий Python-цикл (kopf-style, но без kopf-зависимости: собственный
watch-loop HTTP API Kubernetes, `aios_core/platforms/koperator.py`).

## Модель

| CRD | Назначение | Маппинг на AIOS |
| --- | --- | --- |
| `Platform.aios.io` | онбординг-пакет площадки | `platforms/<name>.yaml` |
| `Profile.aios.io` | аккаунт + привязка к устройству | ProfileStore entry |
| `Job.aios.io` | pull-задача (kind/payload) | ShardJobs.enqueue |

## Применить

```bash
kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl apply -f deploy/k8s/01-crds.yaml
kubectl apply -f deploy/k8s/02-rbac.yaml
kubectl apply -f deploy/k8s/03-operator-deployment.yaml

# пример CR:
kubectl apply -f deploy/k8s/example-cr.yaml
kubectl -n aios-fleet get platforms,profiles,jobs
```

Оператор (образ `ghcr.io/jotalbot/aios:9.1.0-alpha.1`) читает CR:
`Platform` → регистрирует/обновляет yaml-дескриптор в кластерном
ConfigMap; `Profile` → заводит профиль в ProfileStore (sqlite PVC);
`Job` → enqueue в shard jobs-базу, которую разбирают worker-поды.
Guarded-семантика (outbox/confirm/compliance) сохраняется на уровне
видов джоб, оператор лишь материализует желаемое состояние.

Файл `example-cr.yaml` — только пример; без кластера тесты ограничиваются
YAML-валидацией манифестов (в sandbox нет kubectl).
