import { mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import {
  abSession,
  sleep,
  hasSavedSession,
  ensureStateDir,
  snapshot,
  find,
  STATE_FILE,
  ARENA_URL,
  type SnapshotElement,
} from "./browser-core";
import type { SessionStatus } from "./types";

/**
 * Login flow for arena.ai.
 * ------------------------
 * arena.ai uses email + magic link:
 *   1. User enters their email.
 *   2. arena.ai shows a "Create Account" screen (for new emails) where the
 *      user can optionally enter their name, then clicks "Create Account".
 *   3. arena.ai sends a verification email with a magic link.
 *   4. The user opens the email and clicks the link.
 *   5. The link opens arena.ai with a session cookie set.
 *
 * We automate steps 1-3 here. Step 4-5 requires the user to interact with
 * their email client and then paste the resulting URL back into our UI,
 * which we handle in `completeMagicLink`.
 *
 * Why we cannot auto-complete: the magic link URL is sent to the user's
 * email. We cannot read their email. The user must click the link (or
 * copy-paste it), and the link must be opened in the SAME browser session
 * that initiated the login. Since agent-browser runs headless on the
 * server, we navigate to the URL on the user's behalf once they paste it
 * into the playground.
 */

/** Find a ref by simple text match against the snapshot lines. */
async function findRefByText(pattern: RegExp): Promise<string | null> {
  const snap = await abSession(["snapshot", "-i"]);
  const lines = snap.split("\n");
  for (const line of lines) {
    if (pattern.test(line)) {
      const m = line.match(/\[ref=(e\d+)\]/);
      if (m) return m[1];
    }
  }
  return null;
}

/** Open arena.ai and reveal the sidebar (the "Log In" button lives there). */
async function openArenaWithSidebar(): Promise<void> {
  if (hasSavedSession()) {
    try {
      await abSession(["state", "load", STATE_FILE]);
    } catch {
      /* ignore */
    }
  }
  await abSession(["open", ARENA_URL], { timeout: 60_000 });
  await sleep(4000);

  // If "Log In" is not visible, toggle the sidebar.
  let snap = await abSession(["snapshot", "-i"]);
  if (!/button "Log In"/i.test(snap)) {
    const m = snap.match(/button "Toggle Sidebar"\s*\[ref=(e\d+)\]/);
    if (m) {
      await abSession(["click", `@${m[1]}`]);
      await sleep(1500);
    }
    snap = await abSession(["snapshot", "-i"]);
  }
}

/** Open the login dialog by clicking the "Log In" button. */
async function openLoginDialog(): Promise<void> {
  await openArenaWithSidebar();
  const ref = await findRefByText(/button "Log In"/i);
  if (!ref) {
    throw new Error("Could not find 'Log In' button on arena.ai page");
  }
  await abSession(["click", `@${ref}`]);
  await sleep(2000);
}

/**
 * Send a magic link email to the given address.
 * Returns a structured result indicating whether the verification screen
 * was reached.
 */
export async function sendMagicLink(email: string): Promise<{
  ok: boolean;
  message: string;
}> {
  await openLoginDialog();

  // Fill the "Your email" textbox.
  const elements = await snapshot();
  const emailField = find(
    elements,
    (e) => e.role === "textbox" && /Your email/i.test(e.name),
  );
  if (!emailField) {
    throw new Error("Email textbox not found in login dialog");
  }

  await abSession(["fill", `@${emailField.ref}`, email]);
  await sleep(500);

  // Click "Continue with email".
  const elements2 = await snapshot();
  const continueBtn = find(
    elements2,
    (e) => e.role === "button" && /Continue with email/i.test(e.name),
  );
  if (!continueBtn) {
    throw new Error("'Continue with email' button not found");
  }
  await abSession(["click", `@${continueBtn.ref}`]);
  await sleep(3000);

  // The next screen is either:
  //   - "Create Account" (for new emails) — has a "Create Account" button and
  //     an optional "Full Name" field.
  //   - "Verify your email" (for existing users) — has a "Resend verification"
  //     button.
  // We handle both: if we see "Create Account", fill the name (optional)
  // and click it.
  const elements3 = await snapshot();
  const createBtn = find(
    elements3,
    (e) => e.role === "button" && /^Create Account$/i.test(e.name.trim()),
  );
  if (createBtn) {
    // New user — fill the optional name field, then submit.
    const nameField = find(
      elements3,
      (e) => e.role === "textbox" && /Full Name/i.test(e.name),
    );
    if (nameField) {
      await abSession(["fill", `@${nameField.ref}`, "Arena Proxy User"]);
      await sleep(300);
    }
    await abSession(["click", `@${createBtn.ref}`]);
    await sleep(4000);
  }

  // Verify we hit the "Check your email" / "Verify your email" screen.
  const pageText = await abSession(["eval", "document.body.innerText"]);
  const text = pageText.startsWith('"') ? JSON.parse(pageText) : pageText;

  if (
    /Check your email|Verify your email|magic link|Didn't receive the email|Resend verification/i.test(
      text,
    )
  ) {
    return {
      ok: true,
      message: `Magic link sent to ${email}. Open your email inbox, click the verification link, then copy the URL of the page that opens and paste it into the "Magic link URL" field.`,
    };
  }

  return {
    ok: false,
    message:
      "Login flow did not reach the email verification screen. The email may already be in use or arena.ai changed its flow.",
  };
}

/**
 * Complete the magic-link login by navigating agent-browser to the URL the
 * user clicked in their email. After this, the browser session will have
 * the authenticated cookies, which we then save.
 */
export async function completeMagicLink(magicLinkUrl: string): Promise<SessionStatus> {
  await abSession(["open", magicLinkUrl], { timeout: 60_000 });
  await sleep(6000);

  // Save the session — the cookies should now include the auth token.
  await ensureStateDir();
  await abSession(["state", "save", STATE_FILE]);

  // Verify login by re-opening arena.ai and checking for the "Log In" button.
  await abSession(["open", ARENA_URL], { timeout: 60_000 });
  await sleep(4000);

  const snap = await abSession(["snapshot", "-i"]);
  const loggedIn = !/button "Log In"/i.test(snap);

  // Try to extract the user identifier.
  let userIdentifier: string | undefined;
  if (loggedIn) {
    const elements: SnapshotElement[] = [];
    const lines = snap.split("\n");
    for (const line of lines) {
      const m = line.match(/^\s*-\s+(.*)$/);
      if (!m) continue;
      // Crude parse for the user button.
      if (/button "[^"]*@[^"]+"/.test(line)) {
        const nameMatch = line.match(/"([^"]*@[^\"]+)"/);
        if (nameMatch) {
          userIdentifier = nameMatch[1];
          break;
        }
      }
    }
    if (!userIdentifier) {
      // Try via eval — look for an email-shaped string in the DOM.
      try {
        const out = await abSession([
          "eval",
          "Array.from(document.querySelectorAll('button, [role=button]')).map(b => b.textContent).find(t => /@[a-z0-9.-]+\\.[a-z]{2,}/i.test(t)) || ''",
        ]);
        let v = out.trim();
        if (v.startsWith('"') && v.endsWith('"')) {
          try {
            v = JSON.parse(v);
          } catch {
            v = v.slice(1, -1);
          }
        }
        if (v) userIdentifier = v.trim();
      } catch {
        /* ignore */
      }
    }
  }

  return {
    has_saved_session: existsSync(STATE_FILE),
    logged_in: loggedIn,
    user_identifier: userIdentifier,
    last_verified_at: new Date().toISOString(),
  };
}
