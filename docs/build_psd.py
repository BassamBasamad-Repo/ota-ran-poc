"""Fill the Bupa PSD template with the RN OTA POC content.

Usage: python3 -I build_psd.py <template_unpacked_dir> <out_dir> <evidence_dir> <diag_dir> [pages.json]
Copies the unpacked template to out_dir and rewrites document.xml (body), header4.xml,
rels, content types and settings. Styles, cover, logo, headers/footers are preserved.
"""
import json, os, re, shutil, sys
from xml.sax.saxutils import escape
from PIL import Image

TPL, OUT, EVID, DIAG = sys.argv[1:5]
PAGES = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}

BLUE = "2B5EAB"
FULL_W = 9026
EMU_PER_IN = 914400

if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(TPL, OUT)
W = os.path.join(OUT, "word")
doc = open(os.path.join(W, "document.xml"), encoding="utf8").read()

# ---------------------------------------------------------------- helpers
_pid = [0x10000000]


def pid():
    _pid[0] += 1
    return f'w14:paraId="{_pid[0]:08X}" w14:textId="77777777"'


def runs(text, base_rpr=""):
    """Simple inline markup: **bold**."""
    out = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        rpr = base_rpr + ("<w:b/><w:bCs/>" if i % 2 else "")
        rpr_xml = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
        out.append(f'<w:r>{rpr_xml}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def para(text, after=120, before=0, rpr="", jc=None, keep_next=False):
    jc_xml = f'<w:jc w:val="{jc}"/>' if jc else ""
    kn = "<w:keepNext/>" if keep_next else ""
    return (f'<w:p {pid()}><w:pPr>{kn}<w:spacing w:before="{before}" w:after="{after}"/>{jc_xml}</w:pPr>'
            f"{runs(text, rpr)}</w:p>")


def note(text):
    return para(text, rpr='<w:i/><w:iCs/><w:color w:val="666666"/><w:sz w:val="18"/><w:szCs w:val="18"/>')


def bullet(text):
    return (f'<w:p {pid()}><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
            f'<w:spacing w:after="60"/><w:ind w:left="360" w:hanging="270"/></w:pPr>{runs(text)}</w:p>')


def divider():
    return (f'<w:p {pid()}><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="{BLUE}"/>'
            f'</w:pBdr><w:spacing w:before="200" w:after="200"/></w:pPr></w:p>')


def page_break():
    return f'<w:p {pid()}><w:r><w:br w:type="page"/></w:r></w:p>'


TOC = []  # (level, text, bookmark)
_bm = [100]


def heading(text, level=1):
    _bm[0] += 1
    name = f"_Toc9{_bm[0]:07d}"
    TOC.append((level, text, name))
    style = "heading10" if level == 1 else "heading20"
    return (f'<w:p {pid()}><w:pPr><w:pStyle w:val="{style}"/><w:keepNext/></w:pPr>'
            f'<w:bookmarkStart w:id="{_bm[0]}" w:name="{name}"/><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
            f'<w:bookmarkEnd w:id="{_bm[0]}"/></w:p>')


BORD = ('<w:tcBorders>' + "".join(
    f'<w:{s} w:val="single" w:sz="1" w:space="0" w:color="CCCCCC"/>' for s in ("top", "left", "bottom", "right"))
        + '</w:tcBorders>')
MAR = ('<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
       '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>')


def cell(content_xml, width, fill=None, valign=None):
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
    va = f'<w:vAlign w:val="{valign}"/>' if valign else ""
    return f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{BORD}{shd}{MAR}{va}</w:tcPr>{content_xml}</w:tc>'


def cell_text(text, header=False, small=True):
    sz = '<w:sz w:val="18"/><w:szCs w:val="18"/>' if small else ""
    rpr = ('<w:color w:val="FFFFFF"/>' + sz) if header else ('<w:color w:val="333333"/>' + sz)
    if header:
        text = f"**{text}**"
    lines = text.split("\n")
    return "".join(f'<w:p {pid()}><w:pPr><w:spacing w:after="0"/></w:pPr>{runs(l, rpr)}</w:p>' for l in lines)


def table(headers, rows, widths, zebra=True, first_col_bold=False):
    assert sum(widths) == FULL_W, (headers, sum(widths))
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    tblpr = (f'<w:tblPr><w:tblW w:w="{FULL_W}" w:type="dxa"/><w:tblInd w:w="-7" w:type="dxa"/>'
             '<w:tblLayout w:type="fixed"/>'
             '<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
             '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>')
    hdr = ('<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>'
           + "".join(cell(cell_text(h, header=True), w, fill=BLUE, valign="center") for h, w in zip(headers, widths))
           + "</w:tr>")
    body = []
    for r_i, row in enumerate(rows):
        fill = "F5F5F5" if zebra and r_i % 2 == 1 else None
        cells = []
        for c_i, (val, w) in enumerate(zip(row, widths)):
            v = f"**{val}**" if first_col_bold and c_i == 0 and val else val
            cells.append(cell(cell_text(v), w, fill=fill))
        body.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cells) + "</w:tr>")
    return f"<w:tbl>{tblpr}<w:tblGrid>{grid}</w:tblGrid>{hdr}{''.join(body)}</w:tbl>" + para("", after=60)


