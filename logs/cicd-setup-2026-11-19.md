# CI/CD Setup Log — 2026-11-19

**Author:** Bassam Basamad  
**Session:** GitHub Actions + EAS Update pipeline setup  
**Repo:** https://github.com/BassamBasamad-Repo/ota-ran-poc

---

## 1. Project context

This is a personal React Native / Expo proof-of-concept for OTA (over-the-air) updates.
It is **not** connected to any company system. All data is dummy.

| Item | Value |
|---|---|
| Expo project slug | `ota-poc` |
| Expo account (owner) | `biso2026expo` |
| EAS Update channel | `preview` |
| Runtime version policy | `fingerprint` |
| Android demo APK fingerprint | `73cd2156555b7731342bcba099e79150d31e7d0e` |
| EAS CLI version (pinned) | `27.10.0` |
| Expo SDK | `58.0.26` |
| React Native | `0.88.1` |
| expo-updates | `58.0.22` |

---

## 2. Local environment verified (Step 1)

All checks were run against `demo-runtime-b` with the committed bad state
(working tree changes were stashed first, then restored).

| Check | Result |
|---|---|
| `git status` | Clean after stash |
| `npm ci` | ✅ Success |
| `npx tsc --noEmit` | ✅ 0 errors |
| `npm test` | ✅ FAILED as expected — `ageFactor` returns `12.5` in committed state |
| Fingerprint hash | ✅ `73cd2156555b7731342bcba099e79150d31e7d0e` — matches APK |
| Secret scan (files + git history) | ✅ Clean |
| `app.json` projectId | ✅ Public by design — not a secret |

**Test failure detail (expected):**
```
✖ age bands   — 12.5 !== 1.25
✖ premium calculation  — 25000 !== 2500
✔ rejects invalid age
```

---

## 3. GitHub repository (Step 2)

- **Repo:** https://github.com/BassamBasamad-Repo/ota-ran-poc
- **Visibility:** Public (changed from private to allow GitHub Free collaborator features)
- **Account:** `BassamBasamad-Repo` (personal, confirmed)
- **Default branch:** `master`

**Branches pushed:**

| Branch | Runtime | Purpose |
|---|---|---|
| `master` | A | Stable baseline; laptop publishing guide |
| `demo-runtime-b` | B (`73cd2156`) | CI/CD demo — what the demo phones run |
| `release/1.0-hotfix` | A | Hotfix workflow demo |
| `native-v4` | B | Native dependency bump reference |
| `bad-release-v3` | A | Simulated bad release reference |

---

## 4. Expo token (Step 3)

A personal access token named `github-actions-ota-poc` was created on expo.dev:
- Account scope: `biso2026expo` only
- Stored as GitHub Actions secret: `EXPO_TOKEN`
- Secret set via `gh secret set EXPO_TOKEN --repo BassamBasamad-Repo/ota-ran-poc`
  (token was pasted into the hidden CLI prompt — never written to any file or chat)

---

## 5. GitHub Actions workflow (Step 4)

**File:** `.github/workflows/eas-update.yml`

**Triggers:**
- `push` to `demo-runtime-b`
- `workflow_dispatch` (manual)

**Job: `test`** (always runs first)
- Runner: `ubuntu-latest`, Node 22 LTS
- Steps: `npm ci` → `npx tsc --noEmit` → `npm test`
- Failure here blocks `publish` completely

**Job: `publish`** (only if `test` passes)
- Requires approval in the `production-approval` environment before it starts
- Sets up EAS CLI `27.10.0` via `expo/expo-github-action@v9`
- Prints Android fingerprint (`npx expo-updates fingerprint:generate --platform android`)
- Runs:
  ```bash
  eas update \
    --channel preview \
    --environment preview \
    --platform android \
    --message "$COMMIT_MSG" \
    --non-interactive
  ```
- Commit message is passed via env variable `COMMIT_MSG` (not inlined) to prevent shell injection

**Action versions used:**
| Action | Version |
|---|---|
| `actions/checkout` | `v7` (v7.0.1) |
| `actions/setup-node` | `v7` (v7.1.0) |
| `expo/expo-github-action` | `v9` (v9.0.2) |

---

## 6. Production-approval environment (Step 4 addendum)

- Environment name: `production-approval`
- Protection rule: `required_reviewers`
- Required reviewer: `BassamBasamad-Repo` (repo owner)
- Created via GitHub API (`PUT /repos/.../environments/production-approval`)
- Effect: `publish` job pauses after `test` passes and waits for the owner to click
  **Approve** in the GitHub Actions UI before EAS publishes

---

## 7. Fix commit and pipeline validation (Step 5a)

The fix commit restores the branch to a healthy state and proves the pipeline works.

**Changes committed as `fix: restore correct age factor 1.25 and update CI label`:**
- `src/premium.ts` line 19: `return 12.5` → `return 1.25`
- `App.tsx` `UI_LABEL`: `'v7 BAD release: pricing typo (demo)'` → `'v8 published by GitHub Actions'`
- `App.tsx` `ACCENT`: `#C62828` (red) → `#0B5FA5` (blue)

