package ua.aios.companion;

import android.accessibilityservice.AccessibilityService;
import android.content.ComponentName;
import android.content.Context;
import android.graphics.Rect;
import android.provider.Settings;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONObject;

public class AIOSAccessibilityService extends AccessibilityService {
    private static volatile AIOSAccessibilityService instance;
    private static final int MAX_NODES = 500;

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Snapshot is pulled explicitly via the authenticated local gateway.
        // No screen text is uploaded, stored or logged automatically.
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public void onDestroy() {
        instance = null;
        super.onDestroy();
    }

    public static boolean isEnabled(Context context) {
        String enabled = Settings.Secure.getString(context.getContentResolver(), "enabled_accessibility_services");
        if (enabled == null) return false;
        return enabled.contains(new ComponentName(context, AIOSAccessibilityService.class).flattenToString());
    }

    /**
     * A controls-only snapshot is the safe default.  Full text is available
     * only after an authenticated server request explicitly asks for it; the
     * server uses that mode solely inside a confirmed app workflow and never
     * writes the returned text to logs.
     */
    public static JSONObject snapshot() {
        return snapshot(false);
    }

    public static JSONObject snapshot(boolean includeText) {
        try {
            if (instance == null) return new JSONObject().put("error", "accessibility_not_enabled");
            AccessibilityNodeInfo root = instance.getRootInActiveWindow();
            if (root == null) return new JSONObject().put("error", "active_window_unavailable");
            JSONArray nodes = new JSONArray();
            String packageName = trim(root.getPackageName());
            walk(root, nodes, 0, includeText);
            root.recycle();
            return new JSONObject().put("status", "ok")
                    .put("package", packageName)
                    .put("nodes", nodes);
        } catch (Exception error) {
            try { return new JSONObject().put("error", error.getClass().getSimpleName()); }
            catch (Exception ignored) { return new JSONObject(); }
        }
    }

    private static void walk(AccessibilityNodeInfo node, JSONArray output, int depth, boolean includeText) throws Exception {
        if (node == null || output.length() >= MAX_NODES || depth > 32) return;
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        JSONObject item = new JSONObject();
        // A controls-only tree contains geometry and roles, not private chat,
        // banking or location text.  This is sufficient for health/status and
        // forces a deliberate full snapshot for a user-approved workflow.
        if (includeText) {
            item.put("text", trim(node.getText()));
            item.put("description", trim(node.getContentDescription()));
        }
        item.put("resource", trim(node.getViewIdResourceName()));
        item.put("class", trim(node.getClassName()));
        item.put("clickable", node.isClickable());
        item.put("editable", node.isEditable());
        item.put("bounds", new JSONArray().put(bounds.left).put(bounds.top).put(bounds.right).put(bounds.bottom));
        output.put(item);
        for (int i = 0; i < node.getChildCount() && output.length() < MAX_NODES; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            try { walk(child, output, depth + 1, includeText); }
            finally { if (child != null) child.recycle(); }
        }
    }

    private static String trim(CharSequence text) {
        if (text == null) return "";
        String value = text.toString();
        return value.length() > 500 ? value.substring(0, 500) : value;
    }
}
