package ua.aios.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private TextView status;
    private SharedPreferences prefs;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("aios", MODE_PRIVATE);
        String token = getIntent().getStringExtra("aios_token");
        if (token != null && token.length() >= 16) {
            prefs.edit().putString("token", token).apply();
        }
        buildUi();
        refreshStatus();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(36, 48, 36, 36);
        root.setGravity(Gravity.CENTER_HORIZONTAL);

        TextView title = new TextView(this);
        title.setText("AIOS Companion");
        title.setTextSize(26);
        root.addView(title);

        TextView note = new TextView(this);
        note.setText("Локальный защищённый адаптер. Доступен только через WireGuard и токен AIOS.");
        note.setTextSize(15);
        note.setPadding(0, 16, 0, 20);
        root.addView(note);

        status = new TextView(this);
        status.setTextSize(16);
        root.addView(status);

        root.addView(button("Запустить защищённый gateway", v -> startGateway()));
        root.addView(button("Разрешения: камера и геолокация", v -> requestRuntimePermissions()));
        root.addView(button("Разрешить доступ к уведомлениям", v -> openNotificationSettings()));
        root.addView(button("Разрешить управление приложениями", v -> openAccessibilitySettings()));
        root.addView(button("Обновить статус", v -> refreshStatus()));

        TextView safety = new TextView(this);
        safety.setText("AIOS не получает доступ к банковским приложениям, биометрии, SMS или звонкам без отдельного подтверждения.");
        safety.setTextSize(13);
        safety.setPadding(0, 24, 0, 0);
        root.addView(safety);
        setContentView(root);
    }

    private Button button(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(listener);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, 8, 0, 8);
        button.setLayoutParams(params);
        return button;
    }

    private void startGateway() {
        Intent intent = new Intent(this, CompanionService.class);
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        refreshStatus();
    }

    private void requestRuntimePermissions() {
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{
                    Manifest.permission.POST_NOTIFICATIONS,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                    Manifest.permission.CAMERA,
                    Manifest.permission.READ_MEDIA_IMAGES,
            }, 100);
        } else {
            requestPermissions(new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                    Manifest.permission.CAMERA,
            }, 100);
        }
    }

    private void openNotificationSettings() {
        try {
            startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        } catch (Exception ignored) {
        }
    }

    private void openAccessibilitySettings() {
        try {
            startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
        } catch (Exception ignored) {
        }
    }

    private void refreshStatus() {
        boolean token = prefs.getString("token", "").length() >= 16;
        boolean notifications = NotificationRelayService.isEnabled(this);
        boolean accessibility = AIOSAccessibilityService.isEnabled(this);
        String location = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ? "разрешена" : "не выдана";
        status.setText("Токен AIOS: " + (token ? "настроен" : "ожидает настройки") + "\n"
                + "Уведомления: " + (notifications ? "разрешены" : "не разрешены") + "\n"
                + "Управление приложениями: " + (accessibility ? "разрешено" : "не разрешено") + "\n"
                + "Геолокация: " + location + "\n"
                + "Gateway: локальный порт 8765 (после запуска)");
    }
}