### Fingerprint incident — caused and resolved during this session

**What happened:** An earlier commit added `.env` and `.env.*` to `.gitignore` as a
security measure. The `.gitignore` file is a fingerprint source (`bareGitIgnore` reason
in `expo-updates fingerprint:generate`). This shifted the runtime fingerprint from
`73cd2156` to `f46104db`, meaning the published update would not be delivered to the
demo phones (fingerprint mismatch).

**How it was caught:** `eas update:list` showed the wrong runtime version on the latest
update group immediately after the publish step completed.

**Fix:** The `.gitignore` additions were reverted on `demo-runtime-b` via commit
`04f1562`. The fingerprint was confirmed restored before pushing.

**Lesson:** Any file listed as a fingerprint source (`.gitignore`, `app.json`, native
package files, autolinking config) will change the runtime fingerprint if modified.
Always run `npx expo-updates fingerprint:generate --platform android` after editing
such files and before pushing to a CI branch targeting the demo phones.

---

## 8. Workflow run history

| Run ID | Commit | Result | Notes |
|---|---|---|---|
| `44544521450` | `ci: add GitHub Actions workflow…` | ❌ Failure | `npm test` failed on bad commit — expected and correct |
| `44545053643` | `fix: restore correct age factor…` | ❌ Failure | `publish` failed — `expo/expo-github-action@9` tag does not exist |
| `44545208360` | `fix(ci): correct expo-github-action tag to v9` | ✅ Success | First full green run; published runtime `f46104db` (wrong — .gitignore was still modified) |
| `44545907075` | `revert: remove .gitignore additions…` | ✅ Success | Published runtime `73cd2156` ✅ correct |
| `44546576619` | `ci: add production-approval environment…` | ✅ Success | First run with approval gate; manually approved; published runtime `73cd2156` ✅ |
| `44547128698` | `docs: add README…` | ⏳ Waiting | Paused at `production-approval` gate (pending approval as of session end) |

---

## 9. Collaborator (Step 6)

- GitHub username: `a-asaad`
- Access level: `write`
- Status: **Invitation pending** — `a-asaad` must accept via email or
  https://github.com/BassamBasamad-Repo/ota-ran-poc/invitations

---

## 10. Files added or modified this session

| File | Branch(es) | Change |
|---|---|---|
| `.github/workflows/eas-update.yml` | `demo-runtime-b` | Created — CI/CD workflow |
| `src/premium.ts` | `demo-runtime-b` | Fixed `ageFactor` return 12.5 → 1.25 |
| `App.tsx` | `demo-runtime-b` | UI_LABEL and ACCENT updated for CI demo |
| `README.md` | `demo-runtime-b` | Created — project overview + CI/CD demo script |
| `.gitignore` | `master`, `demo-runtime-b` | Added `.env` / `.env.*` on master only; reverted on `demo-runtime-b` (fingerprint conflict) |

---

## 11. Current live state on the preview channel

| Update group | Runtime | Message | Deliverable to phones? |
|---|---|---|---|
| `b0f46255` (latest) | `73cd2156` | `ci: add production-approval environment gate…` | ✅ Yes |
| `124c317c` | `73cd2156` | `revert: remove .gitignore additions…` | ✅ Yes (superseded) |
| `3192ceb9` | `f46104db` | `fix(ci): correct expo-github-action tag to v9` | ❌ No — wrong fingerprint |
| `3cf5f4e7` | `73cd2156` | `v8: published from laptop` | ✅ Yes (superseded) |

---

## 12. Things still to do / to be aware of

| Item | Status |
|---|---|
| `a-asaad` accept collaborator invite | ⏳ Waiting on colleague |
| Approve pending run `44547128698` (README commit) | ⏳ Manual approval needed |
| Live demo bad push (typo 12.5) — to be done during the demo, not before | 📋 Planned |
| `.gitignore` only has `.env*.local` on `demo-runtime-b` (`.env` / `.env.*` were reverted to protect fingerprint) | ⚠️ Known trade-off |
| Publishing from `master` targets a different runtime — will NOT reach the demo phones | ⚠️ Reminder |

---

## 13. Quick reference — demo day commands

```bash
# Check pipeline status
gh run list --repo BassamBasamad-Repo/ota-ran-poc --limit 5

# Approve a pending deployment
gh api repos/BassamBasamad-Repo/ota-ran-poc/actions/runs/<RUN_ID>/pending_deployments \
  --method POST \
  --input - <<'EOF'
{"environment_ids":[27872494557],"state":"approved","comment":"Approved"}
EOF

# Check latest EAS updates
npx eas-cli@27.10.0 update:list --branch preview --limit 3 --non-interactive

# Verify fingerprint locally
npx expo-updates fingerprint:generate --platform android
```

**Environment ID for `production-approval`:** `27872494557`
