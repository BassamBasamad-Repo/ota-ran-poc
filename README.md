# OTA Update POC

React Native / Expo proof-of-concept for over-the-air (OTA) updates using EAS Update.
Demonstrates that JavaScript-only changes can be delivered to installed apps in seconds,
with no rebuild and no store release.

**Stack:** Expo SDK 58 · React Native 0.88 · expo-updates 58 · EAS CLI 27 · TypeScript

---

## How OTA updates work

```
Push commit
    └─ GitHub Actions
         ├─ typecheck (tsc --noEmit)
         ├─ unit tests (npm test)
         └─ [green] ──► EAS Update published to preview channel
                              └─ Phone polls expo.dev ──► downloads JS bundle ──► restarts
```

An update only reaches a device if the **runtime fingerprint** of the installed APK matches
the update. Changes to native code (new packages, `app.json` native fields) produce a new
fingerprint and require a new APK build — OTA alone is not enough.

The APK on the demo phones has runtime fingerprint `73cd2156…` (built from `demo-runtime-b`).
**Publishing from `master` targets a different runtime and will not reach those phones.**

---

## CI/CD pipeline

Workflow file: `.github/workflows/eas-update.yml`

| Trigger | Branch |
|---|---|
| `push` | `master` |
| `workflow_dispatch` | any |

### Jobs

**`test`** — always runs first
- `npm ci`
- `npx tsc --noEmit`
- `npm test`

**`publish`** — runs only if `test` passes, then waits for a reviewer to approve
in the `production-approval` environment before publishing

```
eas update --channel preview --environment preview --platform android --message "<commit msg>"
```

The commit message is passed through an env variable (not inlined in the shell
command) to prevent script injection.

---

## Live demo script

### Good push → phones update

1. On `master`, make a visible JS change (e.g. change `UI_LABEL` or a colour in `App.tsx`)
2. `git push origin master`
3. GitHub Actions → **Actions** tab → watch `test` pass → `publish` pauses for approval
4. Approve in the **production-approval** environment gate
5. `publish` completes → open the app on a demo phone → tap **Check for update** → banner changes

### Bad push → blocked

1. On `master`, introduce the typo: change `src/premium.ts` line 19 to `return 12.5`
2. `git push origin master`
3. GitHub Actions → `test` fails at `npm test` (12.5 ≠ 1.25) → `publish` never starts
4. No update is published — phones are unaffected

### Rollback via expo.dev

If a bad update is accidentally published:

1. Go to **expo.dev → Projects → ota-poc → Updates**
2. Find the previous good update group
3. Click **⋯ → Re-publish** (or "Republish") — this re-points the `preview` channel pointer
   to the old bundle with no code change required
4. Phones pick it up on the next check-in

---

## Local development

```bash
npm ci                          # install dependencies
npm test                        # run unit tests
npx tsc --noEmit                # typecheck
npx expo start                  # start Metro bundler (Expo Go / dev build)
```

To publish manually (requires Expo login):

```bash
npx eas-cli@27.10.0 update \
  --channel preview \
  --environment preview \
  --platform android \
  --message "my message"
```

See `docs/Publish-from-Laptop-Guide.md` (on the `master` branch) for the full
step-by-step guide for colleagues without EAS CLI installed.

---

## Branch map

| Branch | Runtime | Purpose |
|---|---|---|
| `master` | A | Stable baseline; source for the laptop publishing guide |
| `demo-runtime-b` | B (`73cd2156`) | CI/CD demo — this is what the demo phones run |
| `release/1.0-hotfix` | A | Hotfix workflow demo |
| `native-v4` | B | Native dependency bump reference |
| `bad-release-v3` | A | Simulated bad release reference |

---

## Repo

**https://github.com/BassamBasamad-Repo/ota-ran-poc** · Personal account only.
Do not use Bupa credentials or copy Bupa code into this project.
