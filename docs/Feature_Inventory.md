# Trackify Feature Inventory v3 (English)

> Based on manual exploration of Trackify's actual pages (see `Feature_Inventory_01.md` for original sketch).
> Device: Android 14 Emulator (Pixel 8) / app-release.apk
>
> **Important notes:**
> 1. ✅ **App has Monthly budget configuration** during first-run onboarding; the configured budget drives the Home `This Month` progress percentage
> 2. ⭐ Scope was deliberately narrowed to **Home + Transactions only**

---

## 1. Pages Explored (real, observed)

| # | Page | Entry | Core Interaction | Status |
|----|------|-------|------------------|--------|
| 1 | **First-run onboarding** | First app launch after install/data reset | Enter name; select currency; configure Monthly budget; enable Bank SMS Reader; Get Started | ✅ Used |
| 2 | **Home** | Default landing page | Monthly income/expense overview + budget progress + Add Transaction shortcut + last 7 days Spending visualization + Recent transactions display | ✅ Used |
| 3 | **Transactions** | Tab | Lists all transaction types (Expense / Income / Transfer); supports search across transactions by note | ✅ Used |
| 4 | **Add Transaction** | Tab | Add transaction: amount + category (or add new category) + date + note + tags (comma-separated) + photo upload | ✅ Used |
| 5 | **Analytics** | Tab | Charts (Week / Month / Year) + income/expense statistics + spending by category + Weekly/Monthly/Yearly overview | ✅ Used |
| 6 | **Settings** | Tab | Preferences (currency, theme, add categories) + Notifications (daily reminder, reminder time, test live alert) + SMS banks reader + Backup & Restore + Security + Data | ✅ Used |

> ✅ **Confirmed**: Monthly budget is configured during first-run onboarding. The current automation sets it to `30000` and verifies the Home percentage as `expense / budget × 100`, rounded to an integer. Budget is covered as shared setup and a downstream assertion rather than as a standalone management journey.

---

## 2. Decision: Which 2 Core Features to Test

### ✅ Selection 1: Home → Add Transaction shortcut

**Why this one**:
- 🎯 **Highest-frequency user path** — the core of any personal-finance app
- 🔬 **High risk** — the primary data source for everything downstream
- 📊 **Many testable business points** — adding Expense / Income / Transfer transactions; transaction amount; category / add new custom category; note; tags; transaction timestamp; transaction attachment upload
- 🔧 **Cross-page dependency** — feeds both the Transactions page and the Home / Analytics summaries
- ⚡ **Automatable** — UI elements are relatively stable

**Sub-features to test**:

| Sub-feature | Priority | Automatable |
|-------------|----------|-------------|
| Add **Expense** transaction with: amount + category (mandatory, e.g. Food) + note ("breakfast with Dinna") + tags ("food,dinna") + date + photo attachment | P0 | ✅ |
| Add **Income** transaction with: amount + category (mandatory, e.g. Salary) + note ("fulltime salary") + tags ("fulltime salary") + date + photo attachment | P0 | ✅ |
| Add **Transfer** transaction with: amount + category (mandatory, e.g. Others) + note ("transfer amount from main account into sub account") + tags ("transfer") + date + photo attachment | P0 | ✅ |
| Add a **new custom category** inline during Add Transaction flow | P1 | ✅ |
| Use the **new custom category** in an Expense transaction | P0 | ✅ |

### ✅ Selection 2: Transactions

**Why this one**:
- 🔬 **Validation surface** — once transactions are added via Home shortcut, the Transactions page must display them correctly. This is the downstream check that verifies the Add Transaction flow actually persisted the data.

**Sub-features to test**:

| Sub-feature | Priority | Automatable |
|-------------|----------|-------------|
| Filter transactions by type (All / Expense / Income / Transfer) | P0 | ✅ |
| Transactions list is **summarized by date** (grouped sections per date) | P0 | ✅ |

### ❌ Not Selected (and why)

| Feature | Reason |
|---------|--------|
| Analytics / charts | Visual-heavy; assertions have low ROI; DOM structure is unstable |
| Settings | Configuration-focused; low depth of business rules |
| Budget configuration as a standalone journey | Already covered in first-run setup and Home summary assertions; no separate Budget Management scenario selected |

---

## 3. Automation Coverage Matrix

| Core Feature | P0 cases | P1 cases | Total |
|--------------|----------|----------|-------|
| Home → Add Transaction shortcut | 4 | 1 | **5** |
| Transactions | 2 | 0 | **2** |
| **Total** | **6** | **1** | **7** |

> Scope was deliberately narrowed. The brief says "depth, not breadth" — 7 Gherkin cases focused on the highest-value path is enough.

---

## 4. Automation Strategy (brief, for the README)

### 1. Framework selection

- **pytest-bdd** — Gherkin `.feature` files + pytest steps
- **Appium 3 + uiautomator2** — Android emulator / device driver
- **Page Object** — Page layer handles elements; Flow layer handles business

### 2. AI touchpoints

- Use **ChatGPT / Claude / Codex** to draft initial Gherkin cases → manual review
- Use **Appium Inspector** screenshots → AI suggests Locators
- **Day 3** implement AI Failure Triage (failure log → root-cause category)

### 3. Data reset strategy

- `adb shell pm clear <packageName>` → wipe Hive DB
- **Before Smoke / CRUD tests**: clear once
- **Before Persistence / data-validation tests**: do **not** clear — only kill process / restart emulator

---

## 5. Day 2 TODO

1. Based on the §3 coverage matrix, write **2 Gherkin `.feature` files**:
   - `add_transaction.feature` (5 cases)
   - `transactions.feature` (2 cases)
2. Use Appium Inspector to capture Locators for:
   - Home page Add Expense / Income / Transfer transaction entry points
   - Add Transaction screen
   - Transactions page (filter + list grouping)
3. Implement `page/add_transaction.py`, `page/home.py`, `page/transactions.py`
4. Get the first end-to-end case running

---

## Appendix: Additional Trackify Capabilities / Limits

- ✅ Has Monthly budget configuration in first-run onboarding
- ✅ Home `This Month` displays progress derived from expense versus budget
- ⚠️ A separate post-onboarding Budget Management workflow was not selected as a core automation feature
- ❌ No cloud sync (100% offline / Hive-only)
- ❌ No multi-currency conversion (only display currency)
- ✅ Has: SMS banks reader (planned future integration?)
- ✅ Has: Backup & Restore (likely JSON export / import)
- ✅ Has: Security (PIN / biometrics — TBD)

---

*This Feature_Inventory.md is the source of truth for the test scope. `Feature_Inventory_01.md` is kept as the original exploration sketch from Day 1.*
