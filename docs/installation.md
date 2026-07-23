# Installation

## From Source

```bash
git clone https://github.com/JoTalbot/AIOS.git
cd AIOS
pip install -r requirements.txt
```

## Using pip (future)

```bash
pip install aios
```

## Docker

```bash
docker-compose up -d
```

## Kubernetes

```bash
helm install aios ./helm/aios
```

## Development

```bash
pip install -r requirements.txt
pip install -e .
python -m pytest
```
