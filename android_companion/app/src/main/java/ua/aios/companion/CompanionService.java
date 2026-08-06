package ua.aios.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.pm.ApplicationInfo;
import android.content.pm.ServiceInfo;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.os.BatteryManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.InetSocketAddress;
import java.net.InetAddress;
import java.net.Inet4Address;
import java.net.NetworkInterface;
import java.net.URLDecoder;
import java.util.Enumeration;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

public class CompanionService extends Service {
    private static final int PORT = 8765;
    private static final String CHANNEL_ID = "aios_gateway";
    private volatile boolean running = false;
    private ServerSocket server;
    private Thread worker;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        } else {
            startForeground(1, notification());
        }
        if (!running) {
            running = true;
            worker = new Thread(this::serve, "aios-companion-server");
            worker.start();
        }
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        running = false;
        try { if (server != null) server.close(); } catch (Exception ignored) {}
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        super.onDestroy();
    }

    private Notification notification() {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL_ID,
                    getString(R.string.notification_channel), NotificationManager.IMPORTANCE_LOW));
        }
        return new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("AIOS Companion активен")
                .setContentText("Локальный gateway доступен только через WireGuard")
                .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
                .build();
    }

    private void serve() {
        // Rebind on transient Android app-update/process races instead of silently
        // losing the gateway after a port conflict.
        while (running) {
            try {
                // Never bind the authenticated HTTP gateway to Wi-Fi/mobile
                // interfaces.  The Companion is reachable only over the known
                // WireGuard subnet; if the tunnel is down we wait and retry.
                InetAddress tunnel = wireGuardAddress();
                if (tunnel == null) {
                    Log.w("AIOSCompanion", "WireGuard address unavailable; gateway stays private and will retry");
                    try { Thread.sleep(3000); } catch (InterruptedException ignored) { }
                    continue;
                }
                ServerSocket candidate = new ServerSocket();
                candidate.setReuseAddress(true);
                candidate.bind(new InetSocketAddress(tunnel, PORT));
                server = candidate;
                Log.i("AIOSCompanion", "Gateway bound to WireGuard only: " + tunnel.getHostAddress());
                while (running) {
                    Socket socket = candidate.accept();
                    new Thread(() -> handle(socket), "aios-companion-client").start();
                }
            } catch (Exception error) {
                Log.e("AIOSCompanion", "Gateway bind/serve error; retrying", error);
                try { Thread.sleep(2000); } catch (InterruptedException ignored) { }
            } finally {
                try { if (server != null) server.close(); } catch (Exception ignored) { }
                server = null;
            }
        }
    }

    private void handle(Socket socket) {
        try (Socket ignored = socket;
             BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8))) {
            socket.setSoTimeout(10000);
            String request = reader.readLine();
            if (request == null || request.length() > 4096) return;
            String[] requestParts = request.split(" ");
            if (requestParts.length < 2 || !"GET".equals(requestParts[0])) {
                respond(writer, 405, new JSONObject().put("error", "method_not_allowed"));
                return;
            }
            String token = "";
            String line;
            int headerCount = 0;
            while ((line = reader.readLine()) != null && !line.isEmpty()) {
                if (++headerCount > 32 || line.length() > 4096) {
                    respond(writer, 400, new JSONObject().put("error", "invalid_headers"));
                    return;
                }
                int colon = line.indexOf(':');
                if (colon > 0 && line.substring(0, colon).trim().equalsIgnoreCase("X-AIOS-Token")) {
                    token = line.substring(colon + 1).trim();
                }
            }
            if (!constantTimeEquals(token, configuredToken())) {
                respond(writer, 403, new JSONObject().put("error", "forbidden"));
                return;
            }
            String target = requestParts[1];
            int queryIndex = target.indexOf('?');
            String path = queryIndex >= 0 ? target.substring(0, queryIndex) : target;
            String query = queryIndex >= 0 ? target.substring(queryIndex + 1) : "";
            JSONObject response;
            boolean knownPath = true;
            switch (path) {
                case "/health": response = health(); break;
                case "/battery": response = battery(); break;
                case "/apps": response = apps(); break;
                case "/permissions": response = permissions(); break;
                case "/capture-status": response = captureStatus(); break;
                case "/location": response = location(); break;
                case "/location-status": response = locationStatus(); break;
                case "/accessibility": response = accessibility(); break;
                case "/ui":
                    // Full node text is served only after a deliberate request;
                    // the default is a controls-only tree with no chat content.
                    response = AIOSAccessibilityService.snapshot("full".equalsIgnoreCase(queryValue(query, "detail")));
                    break;
                case "/clipboard": response = clipboard(queryValue(query, "text")); break;
                case "/notifications":
                    response = new JSONObject().put("status", "ok").put("notifications", NotificationRelayService.snapshot());
                    break;
                default:
                    response = new JSONObject().put("error", "not_found");
                    knownPath = false;
            }
            // A known endpoint may legitimately return a typed error such as
            // location_unavailable. Preserve its JSON instead of hiding it as HTTP 404.
            respond(writer, knownPath ? 200 : 404, response);
        } catch (Exception ignored) {
        }
    }

    private InetAddress wireGuardAddress() {
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface iface = interfaces.nextElement();
                String name = (iface.getName() == null ? "" : iface.getName()).toLowerCase();
                // Android WireGuard can be exposed as wg0 or a tun interface.
                if (!(name.startsWith("wg") || name.contains("wireguard") || name.startsWith("tun"))) continue;
                Enumeration<InetAddress> addresses = iface.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress address = addresses.nextElement();
                    if (address instanceof Inet4Address && address.getHostAddress().startsWith("10.203.")) {
                        return address;
                    }
                }
            }
        } catch (Exception error) {
            Log.w("AIOSCompanion", "Cannot inspect WireGuard interface", error);
        }
        return null;
    }

    private String configuredToken() {
        SharedPreferences prefs = getSharedPreferences("aios", MODE_PRIVATE);
        return prefs.getString("token", "");
    }

    private boolean constantTimeEquals(String left, String right) {
        try {
            return MessageDigest.isEqual(left.getBytes(StandardCharsets.UTF_8), right.getBytes(StandardCharsets.UTF_8)) && right.length() >= 16;
        } catch (Exception e) {
            return false;
        }
    }

    private String queryValue(String query, String key) {
        try {
            for (String pair : query.split("&")) {
                int index = pair.indexOf('=');
                if (index > 0 && pair.substring(0, index).equals(key)) {
                    return URLDecoder.decode(pair.substring(index + 1), "UTF-8");
                }
            }
        } catch (Exception ignored) {
        }
        return "";
    }

    private JSONObject clipboard(String text) throws Exception {
        if (text == null || text.isEmpty()) return new JSONObject().put("error", "clipboard_text_required");
        ClipboardManager manager = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        manager.setPrimaryClip(ClipData.newPlainText("AIOS", text));
        return new JSONObject().put("status", "ok").put("length", text.length());
    }

    private void respond(BufferedWriter writer, int status, JSONObject data) throws Exception {
        byte[] body = data.toString().getBytes(StandardCharsets.UTF_8);
        writer.write("HTTP/1.1 " + status + (status == 200 ? " OK" : " Error") + "\r\n");
        writer.write("Content-Type: application/json; charset=utf-8\r\n");
        writer.write("Content-Length: " + body.length + "\r\nConnection: close\r\n\r\n");
        writer.write(new String(body, StandardCharsets.UTF_8));
        writer.flush();
    }

    private JSONObject health() throws Exception {
        JSONObject result = battery();
        result.put("status", "ok");
        try { result.put("version", getPackageManager().getPackageInfo(getPackageName(), 0).versionName); } catch (Exception e) { result.put("version", ""); }
        result.put("model", Build.MODEL);
        result.put("android", Build.VERSION.RELEASE);
        result.put("sdk", Build.VERSION.SDK_INT);
        result.put("network", networkName());
        return result;
    }

    private JSONObject battery() throws Exception {
        BatteryManager manager = (BatteryManager) getSystemService(Context.BATTERY_SERVICE);
        return new JSONObject().put("battery", manager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY));
    }

    private JSONObject apps() throws Exception {
        JSONArray packages = new JSONArray();
        List<ApplicationInfo> list = getPackageManager().getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0));
        for (ApplicationInfo app : list) packages.put(app.packageName);
        return new JSONObject().put("status", "ok").put("apps", packages);
    }

    private JSONObject permissions() throws Exception {
        return new JSONObject()
                .put("status", "ok")
                .put("notification_listener", NotificationRelayService.isEnabled(this))
                .put("accessibility", AIOSAccessibilityService.isEnabled(this))
                .put("location", checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
                .put("camera", checkSelfPermission(android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
                .put("microphone", checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)
                .put("media", Build.VERSION.SDK_INT < 33 || checkSelfPermission(android.Manifest.permission.READ_MEDIA_IMAGES) == PackageManager.PERMISSION_GRANTED);
    }

    private JSONObject captureStatus() throws Exception {
        boolean camera = checkSelfPermission(android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
        boolean microphone = checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        // The Companion intentionally exposes readiness only. There is no
        // camera/microphone capture endpoint and no background capture path.
        return new JSONObject().put("status", "ok")
                .put("camera_permission", camera)
                .put("microphone_permission", microphone)
                .put("camera_capture_enabled", false)
                .put("microphone_capture_enabled", false)
                .put("background_capture", false);
    }

    private JSONObject accessibility() throws Exception {
        return new JSONObject().put("status", "ok")
                .put("enabled", AIOSAccessibilityService.isEnabled(this));
    }

    private JSONObject locationStatus() throws Exception {
        boolean permission = checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        LocationManager manager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        boolean gps = false;
        boolean network = false;
        try { gps = manager.isProviderEnabled(LocationManager.GPS_PROVIDER); } catch (Exception ignored) { }
        try { network = manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER); } catch (Exception ignored) { }
        return new JSONObject().put("status", "ok")
                .put("permission", permission)
                .put("gps_enabled", gps)
                .put("network_enabled", network)
                .put("ready", permission && (gps || network));
    }

    private JSONObject location() throws Exception {
        if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            return new JSONObject().put("error", "location_permission_required");
        }
        LocationManager manager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        Location location = manager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
        if (location == null) location = manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
        if (location == null) return new JSONObject().put("error", "location_unavailable");
        return new JSONObject().put("status", "ok")
                .put("latitude", location.getLatitude()).put("longitude", location.getLongitude())
                .put("accuracy_m", location.getAccuracy()).put("time", location.getTime());
    }

    private String networkName() {
        ConnectivityManager manager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkCapabilities caps = manager.getNetworkCapabilities(manager.getActiveNetwork());
        if (caps == null) return "offline";
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return "wifi";
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) return "cellular";
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) return "vpn";
        return "other";
    }
}
