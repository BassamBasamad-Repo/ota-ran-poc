# POC Report: React Native OTA Updates (Expo EAS Update)

| | |
|---|---|
| **Prepared by** | Bassam Basamad, Technical Architect |
| **Requested by** | Waseem Ahmed, Director – Application & Software Engineering |
| **Date** | 18 November 2026 |
| **Status** | Draft for review (Abdullah Asaad) |
| **Scope** | Standalone sample app, dummy data, personal Expo account. No Bupa code, systems, data or credentials. Android only. No App Store / Play Store publishing. |

---

## 1. Executive summary

**Result: the POC was successful.** On a physical Android phone we showed the full lifecycle: **deploy → OTA update → bad release → rollback → native change → hotfix**. JavaScript, UI and business-logic changes reached the installed app **within minutes, with no rebuild and no store release**. Rollback took **seconds**.

**Most important finding:** Expo **blocks** an OTA update that needs native code the installed app does not have (evidence #6). This is safer than the OutSystems 11 model, where new code reaches old native shells and developers must guard against it at runtime.

**Recommendation: conditional GO.** The technology is suitable for our production mobile app, **provided that** the controls in section 7 are put in place. The main open decision is **hosting and compliance**: either **Expo Enterprise** (managed, US-hosted SaaS, subject to a data-residency and legal review) or a **self-hosted update server** on Bupa infrastructure, using the open `expo-updates` protocol.

---

## 2. What was built

| Item | Detail |
|---|---|
| Stack | Expo SDK 58.0.26, React Native 0.88.1, `expo-updates` 58.0.22, EAS CLI 27.10.0 (versions checked against the official docs on the day) |
| App | One screen: dummy premium calculator (plan × age factor × smoker loading) with unit tests, plus an "About this build" panel showing channel, runtime version, update ID, and whether the embedded bundle or an OTA update is running |
| Build | Expo cloud build (EAS Build), signed **APK** installed directly from expo.dev. Signing key generated and stored by Expo. |
| Update channel | `preview` |
| Compatibility policy | `runtimeVersion: { policy: "fingerprint" }`: a hash of all native inputs, recalculated automatically |

---

## 3. Evidence (device screenshots in `/evidence`)

| # | Scenario | Runtime | Update ID | Result |
|---|---|---|---|---|
| 1 | APK v1 installed | A `c07c2603` | `2cd09f30…` (embedded) | ✅ Blue v1, Silver 35 = **2,600** |
| 2 | **OTA v2**: UI + business rule (age factor 1.3 → 1.25) | A | `01a1ee87…` | ✅ Green v2, **2,500**, no rebuild |
| 3 | **Bad release v3** (simulated pricing typo 12.5) | A | `01a1ee8b…` | ⚠️ Red v3, **25,000**. Reached the phone automatically on relaunch. |
| 4 | **Rollback** to the previous good update (`eas update:rollback`) | A | `01a1ee90…` | ✅ Back to v2 within seconds; same tested bundle republished |
| 5 | **Roll back to embedded** (`eas update:roll-back-to-embedded`) | A | `2cd09f30…` | ✅ Back to the original APK code (same ID as #1) |
| 6 | **Native dependency added** (`expo-haptics`), OTA v4 published | B `73cd2156` | `01a1eec6…` | ✅ **Old APK did NOT receive it** ("Up to date"). No crash. |
| 7 | **Urgent hotfix for store users**, published from the release branch | A | `01a1eee8…` | ✅ Old APK received the hotfix while a newer native version existed |
| 8 | **New APK** with the native module (installed as an upgrade, same key) | B | `b7c489c3…` (embedded) | ✅ Purple v4, vibration works |
| 9 | **OTA v5 on the new native runtime** | B | `01a1eeec…` | ✅ Teal v5; native feature still works |

The full publish history (who, when, which runtime, which git commit) is exported in `evidence/eas-update-history.json`.

**Timings observed:** a cloud build took about 13 minutes (free low-priority queue). Publishing an OTA took about 1 minute. A rollback published in seconds. The device applies an update on its next launch, or immediately when prompted.

---

## 4. What can and cannot be delivered OTA

| ✅ OTA (no store release) | ❌ Needs a new build and a store release |
|---|---|
| UI, screens, styling, text, translations | Adding or upgrading a native module or SDK (camera, biometrics, payments, push, analytics SDKs…) |
| Business logic and validation rules in JavaScript | Expo SDK / React Native upgrades |
| API calls, endpoints, feature flags in JS | Permissions, app icon, splash screen, deep-link or manifest changes |
| Images and assets bundled with JS | Native config (Android/iOS project settings), signing |

**Control:** the `fingerprint` runtime policy detects native changes **automatically**. Proven: a JavaScript-only change kept fingerprint A, while adding `expo-haptics` produced fingerprint B. An update is only ever served to builds with the **same** fingerprint.

**Store policies:** both Apple and Google allow interpreted JavaScript updates that do not change the app's primary purpose. *Confirm with Compliance before production.*

---

## 5. Update behaviour (how users receive updates)

| Setting | Default | Meaning |
|---|---|---|
| `checkAutomatically` | `ON_LOAD` | Checks on every cold start (not on screen navigation or resume) |
| `fallbackToCacheTimeout` | `0` | The app opens immediately; the update downloads in the background |
| Apply | Next cold start | Or immediately via `Updates.reloadAsync()`. The POC used a **"Restart to apply"** prompt. |

Unlike OutSystems, **the update policy is ours to design**. Recommended standard: check on cold start **and** on app resume; **prompt** the user (never reload in the middle of a form); use a short `fallbackToCacheTimeout` or a blocking flow only for critical fixes.

---

## 6. Operations

### 6.1 Rollback and failure recovery
- **Rollback to the previous update**: `eas update:rollback` (proven, #4). **Rollback to embedded**: `eas update:roll-back-to-embedded` (proven, #5). Both are also available in the Expo dashboard.
- **Automatic recovery** (built in): if an update crashes **before its first screen renders** on its first launch, the device marks it as failed, checks for a fix for about 5 seconds, then falls back to the last update that worked. After the first render, it only fixes forward.
- **Limits (from the Expo docs):** errors more than 10 s after the first render are not caught, and a rollback is unsafe if the bad update changed locally stored data. Persistent data and schema changes must stay backward-compatible. *(The crash-recovery path itself was not demonstrated.)*

### 6.2 Staged / canary rollout
- **Per update:** `eas update --rollout-percentage=10`, raised step by step with `eas update:edit`, reverted with `eas update:revert-update-rollout`.
- **By branch:** `eas channel:rollout` sends a share of a channel's users to a new branch.
- Only one active rollout per branch and runtime. *(Documented; not measurable with one device.)*

### 6.3 Versioning and release branching
- **Lesson from #7:** an urgent fix must be published **from the git release branch that matches the users' runtime**, not from `main` while `main` contains unreleased native changes. Otherwise store users will not receive it.
- Standard: tag every store release (`release/x.y`). Maintain one hotfix line per supported runtime.
- **Force upgrade:** a Spring Boot endpoint returns the minimum supported app version; the app shows "Please update from the store" below it. (OutSystems teams need a similar Forge component; in Expo we build it once as a standard.)

### 6.4 Security, signing, access and audit

| Control | Expo capability | Plan required |
|---|---|---|
| End-to-end **update code signing** (the device verifies a Bupa-held key) | `expo-updates` code signing | **Production or Enterprise** *(not demonstrated: free plan)* |
| **Roles** | Owner, Admin, **Release Manager**, Developer, Runner, Viewer | Organization account |
| **Protected channels** | `eas channel:protect production`: only Release Manager and above can publish, roll back or change rollouts on production | Organization account |
| **CI identity** | Robot users with an access token and a scoped role; no personal tokens in CI | Organization account |
| **SSO** | Corporate identity provider sign-in | Production and above |
| **Audit logs** | Cannot be changed or deleted; kept 1.5 years | **Enterprise only** |
| Traceability | Every update records its git commit, message and author (`eas-update-history.json`) | All |

### 6.5 CI/CD (target design; not built in this POC)
1. PR → lint, typecheck, **unit tests** (the POC tests caught the v3 typo, but `eas update` does not run tests itself), security scan, optional preview update on a PR channel.
2. Merge → publish to `staging`, then QA sign-off.
3. **Approval gate** → a CI robot (Release Manager role) publishes to `production` with `--rollout-percentage` 5 → 25 → 100, watching crash and error metrics between steps.
4. A hotfix pipeline publishes from `release/x.y` tags.
5. Nobody publishes to production from a laptop. Enforced by protected channels plus robot-only credentials.

Works with Expo Workflows, GitHub Actions or Azure DevOps (EAS CLI with `EXPO_TOKEN`).

### 6.6 Monitoring
- Expo dashboard: update adoption per update and runtime, deployments and update download performance (Expo Insights).
- Add crash and error reporting (e.g. Sentry), tagged with the update ID, so a bad update is detected within minutes and triggers a rollback.

### 6.7 Operational effort (estimate)
- One-off: org setup, CI pipelines, signing keys, force-upgrade endpoint, update-policy standard, runbooks.
- Ongoing: release management (a Release Manager role), maintaining release branches for supported runtimes, monitoring rollouts. Self-hosting adds running and securing an update server and CDN (high availability, key management, patching).

---

## 7. Comparison with OutSystems 11 mobile updates

| Aspect | OutSystems 11 | React Native + Expo EAS Update |
|---|---|---|
| JS/UI/logic updates | Automatic on publish | Explicit `eas update` per channel |
| **Native/plugin change** | New code reaches **all** installed apps; old shells need defensive `Check…Plugin` logic and a forced store update | **Blocked automatically** by fingerprint: old apps never receive incompatible code (#6) |
| Old-version users | Get the latest code (risk of broken features) | Stay on the last compatible version (risk of fragmentation; fixed with release-branch hotfixes #7 and force upgrade) |
| When updates apply | Platform-managed at startup/resume | Configurable policy (silent, prompt, forced) |
| Rollback | Republish an earlier version via LifeTime | **One command, seconds**; also back to the embedded bundle |
| Staged / canary rollout | Not native to OTA (all users at once) | **Built in** (% per update, or by branch) |
| Environments | LifeTime environments (Dev/Test/Prod) | Channels and branches; flexible but must be governed |
| Signing / integrity | Platform-managed | Code signing (paid plans) or self-hosted |
| Audit | LifeTime deployment history | Audit logs (Enterprise) plus CI logs |
| Hosting | Bupa's OutSystems infrastructure | Expo SaaS (US) **or** self-hosted |
| Governance effort | Low (opinionated platform) | Higher (we design and enforce the policy) |

*The OutSystems behaviour is based on our team's experience and OutSystems community and Forge documentation. Validate it against the official "Mobile App Update Scenarios" documentation.*

**In short:** OutSystems favours **reach** (everyone gets the update); Expo favours **safety and control** (only compatible apps get it, staged, rollback in seconds). The cost of Expo's model is more release governance.

---

## 8. Enterprise options and alternatives

| Option | Pros | Cons |
|---|---|---|
| **Expo EAS Update, Enterprise plan** (recommended starting point) | Mature, integrated with builds; rollouts, protected channels, SSO, audit logs, code signing, support/SLA | US-hosted SaaS → **data residency and legal review required**; MAU-based cost (quote needed) |
| **Self-hosted `expo-updates` protocol server** | Bupa-hosted; full data control; same client library and behaviour | We build and run the server, CDN, signing and HA; lose the Expo dashboard and insights |
| Open-source self-hosted tools (e.g. Hot Updater, maintained CodePush-server forks) | Self-hosted, low licence cost | Smaller communities, maturity varies (vendor claims unverified); due diligence needed |
| Microsoft App Center CodePush | — | **Retired 31 March 2025**; not an option |

---

## 9. Limitations and gaps of this POC

- **Android only**; iOS not tested (Apple adds TestFlight / App Store review for native releases).
- **Code signing, audit logs and SSO not demonstrated** (paid plans).
- **Staged rollout and automatic crash recovery** documented, not demonstrated (single device).
- **CI/CD not built**; publishing was manual from a workstation.
- No Spring Boot backend, authentication, offline data or push notifications in scope.
- One device and one test user. No performance, bandwidth or large-bundle testing.
- **Data residency and privacy of Expo's service not assessed** (needs Legal, Security and Compliance).

---

## 10. Recommendation and required controls

**Conditional GO.** Adopt Expo EAS Update for the React Native app, subject to:

1. **Hosting decision**: Expo Enterprise (after data-residency, PDPL and vendor security review) **or** a self-hosted `expo-updates` server.
2. **Organization account with SSO**, least-privilege roles, a **protected `production` channel**, and Release Manager approval.
3. **CI-only publishing** with a robot user: tests, security scan and approval gate. No personal tokens.
4. **End-to-end update code signing** with a Bupa-held key.
5. **`fingerprint` runtime policy**, **release branches per store version**, and a hotfix pipeline.
6. **Staged rollouts** (5 → 25 → 100%) with crash and error monitoring tagged by update ID, plus a rollback runbook.
7. **Force-upgrade endpoint** (Spring Boot) and a standard update-UX policy.
8. **Audit trail**: Expo audit logs (Enterprise) or CI and SIEM logging.

**Proposed next steps:**
- Request an Expo Enterprise quote and a data-hosting statement.
- Run a 2–3 week pilot with an Expo organization account covering iOS, code signing, a CI pipeline and staged rollout.
- Prototype a self-hosted update server for comparison.