# ---------------------------------------------------------------- images
IMAGES = []  # (rid, target)
_img_id = [100]


def add_image(src, name):
    _img_id[0] += 1
    ext = os.path.splitext(src)[1].lower().lstrip(".")
    ext = "jpeg" if ext == "jpg" else ext
    target = f"media/poc_{_img_id[0]}.{ 'jpg' if ext == 'jpeg' else ext }"
    shutil.copy(src, os.path.join(W, target))
    rid = f"rIdPoc{_img_id[0]}"
    IMAGES.append((rid, target))
    return rid, _img_id[0]


def drawing(src, width_in, name):
    rid, iid = add_image(src, name)
    w, h = Image.open(src).size
    cx = int(width_in * EMU_PER_IN)
    cy = int(cx * h / w)
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{iid}" name="{escape(name)}" descr="{escape(name)}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{iid}" name="{escape(name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            f'</wp:inline></w:drawing></w:r>')


def figure(src, width_in, caption):
    return (f'<w:p {pid()}><w:pPr><w:keepNext/><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr>'
            f'{drawing(src, width_in, caption)}</w:p>' + para(caption, after=200, jc="center",
            rpr='<w:i/><w:iCs/><w:color w:val="666666"/><w:sz w:val="16"/><w:szCs w:val="16"/>'))


def screenshot_grid(items, per_row, img_w_in):
    col_w = FULL_W // per_row
    widths = [col_w] * per_row
    widths[-1] += FULL_W - sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    rows_xml = []
    for i in range(0, len(items), per_row):
        chunk = items[i:i + per_row]
        cells = []
        for j in range(per_row):
            if j < len(chunk):
                src, cap = chunk[j]
                c = (f'<w:p {pid()}><w:pPr><w:spacing w:after="40"/><w:jc w:val="center"/></w:pPr>{drawing(src, img_w_in, cap)}</w:p>'
                     f'<w:p {pid()}><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
                     f'{runs(cap, "<w:color w:val=\"333333\"/><w:sz w:val=\"15\"/><w:szCs w:val=\"15\"/>")}</w:p>')
            else:
                c = f'<w:p {pid()}/>'
            cells.append(cell(c, widths[j]))
        rows_xml.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cells) + "</w:tr>")
    tblpr = (f'<w:tblPr><w:tblW w:w="{FULL_W}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
             '<w:tblLook w:val="04A0" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>')
    return f"<w:tbl>{tblpr}<w:tblGrid>{grid}</w:tblGrid>{''.join(rows_xml)}</w:tbl>" + para("", after=60)


# ---------------------------------------------------------------- content
B = []
a = B.append

# 1. Version control
a(heading("Version Control"))
a(table(["Date", "Modified By", "Description", "Ver."],
        [["18/11/2026", "Bassam Basamad", "Initial draft: POC results, operating model and recommendation for review (Abdullah Asaad)", "0.9"],
         ["", "", "", ""]],
        [1300, 1800, 5126, 800]))
a(page_break())

# 2. Impact assessment
a(heading("Impact Assessment"))
a(note("Scope of this POC: standalone sample app, dummy data, personal Expo test account. No Bupa systems, code, data or credentials were used. "
       "Notes describe the impact if the recommendation is adopted for the future React Native app."))
a(table(["Area", "Impacted?", "Notes"], [
    ["Mobile App (OutSystems)", "No (POC)", "Future: React Native app is the candidate replacement of the OutSystems 11 mobile app; OTA model changes (see §6)."],
    ["Back Office (OutSystems)", "No", "Not affected."],
    ["Core System (Caesar / Oracle)", "No", "Not affected by the OTA mechanism."],
    ["IBM API Gateway", "Future", "Exposes the force-upgrade (minimum version) API from Spring Boot (§5.11)."],
    ["External Integration", "Yes", "Expo Services (EAS Build / EAS Update, SaaS) or a self-hosted update server + CDN."],
    ["Database / Data Model", "No", "Client-side local data must stay backward-compatible to allow rollbacks."],
    ["Security / Compliance (PDPL, SAMA)", "Yes", "Data residency of the update service, code signing, access control, audit logs, vendor assessment."],
    ["Infrastructure / DevOps", "Yes", "New CI/CD pipelines (build, OTA publish, staged rollout, hotfix); key management; optional self-hosting."],
    ["LifeTime Pipeline", "No", "Replaced by Git + CI/CD + Expo channels for the React Native app."],
], [3000, 1300, 4726], first_col_bold=True))
a(page_break())

