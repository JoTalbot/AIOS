package ua.aios.companion;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        String token = context.getSharedPreferences("aios", Context.MODE_PRIVATE).getString("token", "");
        if (token.length() < 16) return;
        try {
            Intent service = new Intent(context, CompanionService.class);
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(service);
            else context.startService(service);
        } catch (Exception ignored) {
        }
    }
}
