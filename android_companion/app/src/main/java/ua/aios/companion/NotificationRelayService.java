package ua.aios.companion;

import android.content.ComponentName;
import android.content.Context;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.os.Bundle;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class NotificationRelayService extends NotificationListenerService {
    private static final List<JSONObject> EVENTS = Collections.synchronizedList(new ArrayList<>());

    public static boolean isEnabled(Context context) {
        String enabled = Settings.Secure.getString(context.getContentResolver(), "enabled_notification_listeners");
        if (enabled == null) return false;
        return enabled.contains(new ComponentName(context, NotificationRelayService.class).flattenToString());
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            Bundle extras = sbn.getNotification().extras;
            JSONObject event = new JSONObject();
            event.put("package", sbn.getPackageName());
            event.put("title", trim(String.valueOf(extras.getCharSequence("android.title")), 160));
            event.put("text", trim(String.valueOf(extras.getCharSequence("android.text")), 300));
            event.put("posted_at", sbn.getPostTime());
            synchronized (EVENTS) {
                EVENTS.add(event);
                while (EVENTS.size() > 30) EVENTS.remove(0);
            }
        } catch (Exception ignored) {
        }
    }

    public static JSONArray snapshot() {
        JSONArray result = new JSONArray();
        synchronized (EVENTS) {
            for (JSONObject event : EVENTS) result.put(event);
        }
        return result;
    }

    private static String trim(String value, int max) {
        if (value == null || "null".equals(value)) return "";
        return value.length() > max ? value.substring(0, max) : value;
    }
}