# 3. Executive summary
a(heading("Executive Summary"))
a(para("Management requested a practical POC of Over-the-Air (OTA) updates for a future React Native mobile application "
       "(with a Java Spring Boot backend) replacing the current OutSystems 11 mobile app. A sample app was built with "
       "**Expo (SDK 58) and Expo EAS Update**, installed on a physical Android phone as a signed preview APK, and taken through "
       "the full lifecycle: **deploy → OTA update → bad release → rollback → native change → hotfix**."))
a(para("**Result: successful.** JavaScript, UI and business-logic changes reached the installed app within minutes with no "
       "rebuild and no store release; a faulty release was rolled back in seconds; and an update requiring a new native module "
       "was **automatically withheld** from incompatible installed apps (no crash). This compatibility guarantee is stronger than "
       "the OutSystems 11 model, where new code reaches old native shells and must be guarded at runtime."))
a(para("**Recommendation: conditional GO.** The technology is suitable for our production mobile app, provided the controls in "
       "§9 are implemented. The key open decision is hosting and compliance: **Expo Enterprise** (managed SaaS, subject to data-residency, "
       "PDPL and vendor-security review) versus a **self-hosted update server** on Bupa infrastructure using the open expo-updates protocol."))
a(table(["Management question", "POC answer", "Evidence"], [
    ["Push JS / UI / business logic OTA without a store release?", "Yes, live in ~1 minute; applied on next launch or via prompt", "#2"],
    ["Deploy → OTA update → rollback?", "Yes, rollback to previous update or to the APK's embedded code in seconds", "#3, #4, #5"],
    ["What cannot be delivered OTA?", "Native SDK/plugin, permission and configuration changes, which need a new build and a store release", "#6, #8"],
    ["Runtime / version compatibility?", "Automatic native fingerprint; incompatible updates are never delivered", "#6, #7, #9"],
    ["Security, signing, access, audit?", "Available: code signing (Production+ plan), roles and protected channels, audit logs (Enterprise)", "Docs (§5.7)"],
    ["Staged / canary rollout and recovery?", "Built in: % rollout per update or by branch; automatic launch-crash recovery", "Docs (§5.8)"],
    ["CI/CD and operational effort?", "Standard CLI pipeline; needs release-branch discipline and a Release Manager role", "§5.9, §10"],
    ["Compared with OutSystems?", "Safer and more controllable; more governance effort", "§6"],
], [3300, 4626, 1100]))
a(page_break())

# 4. Dependencies
a(heading("Dependencies"))
a(table(["#", "Dependency", "Description", "Owner / Team", "Status"], [
    ["1", "Hosting decision", "Expo Enterprise (quote, data-hosting statement, SLA) vs. self-hosted update server", "Architecture / Procurement", "Open"],
    ["2", "Compliance review", "Data residency, PDPL, vendor security assessment of Expo Services", "InfoSec / Legal / Compliance", "Open"],
    ["3", "Signing keys", "Bupa-owned code-signing key pair in a key vault / HSM; rotation policy", "InfoSec", "Open"],
    ["4", "CI/CD platform", "Pipeline runner (e.g. Azure DevOps / GitHub Actions / Expo Workflows) with robot credentials", "DevOps", "Open"],
    ["5", "Force-upgrade API", "Spring Boot endpoint returning the minimum supported app version, via IBM API Gateway", "Backend", "Open"],
    ["6", "Store accounts", "Bupa Google Play and Apple Developer accounts for native releases", "Mobile / IT", "Existing"],
], [400, 1700, 3826, 1900, 1200]))
a(divider())

# 5. HLD
a(heading("High-Level Design (End-to-End)"))
a(heading("Architecture Diagrams", 2))
a(para("Target operating architecture: two release paths share one source repository. **JavaScript/UI/logic changes** go out OTA "
       "in minutes; **native changes** (new runtime version) go through a signed build and a store release."))
