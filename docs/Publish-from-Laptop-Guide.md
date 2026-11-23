# Guide: Publish an OTA Update from Your Laptop

This guide covers how to change the POC app and send the change to your phone over the air, with no rebuild and no store release.
It takes about 20 minutes the first time and about 2 minutes after that.

> **Use a personal laptop**, or one where you're allowed to install Node.js and reach `expo.dev` and `registry.npmjs.org`.
> This is a personal POC account. Don't use Bupa credentials, and don't copy Bupa code into this project.

---

## 0. What you need

| Item | How to get it |
|---|---|
| **Node.js 22 LTS** | https://nodejs.org → download the **LTS** installer → Next, Next, Finish |
| **Git** | https://git-scm.com/downloads (Windows: keep the defaults) |
| **The project** | Access to https://github.com/BassamBasamad-Repo/ota-ran-poc (accept the collaborator invite) |
| **Your Expo login** | Your own expo.dev account, invited as a member of the `biso2026expos-team` team (accept the email invite first) |
| **A code editor** (optional) | VS Code: https://code.visualstudio.com |

Check the installation in a **new** terminal (Windows: *Command Prompt*; Mac: *Terminal*):

```bash
node -v
```
```bash
git --version
```

`node -v` should show `v22.x` or `v20.x` or later.

> **Windows tip:** use **Command Prompt (cmd)**, not PowerShell. PowerShell sometimes blocks `npx` with an "execution policy" error.

---

## 1. Get the project

Clone the repo into a simple folder, for example:

- Windows: `C:\dev\ota-poc`
- Mac: `~/dev/ota-poc`

```bash
git clone https://github.com/BassamBasamad-Repo/ota-ran-poc.git C:\dev\ota-poc
```

(Mac: `git clone https://github.com/BassamBasamad-Repo/ota-ran-poc.git ~/dev/ota-poc`)

Then go into it:

```bash
cd C:\dev\ota-poc
```

(Mac: `cd ~/dev/ota-poc`)

Already cloned? Get the latest with `git pull` instead.

---

## 2. Install the project's libraries (once)

```bash
npm ci
```

This reads `package-lock.json` and installs the exact versions used in the POC (React Native, Expo SDK 58, expo-updates, …) into a `node_modules` folder. It takes 1–3 minutes.
The warnings that say `npm warn deprecated` are harmless.

---

## 3. Log in to Expo (once per laptop)

```bash
npx eas-cli@27.10.0 login
```

Enter your expo.dev username and password. Then check it worked:

```bash
npx eas-cli@27.10.0 whoami
```

✅ It should show your username, with `biso2026expos-team` listed under **Accounts**. If the team is missing, accept the invite at expo.dev first.

> `npx eas-cli@27.10.0` runs Expo's command-line tool (EAS CLI) without installing it permanently. The version is pinned to the one used in the POC.

---

## 4. ⚠️ Switch to the code that matches your phone (most important step)

Your phone must have the **demo APK built from `master`**. Older APKs (runtime A or B) have a different fingerprint.
**If you publish code whose fingerprint doesn't match the phone's APK, the phone will say "Up to date" and ignore the update.** That's the compatibility protection we proved in the POC.

```bash
git switch master
```

Then check that the native fingerprint matches your phone:

```bash
npx expo-updates fingerprint:generate --platform android
```

Look for `"hash"` in the output:

| Hash starts with | Matches | OK to publish for your phone? |
|---|---|---|
| **`dfdfce9f`** | Demo APK built from `master` (current) | ✅ Yes |
| `73cd2156` | Old runtime B APK (before the project moved to `biso2026expos-team`) | ❌ Install the new APK |
| `c07c2603` | Old runtime A APK | ❌ Install the new APK |

> If the hash is different from all of these, a native change (new package or `app.json` native field) was made: a new APK must be built before OTA updates will reach the phone.

Branches in the project:

| Branch | Runtime | Content |
|---|---|---|
| `master` | Current | Demo branch: publish from here |
| `release/1.0-hotfix` | A | v2.1 hotfix |
| `native-v4` | B | v5 teal (with haptics) |
| `demo-runtime-b` | B | Earlier demo state, merged into `master` |

---

## 5. Make a change

Open the project folder in VS Code (or any text editor).

