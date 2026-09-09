# Connect a calendar

Yaad creates prayer reminders as events in a calendar you own. That makes the
reminders native Calendar alarms on your device, rather than notifications from
another app. Connect iCloud Calendar, Google Calendar, or both.

## Connect iCloud Calendar

You need the email address for your Apple Account and an **app-specific
password**. Do not enter your normal Apple Account password into Yaad.

1. Make sure [two-factor authentication is enabled for your Apple
   Account](https://support.apple.com/en-gb/102660). Apple requires it before
   app-specific passwords can be created.
2. Sign in at [account.apple.com](https://account.apple.com/).
3. Open **Sign-In and Security**, then select **App-Specific Passwords**.
4. Choose **Generate an app-specific password** and follow Apple's prompts.
   A label such as `Yaad e Khuda` makes it easy to identify later.
5. Copy the generated password. Apple only shows it once.
6. Return to Yaad. Under **iCloud Calendar**, enter your Apple Account email
   address and paste the app-specific password.
7. Select **Connect iCloud**. Yaad checks the credentials before saving them.

Yaad creates a calendar named `Prayer Reminders` when the connection succeeds,
or reuses one with that name if it already exists. If iCloud refuses calendar
creation, create a calendar called `Prayer Reminders` yourself in Apple's
Calendar app or at [iCloud Calendar](https://www.icloud.com/calendar/), then
connect again.

### iCloud troubleshooting

- **No “App-Specific Passwords” option:** confirm that two-factor
  authentication is enabled for the same Apple Account.
- **Connection is rejected:** generate a fresh app-specific password and check
  that the Apple Account email and password were pasted without extra spaces.
- **You changed your Apple Account password:** Apple revokes app-specific
  passwords after a password reset or change. Generate a new one and update
  the iCloud connection in Yaad.

For Apple's current instructions, see [Sign in to apps with app-specific
passwords](https://support.apple.com/en-us/102654).

## Connect Google Calendar

Google Calendar uses OAuth instead of an app-specific password. Before
connecting Yaad, create a Google Cloud OAuth client for the address where you
open Yaad.

### 1. Decide the redirect URI

The redirect URI is the address Google returns to after you approve access. It
must match the address in your browser exactly, including `http`/`https`, host,
port, and path.

Use your Yaad address followed by `/api/google/oauth/callback`. Common local
examples are:

| How Yaad is running | Redirect URI |
| --- | --- |
| `yaad serve` at `http://localhost:8000` | `http://localhost:8000/api/google/oauth/callback` |
| Docker Compose frontend | `http://localhost:8180/api/google/oauth/callback` |
| `yaad serve` opened at `http://127.0.0.1:8000` | `http://127.0.0.1:8000/api/google/oauth/callback` |
| Your HTTPS domain | `https://your-domain.example/api/google/oauth/callback` |

If you use more than one address, register each corresponding redirect URI on
the same OAuth client.

### 2. Create Google Cloud credentials

1. Go to the [Google Cloud console](https://console.cloud.google.com/) and
   create a project, or select an existing project.
2. Open **APIs & Services** → **Library**, search for **Google Calendar API**,
   and enable it.
3. Open **APIs & Services** → **OAuth consent screen**. Complete the required
   app information and choose the appropriate audience. If the app remains in
   testing, add the Google account you plan to connect as a test user.
4. Open **APIs & Services** → **Credentials** → **Create credentials** →
   **OAuth client ID**.
5. Choose **Web application** as the application type.
6. Under **Authorized redirect URIs**, add the exact URI you decided in step 1.
7. Create the client, then copy its **Client ID** and **Client secret**.

Google's [OAuth credential guide](https://developers.google.com/workspace/guides/create-credentials)
has current screenshots and Console terminology if its interface differs from
these steps.

### 3. Authorize Yaad

1. Return to Yaad and enter the **Client ID** and **Client Secret** under
   **Google Calendar**.
2. Select **Connect Google Calendar**.
3. In the Google window, sign in to the account whose calendar should receive
   the prayer reminders.
4. Review the requested Calendar permission and select **Allow**.
5. Google redirects you back to Yaad. A **Connected** status confirms the
   connection.

Yaad creates or reuses a calendar named `Prayer Reminders` in that Google
account. It stores the refresh token returned by Google so daily syncs can run
without asking you to approve access each day.

### Google troubleshooting

- **“Redirect URI mismatch”:** compare the full address in the browser with
  the authorized redirect URI in Google Cloud. `localhost` and `127.0.0.1` are
  different values.
- **Google says the app is unavailable to you:** if the OAuth consent screen is
  in testing, add the Google account under its **Test users** section.
- **No refresh token is returned:** remove Yaad from
  [Google Account permissions](https://myaccount.google.com/permissions), then
  select **Connect Google Calendar** again and complete consent.
- **You move Yaad to another address:** add that address's callback URI to the
  OAuth client before reconnecting.

## After connecting

Once at least one calendar is connected, select **Continue** in Yaad, enter
your mosque's Mawaqit slug, and finish onboarding. You can add, update, or
disconnect a calendar later from **Settings**.