a(figure(os.path.join(DIAG, "arch.png"), 6.27, "Figure 1: Target OTA architecture (OTA path in green, native/store path in orange)"))
a(heading("Sequence / Component Diagrams", 2))
a(figure(os.path.join(DIAG, "seq.png"), 6.27, "Figure 2: Update check sequence on the device (all paths observed in the POC except step 4)"))

a(heading("POC Scope & Configuration", 2))
a(table(["Item", "POC setting"], [
    ["Framework / versions", "Expo SDK 58.0.26, React Native 0.88.1, expo-updates 58.0.22, EAS CLI 27.10.0 (checked against the official docs on 18/11/2026)"],
    ["Sample app", "Dummy premium quote (plan × age factor × smoker loading) with unit tests; 'About this build' panel showing channel, runtime, update ID, embedded/OTA"],
    ["Build", "EAS cloud build, Android APK (internal distribution), signed with an Expo-managed keystore; about 13 min on the free queue"],
    ["Channel / branch", "preview → preview"],
    ["Runtime version policy", "fingerprint (hash of native inputs), recommended over appVersion, which depends on manually bumping the version"],
    ["Update behaviour", "checkAutomatically = ON_LOAD; fallbackToCacheTimeout = 0; in-app 'Check for update' and 'Restart to apply' prompt"],
    ["Account", "Personal Expo free plan (15 Android builds/month, 1,000 update MAUs); 2 builds and 7 updates used"],
], [2400, 6626], first_col_bold=True))

a(heading("OTA Scope: What Can and Cannot Be Delivered", 2))
a(table(["Delivered OTA (no store release)", "Requires a new build + store release"], [
    ["UI, screens, styling, text, translations", "Adding or upgrading native modules / SDKs (camera, biometrics, payments, push, analytics)"],
    ["Business logic and validation rules in JavaScript", "Expo SDK / React Native version upgrades"],
    ["API calls, endpoints, JS feature flags", "Permissions, app icon, splash, deep links, manifest / Info.plist"],
    ["Images and assets bundled with JS", "Native project configuration and signing"],
], [4513, 4513]))
a(note("Store policies (Apple and Google) allow interpreted JavaScript updates that do not change the app's primary purpose. Confirm with Compliance before production."))

a(heading("Runtime Compatibility & Release Branching", 2))
a(para("Every build and every update carries a **runtime version**. With the **fingerprint** policy this is a hash of all native inputs, so it changes "
       "automatically when native code changes, and **an update is only served to builds with the same runtime version**. Observed in the POC:"))
a(table(["Change", "Runtime version", "Effect on installed apps"], [
    ["UI + business rule (v2, v3)", "A c07c2603 (unchanged)", "Delivered OTA to the installed APK"],
    ["Added native module expo-haptics (v4)", "B 73cd2156 (changed)", "Not delivered to APK A ('Up to date'); required APK build B"],
    ["Hotfix published from release branch (v2.1)", "A c07c2603", "Delivered to APK A even though B existed"],
    ["JS update on new native build (v5)", "B 73cd2156", "Delivered to APK B; native feature intact"],
], [3300, 2300, 3426]))
a(para("**Key operating rule:** urgent fixes must be published **from the git release branch matching the users' runtime** (release/x.y), "
       "not from main while main contains unreleased native changes; otherwise store users will not receive the fix. Users on unsupported "
       "old versions are moved forward by a **force-upgrade** check (§5.11)."))

a(heading("Update Behaviour on the Device", 2))
a(table(["Setting", "Default", "Recommended Bupa standard"], [
    ["When to check", "ON_LOAD (each cold start)", "Cold start + app resume (AppState 'active')"],
    ["Wait at startup", "0 ms (open immediately)", "0 ms normally; a short timeout or blocking screen only for critical fixes"],
    ["When to apply", "Next cold start", "Prompt 'Restart to apply'; never reload during a transaction or form"],
], [2200, 2900, 3926], first_col_bold=True))

a(heading("Security, Signing, Access Control & Audit", 2))
a(table(["Control", "Capability", "Expo plan"], [
    ["End-to-end update code signing", "The device verifies each update against a Bupa-held public key (eas update with a private key)", "Production / Enterprise"],
    ["Role-based access", "Owner, Admin, Release Manager, Developer, Runner, Viewer", "Organization account"],
    ["Protected channels", "eas channel:protect production: only Release Manager and above can publish, roll back or change rollouts", "Organization account"],
    ["CI identity", "Robot users with scoped role and access token; no personal tokens in pipelines", "Organization account"],
    ["Single sign-on", "Corporate IdP sign-in for Expo accounts", "Production and above"],
    ["Audit logs", "Immutable; kept 1.5 years; who did what and when", "Enterprise only"],
    ["Traceability", "Each update records git commit, message and author (exported: eas-update-history.json)", "All plans"],
], [2400, 4826, 1800], first_col_bold=True))
a(note("Not demonstrated in the POC (free plan): code signing, SSO, audit logs. Signing keys were Expo-managed for the POC; production keys must be Bupa-owned."))

