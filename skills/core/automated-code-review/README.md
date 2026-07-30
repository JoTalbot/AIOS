# Automated Code Review

Автоматический code review для выявления антипаттернов в коде.

## Функции
- ✅ Magic numbers detection
- ✅ Hardcoded credentials detection
- ✅ Long lines detection
- ✅ Deprecated patterns detection
- ✅ Code complexity metrics

## Использование
```bash
# Code review файла
python3 code/run.py /path/to/file.py

# Code review с кастомным порогом
python3 code/run.py /path/to/file.py 15

# Pipe input
echo '{"file_path": "/path/to/file.py"}' | python3 code/run.py
```

## Вывод
```json
{
  "skill": "automated-code-review",
  "file_path": "/path/to/file.py",
  "metrics": {
    "lines": 150,
    "magic_numbers": 5,
    "hardcoded_secrets": 0,
    "long_lines": 12,
    "deprecated_patterns": 1
  },
  "issues": [
    "Found 5 magic numbers",
    "Found 12 lines > 100 chars"
  ],
  "status": "needs_improvement",
  "severity": "medium"
}
```