**a) Change the UI:** in `App.tsx`, near the top:

```ts
const UI_LABEL = 'v8 published from my laptop';
const ACCENT = '#0B5FA5';   // banner colour (hex)
```

**b) Change the business rule (optional):** in `src/premium.ts`, the 30–49 age factor. The correct value is:

```ts
if (age < 50) return 1.25;
```

Save both files.

---

## 6. Test before publishing (the "quality gate")

```bash
npm test
```
```bash
npx tsc --noEmit
```

✅ `npm test` must show `# fail 0`, and `tsc` must print nothing.

> **Reminder from the POC:** `eas update` does **not** run tests. It publishes whatever you give it. There is no CI pipeline in this demo, so it's up to you.

---

## 7. Save the change in git (traceability)

```bash
git add -A
```
```bash
git commit -m "v8: published from laptop"
```

The first time, git may ask who you are. Run these once with your own details:

```bash
git config --global user.name "Your Name"
```
```bash
git config --global user.email "you@example.com"
```

Expo records the git commit with each update, so every OTA update traces back to the exact code it came from.

---

## 8. Publish the OTA update

```bash
npx eas-cli@27.10.0 update --channel preview --message "v8: published from laptop" --environment preview --platform android
```

What happens:
1. Expo bundles your JavaScript locally (about 30 seconds)
2. It uploads the bundle to Expo
3. It publishes to the `preview` channel for **runtime 73cd2156**

✅ The output ends with **Published!** and shows the **Runtime version**, **Update group ID** and **Android update ID**. Note the group ID, which you need if you want to roll back.

---

## 9. Check it on your phone

1. Close the app fully (swipe it away), then reopen it.
2. Wait 2–3 seconds for **Restart to apply**, then tap it. Alternatively, close and reopen the app once more.
3. ✅ You see the new banner, and **Update ID** matches the *Android update ID* from step 8.

---

## 10. Roll back (if needed)

**Option A: from the website, no laptop needed**
expo.dev → Projects → `ota-poc` → Updates → open the previous good update → **Republish**.

**Option B: from the laptop**

Roll back the latest update (re-publishes the one before it):

```bash
npx eas-cli@27.10.0 update:rollback <UPDATE-GROUP-ID> --platform android --message "Rollback" --non-interactive
```

Republish any earlier update by its group ID:

```bash
npx eas-cli@27.10.0 update:republish --group <UPDATE-GROUP-ID> --platform android --message "Republish"
```

Go back to the code built into the APK:

```bash
npx eas-cli@27.10.0 update:roll-back-to-embedded --channel preview --runtime-version 73cd2156555b7731342bcba099e79150d31e7d0e --platform android --message "Back to built-in"
```

List recent updates (to find group IDs):

```bash
npx eas-cli@27.10.0 update:list --branch preview
```

---

## 11. Troubleshooting

| Problem | Cause → Fix |
|---|---|
| Phone says **"Up to date"** after publishing | Wrong branch/runtime. Check step 4: the hash must start with `73cd2156`. |
| `npx` blocked / "execution policy" (Windows) | Use **Command Prompt** instead of PowerShell. |
| `npm ci` fails with SSL / proxy / timeout errors | Corporate network or proxy. Use a personal network or laptop, or ask IT to allow `registry.npmjs.org`. |
| `Not logged in` / 401 | Run `npx eas-cli@27.10.0 login` again. |
| `fingerprint` hash is different from both values above | You changed native things (added a package with native code, or edited `app.json` native settings). That **needs a new APK build**, not an OTA update. Undo the change (`git checkout -- .`) or ask for a new build. |
| `npm test` fails | Your business-rule change broke an expected value. Fix the code or update `src/premium.test.ts` deliberately. |

---

## 12. When the POC is finished

Log out of the CLI:

```bash
npx eas-cli@27.10.0 logout
```

Then **revoke the access token** at https://expo.dev/settings/access-tokens (the `ota-poc` token created for the cloud session).

---

### Cheat sheet (after the first setup)

```bash
cd C:\dev\ota-poc
```
```bash
git switch master
```
```bash
npm test
```
```bash
git commit -am "my change"
```
```bash
npx eas-cli@27.10.0 update --channel preview --message "my change" --environment preview --platform android
```