a(heading("Rollback, Staged Rollout & Failure Recovery", 2))
a(table(["Capability", "How", "POC status"], [
    ["Roll back to previous update", "eas update:rollback <group> (republishes the last good bundle; no rebuild)", "Demonstrated (#4)"],
    ["Roll back to embedded code", "eas update:roll-back-to-embedded", "Demonstrated (#5)"],
    ["Staged rollout per update", "eas update --rollout-percentage=10, raise with eas update:edit, revert with eas update:revert-update-rollout", "Documented"],
    ["Branch-based rollout", "eas channel:rollout (share of a channel's users to a new branch)", "Documented"],
    ["Automatic recovery", "Crash before first render on the first launch of an update → marked failed → falls back to the last working update", "Documented"],
], [2300, 5026, 1700], first_col_bold=True))
a(note("Limits per Expo documentation: errors more than 10 s after the first render are not auto-recovered; rollbacks are unsafe if an update changed locally stored data, "
       "so local data and schema changes must remain backward-compatible."))

a(heading("CI/CD & Operational Model", 2))
a(table(["Stage", "Activities", "Gate / owner"], [
    ["1. Pull request", "Lint, typecheck, unit tests, SAST/dependency scan; optional preview update on a PR channel", "Code review"],
    ["2. Merge to main", "Publish to the staging channel; QA regression on staging builds", "QA sign-off"],
    ["3. Production OTA", "CI robot publishes signed update with rollout 5% → 25% → 100%, monitoring crash and error rate between steps", "Release Manager approval"],
    ["4. Native release", "Fingerprint changed → EAS Build (signed AAB/IPA) → store submission → tag release/x.y", "Release Manager + store review"],
    ["5. Hotfix", "Cherry-pick to release/x.y → publish OTA for that runtime only", "Release Manager (expedited)"],
], [1800, 5226, 2000], first_col_bold=True))
a(para("Finding: the POC's unit tests caught the simulated pricing typo, but **eas update publishes whatever it is given**. Tests and approvals must therefore be enforced "
       "by the pipeline, and production publishing restricted to the CI robot through protected channels. No publishing from developer laptops."))

a(heading("Monitoring", 2))
a(bullet("Expo dashboard / Insights: adoption per update and runtime, deployments, update download performance."))
a(bullet("Crash and error reporting (e.g. Sentry) tagged with the update ID, with alerts that trigger the rollback runbook."))
a(bullet("Release KPIs: time-to-fix, rollback count, percentage of users on supported runtimes."))

a(heading("API Specification", 2))
a(para("Proposed backend API to support forced upgrades (Spring Boot, exposed via IBM API Gateway):"))
a(table(["Endpoint", "Method", "Description", "Request / Response", "Auth"], [
    ["/mobile/v1/app-version-policy", "GET", "Returns minimum supported and latest native app version per platform; the app blocks or prompts store upgrade below the minimum",
     "Req: platform, appVersion, runtimeVersion\nRes: {minVersion, latestVersion, storeUrl, message}", "App key via gateway (no user token required)"],
], [2200, 900, 2626, 2200, 1100]))

a(page_break())
a(heading("UX Screenshots / POC Evidence", 2))
a(table(["#", "Scenario", "Runtime", "Update ID", "Result"], [
    ["1", "APK v1 installed", "A", "2cd09f30 (embedded)", "Blue v1; Silver 35 = 2,600"],
    ["2", "OTA v2: UI + rule (factor 1.3 → 1.25)", "A", "01a1ee87", "Green v2; 2,500; no rebuild"],
    ["3", "Bad release v3 (pricing typo 12.5)", "A", "01a1ee8b", "Red v3; 25,000 (simulated incident)"],
    ["4", "Rollback to previous update", "A", "01a1ee90", "Back to v2 in seconds"],
    ["5", "Roll back to embedded", "A", "2cd09f30", "Original APK code restored"],
    ["6", "Native module added; OTA v4", "B", "01a1eec6", "Old APK NOT updated ('Up to date'); no crash"],
    ["7", "Hotfix from release branch", "A", "01a1eee8", "Old APK received hotfix"],
    ["8", "New APK with native module", "B", "b7c489c3 (embedded)", "Purple v4; vibration works"],
    ["9", "OTA v5 on new runtime", "B", "01a1eeec", "Teal v5; native feature intact"],
], [400, 3026, 1100, 1900, 2600]))
shots = [("01-v1-embedded.jpg", "#1 v1 embedded"), ("02-v2-ota.jpg", "#2 OTA v2"), ("03-v3-bad-ota.jpg", "#3 bad v3"),
         ("04b-rollback-to-v2.jpg", "#4 rollback"), ("05b-rollback-to-embedded-v1.jpg", "#5 embedded"),
         ("06-incompatible-update-blocked.jpg", "#6 blocked"), ("07-hotfix-old-runtime.jpg", "#7 hotfix"),
         ("08-new-apk-native-embedded.jpg", "#8 new APK"), ("09-ota-on-new-runtime.jpg", "#9 OTA v5")]
