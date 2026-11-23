# OTA Update POC

React Native / Expo proof-of-concept for over-the-air (OTA) updates using EAS Update.
Demonstrates that JavaScript-only changes can be delivered to installed apps in seconds,
with no rebuild and no store release.

**Stack:** Expo SDK 58 · React Native 0.88 · expo-updates 58 · EAS CLI 27 · TypeScript

---

## How OTA updates work

```
Make a JS change
    └─ Check locally: npx tsc --noEmit && npm test
         └─ [green] ──► eas update (from laptop or expo.dev) ──► preview channel
                              └─ Phone polls expo.dev ──► downloads JS bundle ──► restarts
```

An update only reaches a device if the **runtime fingerprint** of the installed APK matches
the update. Changes to native code (new packages, `app.json` native fields) produce a new
fingerprint and require a new APK build. OTA alone is not enough.

The demo phones must run an APK **built from `master`** (after the project moved to the
`biso2026expos-team` Expo account, which changed the fingerprint). Older APKs will not
receive updates published from `master`.

Publishing is **manual**. The GitHub Actions workflow was removed on 2026-11-23.

---

## Build the demo APK (once per native change)

```bash
npx eas-cli@latest build --profile preview --platform android
```

Install the APK from the build page on each demo phone.

---

## Publish an update

Requires `npx eas-cli@latest login` with an account that is a member of `biso2026expos-team`.

```bash
npx tsc --noEmit && npm test     # check first: nothing stops a bad publish automatically
npx eas-cli@latest update \
  --channel preview \
  --environment preview \
  --platform android \
  --message "my message"
```

---

## Live demo script

### Good change → phones update

1. On `master`, make a visible JS change (e.g. change `UI_LABEL` or a colour in `App.tsx`)
2. Run `npx tsc --noEmit && npm test`. It should pass.
3. Publish with the `eas update` command above
4. Open the app on a demo phone → tap **Check for update** → banner changes

### Bad change → caught before publishing

1. On `master`, introduce the typo: change `src/premium.ts` line 19 to `return 12.5`
2. Run `npm test`. It fails (12.5 ≠ 1.25), so do not publish.
3. Revert the change. Phones are unaffected.

### Rollback via expo.dev

If a bad update is accidentally published:

1. Go to **expo.dev → biso2026expos-team → ota-poc → Updates**
2. Find the previous good update group
3. Click **⋯ → Re-publish** (or "Republish"). This re-points the `preview` channel
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

See `docs/Publish-from-Laptop-Guide.md` for the full step-by-step guide for colleagues
without EAS CLI installed.

---

## Branch map

| Branch | Runtime | Purpose |
|---|---|---|
| `master` | Current | Demo branch: build the demo APK and publish updates from here |
| `demo-runtime-b` | B (`73cd2156`) | Earlier CI/CD demo, merged into `master` |
| `release/1.0-hotfix` | A | Hotfix workflow demo |
| `native-v4` | B | Native dependency bump reference |
| `bad-release-v3` | A | Simulated bad release reference |

---

## Repo

**https://github.com/BassamBasamad-Repo/ota-ran-poc** · Personal account only.
Do not use Bupa credentials or copy Bupa code into this project.
