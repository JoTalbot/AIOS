# Руководство по развертыванию (Deploy) и использованию AIOS

Данный документ содержит подробные инструкции по развертыванию инфраструктуры **AIOS** (в том числе в "1 клик"), а также детальное руководство по работе с мобильной роботизацией (RPA) для **Android приложений**.

---

## 🚀 Деплой в 1 Клик (All-in-One)

Для локального запуска всей системы вместе с Android-эмулятором был подготовлен специальный скрипт `deploy-all-in-one.sh`.

### Системные требования:
* **Docker** и **Docker Compose**
* Поддержка аппаратной виртуализации (KVM) для Android эмулятора (в Linux: `kvm-ok` должно выдавать *KVM acceleration can be used*).

### Как запустить:
1. Откройте терминал в корневой папке проекта (`/AIOS/`).
2. Запустите скрипт:
   ```bash
   ./deploy-all-in-one.sh
   ```
3. Скрипт выполнит:
   * Копирование файла `.env.example` в `.env` (если его нет).
   * Запуск Docker Compose (поднимет `aios-api`, `aios-mcp` и `aios-dashboard`).
   * Сборку образа из `Dockerfile.android`.
   * Запуск контейнера `aios-android-emulator` с пробросом KVM.

### Результат (точки входа):
* **Dashboard (UI)**: [http://localhost:8080](http://localhost:8080)
* **REST API**: [http://localhost:8000](http://localhost:8000)
* **MCP Server**: `localhost:8471`
* **Android Emulator (ADB)**: `localhost:5555`

---

## 📱 Роботизация и управление Android-приложениями

Подсистема AIOS для мобильных платформ позволяет агентам (например, `ai_agent.py` или парсерам) напрямую управлять интерфейсом любых Android-приложений (клики, свайпы, ввод текста).

### 1. Архитектура мобильной RPA
* **Среда выполнения**: Изолированный Docker-контейнер (`Dockerfile.android`), базирующийся на ОС Debian и Android SDK 35.
* **Эмулятор**: По умолчанию поднимается устройство **AIOS_Slando** (`pixel` профиль).
* **Связь (Bridge)**: Осуществляется через ADB (Android Debug Bridge), Python скрипты (например, `test_real_android_app.py`) обращаются к интерфейсу через uiautomator или Appium.

### 2. Подготовка и установка APK (Android-приложений)
Чтобы AIOS мог взаимодействовать с приложением, его нужно установить на эмулятор.

* **Ручная установка через ADB:**
  ```bash
  # Подключаемся к работающему эмулятору
  adb connect localhost:5555
  # Устанавливаем целевой APK (например, клиент OLX / Slando)
  adb install ./data/apps/ua.slando.apk
  ```

* **Автоматическая установка через AIOS:**
  Поместите нужные `.apk` файлы в папку `platforms/`. Оркестратор AIOS (при наличии соответствующих задач) сможет автоматически установить их в эмулятор, используя модуль `android_registry.py`.

### 3. Инструкция по написанию сценариев (Скриптов автоматизации)
Управление Android-приложением в AIOS строится на концепции **Драйвера** (`android_driver.py` и `android_rpa_bridge.py`).

**Пример вызова автоматизации из Python-кода:**
```python
from aios_core.android_driver import AndroidDriver

# 1. Инициализация драйвера для конкретного пакета
driver = AndroidDriver(package_name="ua.slando", device_serial="localhost:5555")

# 2. Запуск приложения
driver.launch_app()

# 3. Инструкции для агента (UI Automator)
driver.wait_for_element(element_id="ua.slando:id/button_search", timeout=10)
driver.click(element_id="ua.slando:id/button_search")
driver.input_text(element_id="ua.slando:id/search_bar", text="MacBook Pro")

# 4. Сбор (скрейпинг) информации с экрана
screen_data = driver.dump_screen_hierarchy()
print("Найдено элементов на экране:", len(screen_data))
```

### 4. Отладка и мониторинг Android-подсистемы
При возникновении ошибок или для разработки новых сценариев вам понадобится визуальный контроль:
* **Логи эмулятора:** `docker logs -f aios-android-emulator`
* **VNC / Scrcpy:** Для просмотра экрана (screencast) можно запустить инструмент `scrcpy` на вашей локальной машине:
  ```bash
  scrcpy -s localhost:5555
  ```
  *Это выведет живой экран эмулятора прямо на ваш рабочий стол, что невероятно полезно для отладки свайпов и поиска `id` элементов.*

---

## ☁️ Развертывание в Production (AWS EKS & Kubernetes)

Если вам нужно развернуть AIOS не локально, а в облаке для высоких нагрузок (Cloud Production):

1. **Развертывание AWS Инфраструктуры (Terraform)**
   ```bash
   cd terraform/aws
   terraform init
   terraform apply
   ```
   *Это поднимет AWS EKS, управляемую базу RDS PostgreSQL 16 и Redis ElastiCache.*

2. **Деплой через Helm (Kubernetes)**
   ```bash
   aws eks update-kubeconfig --region eu-central-1 --name aios-prod-cluster
   helm upgrade --install aios-prod ./helm/aios --namespace production --create-namespace
   ```

3. **Особенности мобильного облака:**
   В облачном режиме контейнеры с Android-эмуляторами ресурсоёмки (требуют nested virtualization или bare-metal нод AWS - инстансы типа `mac` или `metal`). В `values.yaml` для мобильных нод предусмотрены отдельные NodeSelectors.