a(screenshot_grid([(os.path.join(EVID, f), c) for f, c in shots], 5, 0.92))
a(note("Full-size screenshots and the exported update history (eas-update-history.json) are kept with the POC source."))
a(page_break())

# 6. Comparison
a(heading("Comparison with OutSystems 11 Mobile Updates"))
a(table(["Aspect", "OutSystems 11", "React Native + Expo EAS Update"], [
    ["JS / UI / logic updates", "Automatic on publish", "Explicit eas update per channel (via CI)"],
    ["Native / plugin change", "New code reaches all installed apps; old shells need defensive plugin checks and a forced store update", "Blocked automatically by fingerprint: old apps never receive incompatible code (#6)"],
    ["Users on old versions", "Get latest code (risk of broken features)", "Stay on last compatible version; hotfix from release branch (#7) + force upgrade"],
    ["When updates apply", "Platform-managed at startup / resume", "Configurable policy (silent, prompt, forced)"],
    ["Rollback", "Redeploy an earlier version via LifeTime", "One command, seconds; also back to embedded code"],
    ["Staged / canary rollout", "Not available for OTA (all users)", "Built in (% per update or per branch)"],
    ["Environments", "LifeTime environments", "Channels / branches (flexible; must be governed)"],
    ["Signing / integrity", "Platform-managed", "Code signing (paid plans) or self-hosted"],
    ["Audit", "LifeTime deployment history", "Audit logs (Enterprise) + CI logs"],
    ["Hosting", "Bupa OutSystems infrastructure", "Expo SaaS (US) or self-hosted"],
    ["Governance effort", "Low (opinionated platform)", "Higher (Bupa defines and enforces policy)"],
], [2100, 3300, 3626], first_col_bold=True))
a(para("**Summary:** OutSystems favours **reach** (everyone receives the update); Expo favours **safety and control** (only compatible apps receive it, "
       "with staged rollout and rollback in seconds). The trade-off is additional release governance."))
a(note("OutSystems behaviour is based on team experience and OutSystems community / Forge documentation; validate against the official 'Mobile App Update Scenarios' documentation."))
a(divider())

# 7. Options
a(heading("Enterprise Options & Alternatives"))
a(table(["Option", "Advantages", "Disadvantages"], [
    ["Expo EAS Update: Enterprise plan (recommended starting point)", "Mature, integrated with builds; rollouts, protected channels, SSO, audit logs, code signing, SLA",
     "US-hosted SaaS → data-residency / legal review; MAU-based cost (quote required)"],
    ["Self-hosted expo-updates protocol server", "Bupa-hosted; full data control; same client library and behaviour",
     "Build and operate server, CDN, signing, HA; no Expo dashboard / insights"],
    ["Open-source self-hosted tools (e.g. Hot Updater, maintained CodePush-server forks)", "Self-hosted; low licence cost",
     "Smaller communities; maturity varies; due diligence needed"],
    ["Microsoft App Center CodePush", "-", "Retired 31 March 2025; not an option"],
], [2900, 3063, 3063], first_col_bold=True))
a(page_break())

# 8. Limitations
a(heading("POC Limitations & Gaps"))
a(table(["Gap", "Impact", "Mitigation / next step"], [
    ["Android only; iOS not tested", "Apple review / TestFlight path unverified", "iOS validation in pilot"],
    ["Code signing, SSO, audit logs not demonstrated", "Security controls validated on paper only", "Pilot on a paid / Enterprise trial organization"],
    ["Staged rollout and crash recovery not demonstrated", "Behaviour at scale unverified", "Pilot with test-device group and fault injection"],
    ["No CI/CD pipeline built (manual publishing)", "Governance not yet proven", "Build reference pipeline in pilot"],
    ["No backend, auth, offline data or push in scope", "Integration risks open", "Include Spring Boot + gateway in pilot"],
    ["Single device, no load / bandwidth testing", "Performance at scale unknown", "Measure bundle size and adoption in pilot"],
    ["Data residency of Expo service not assessed", "Possible compliance blocker", "InfoSec / Legal review (Dependency #2)"],
], [3000, 2800, 3226]))
a(divider())

# 9. Recommendation
a(heading("Recommendation & Required Controls"))
a(para("**Conditional GO**: adopt Expo EAS Update for the React Native mobile app, subject to the following controls:"))
a(table(["#", "Control", "Owner", "Priority"], [
    ["1", "Hosting decision: Expo Enterprise (after data-residency, PDPL and vendor review) or self-hosted expo-updates server", "Architecture / InfoSec", "Must"],
    ["2", "Organization account with SSO, least-privilege roles, protected production channel, Release Manager role", "Architecture / DevOps", "Must"],
    ["3", "CI-only production publishing with robot identity, tests, security scan and approval gate", "DevOps", "Must"],
    ["4", "End-to-end update code signing with a Bupa-held key", "InfoSec", "Must"],
    ["5", "Fingerprint runtime policy, release branches per store version and hotfix pipeline", "Mobile / DevOps", "Must"],
    ["6", "Staged rollouts with crash/error monitoring tagged by update ID and a rollback runbook", "Mobile / Operations", "Must"],
    ["7", "Force-upgrade API and a standard update-UX policy", "Backend / Mobile", "Should"],
    ["8", "Audit trail: Expo audit logs (Enterprise) or CI + SIEM logging", "InfoSec", "Must"],
], [400, 5426, 2200, 1000]))
a(para("**Next steps:** (1) request an Expo Enterprise quote and data-hosting statement; (2) run a 2–3 week pilot with a Bupa Expo organization covering iOS, "
       "code signing, a CI pipeline and staged rollout; (3) prototype a self-hosted update server for comparison."))
a(page_break())

# 10. Tasks
a(heading("Development Task Breakdown & Effort Estimation"))
a(note("Indicative effort for the proposed pilot and production readiness; to be refined during pilot planning."))
tasks = [
    ["1", "Expo organization, SSO, roles, protected channels", "Setup", "Architecture / DevOps", "2", "-", "Not started"],
    ["2", "Hosting decision: Enterprise quote + data-residency / PDPL review", "Assessment", "Architecture / InfoSec / Legal", "5", "-", "Not started"],
    ["3", "Code-signing keys (key vault / HSM) and signed builds and updates", "Security", "InfoSec / Mobile", "3", "1", "Not started"],
    ["4", "CI/CD: quality gates, approval, staged rollout, hotfix pipeline", "DevOps", "DevOps", "8", "1, 3", "Not started"],
    ["5", "Update-UX component (check on resume, prompt, critical mode)", "Development", "Mobile", "3", "-", "Not started"],
    ["6", "Force-upgrade API (Spring Boot + gateway) and app check", "Development", "Backend / Mobile", "4", "-", "Not started"],
    ["7", "Monitoring: crash reporting by update ID, dashboards, alerts", "Operations", "Mobile / Operations", "3", "4", "Not started"],
    ["8", "iOS validation (TestFlight build + OTA + rollback)", "Validation", "Mobile", "3", "1", "Not started"],
    ["9", "Self-hosted update server prototype (comparison)", "Assessment", "Architecture / Backend", "5", "2", "Not started"],
    ["10", "Runbooks: release, hotfix, rollback, incident", "Governance", "Architecture", "2", "4", "Not started"],
]
a(table(["#", "Task", "Phase", "Owner", "Effort (days)", "Dep.", "Status"], tasks,
        [450, 2876, 1300, 1700, 900, 700, 1100]))
total = sum(int(t[4]) for t in tasks)
a(f'<w:p {pid()}><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr>'
  f'<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="{BLUE}"/></w:rPr><w:t xml:space="preserve">Total Estimated Effort: </w:t></w:r>'
  f'<w:r><w:rPr><w:i/><w:iCs/><w:color w:val="666666"/></w:rPr><w:t>{total} days (indicative)</w:t></w:r></w:p>')

body_xml = "".join(B)

# ---------------------------------------------------------------- splice body
vc = doc.find(">Version Control</w:t>", doc.find("</w:sdtContent></w:sdt>"))
start = max(doc.rfind("<w:p ", 0, vc), doc.rfind("<w:p>", 0, vc))
end = doc.rfind("<w:sectPr")  # final body-level sectPr
doc = doc[:start] + body_xml + doc[end:]

# ---------------------------------------------------------------- TOC rebuild
def toc_entry(level, text, name, first):
    style = "TOC1" if level == 1 else "TOC2"
    page = str(PAGES.get(text, ""))
    field_begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
                   '<w:r><w:fldChar w:fldCharType="separate"/></w:r>') if first else ""
    nr = '<w:rPr><w:noProof/><w:webHidden/></w:rPr>'
    return (f'<w:p {pid()}><w:pPr><w:pStyle w:val="{style}"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9016"/></w:tabs><w:rPr><w:noProof/></w:rPr></w:pPr>'
            f'{field_begin}<w:hyperlink w:anchor="{name}" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/><w:noProof/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
            f'<w:r>{nr}<w:tab/></w:r><w:r>{nr}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{nr}<w:instrText xml:space="preserve"> PAGEREF {name} \\h </w:instrText></w:r>'
            f'<w:r>{nr}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{nr}<w:t>{page}</w:t></w:r><w:r>{nr}<w:fldChar w:fldCharType="end"/></w:r></w:hyperlink></w:p>')


toc_xml = "".join(toc_entry(l, t, n, i == 0) for i, (l, t, n) in enumerate(TOC))
toc_xml += f'<w:p {pid()}><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
sdt_start = doc.find("<w:sdtContent>", doc.find("Table of Contents") - 2000)
th = doc.find("Table of Contents</w:t></w:r></w:p>", sdt_start) + len("Table of Contents</w:t></w:r></w:p>")
sdt_end = doc.find("</w:sdtContent></w:sdt>", th)
doc = doc[:th] + toc_xml + doc[sdt_end:]

# ---------------------------------------------------------------- cover
TITLE = "React Native OTA Updates: Expo EAS Update POC"
CODE = "PSD_RN_OTA_POC"
doc = doc.replace("<w:t>[Project Name]</w:t>", f"<w:t>{escape(TITLE)}</w:t>", 1)
doc = re.sub(r"<w:t>PSD_\[</w:t>(.*?)<w:t>ProjectName</w:t>(.*?)<w:t>\]</w:t>",
             lambda m: f"<w:t>{CODE}</w:t>{m.group(1)}<w:t></w:t>{m.group(2)}<w:t></w:t>", doc, count=1, flags=re.S)
doc = doc.replace("<w:t>[Date]</w:t>", "<w:t>18 November 2026</w:t>", 1)
doc = re.sub(r"<w:t>1\.0</w:t>", "<w:t>0.9 (Draft)</w:t>", doc, count=1)
open(os.path.join(W, "document.xml"), "w", encoding="utf8").write(doc)

# ---------------------------------------------------------------- header
for hf in ("header4.xml",):
    p = os.path.join(W, hf)
    h = open(p, encoding="utf8").read()
    h = re.sub(r"<w:t>PSD_\[</w:t>(.*?)<w:t>ProjectName</w:t>(.*?)<w:t>\]</w:t>",
               lambda m: f"<w:t>{CODE}</w:t>{m.group(1)}<w:t></w:t>{m.group(2)}<w:t></w:t>", h, count=1, flags=re.S)
    open(p, "w", encoding="utf8").write(h)

# ---------------------------------------------------------------- rels / content types / settings
rp = os.path.join(W, "_rels", "document.xml.rels")
rels = open(rp, encoding="utf8").read()
add = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{t}"/>'
              for rid, t in IMAGES)
rels = rels.replace("</Relationships>", add + "</Relationships>")
open(rp, "w", encoding="utf8").write(rels)

cp = os.path.join(OUT, "[Content_Types].xml")
ct = open(cp, encoding="utf8").read()
if 'Extension="jpg"' not in ct:
    ct = ct.replace('<Default Extension="png"', '<Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="png"', 1)
open(cp, "w", encoding="utf8").write(ct)

sp = os.path.join(W, "settings.xml")
st = open(sp, encoding="utf8").read()
if "w:updateFields" not in st:
    for anchor in ("<w:hdrShapeDefaults", "<w:footnotePr", "<w:endnotePr", "<w:compat"):
        if anchor in st:
            st = st.replace(anchor, '<w:updateFields w:val="true"/>' + anchor, 1)
            break
open(sp, "w", encoding="utf8").write(st)

json.dump([t for _, t, _ in TOC], open(os.path.join(os.path.dirname(OUT), "toc_titles.json"), "w"))
print("headings:", len(TOC), "images:", len(IMAGES), "tasks total:", total)
