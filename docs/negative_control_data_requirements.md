# SafeMap AI — Negative-Control Data Requirements & Non-Flood Observation Schema

**Document Version**: 1.0.0  
**Status**: Formal Quality Standard  
**Target Domain**: Statistical Validation, False-Positive Rate Modeling, and ROC-AUC Computation  
**Governing Principle**: Strict Anti-Fabrication & Evidence-Grounded Negative-Control Classification  

---

## 1. Executive Summary & Problem Formulation

In machine learning and hydrological flood modeling, model performance cannot be scientifically determined from positive (flood) instances alone. A model that predicts "Severe Flood" 100% of the time will achieve a 100% true-positive recall on an all-positive dataset, while producing catastrophic false alarms during everyday weather.

### The Positive Selection Bias Trap
Conventional disaster databases, news archives, and municipal disaster summaries record events exclusively when major damage, displacement, or loss of life occurs. 
In Milestone 7, our audit demonstrated:
- Curated flood events: $N = 8$ across 115 years (1908–2023).
- Continuous non-flood control days: $N = 0$.
- Consequence: Specificity ($\frac{TN}{TN + FP}$) and False-Positive Rate ($\frac{FP}{FP + TN}$) are **mathematically undefined**.

### The Fallacy of Passive "No Flood" Labeling
A naive or unscientific engineering shortcut is to label any day without a recorded disaster report as "NO_FLOOD". **SafeMap AI strictly forbids this assumption.**

Why passive absence of a flood report is NOT proof of no flooding:
1. **Unrecorded Micro-Inundation**: A localized convective storm dumping 70 mm in 1 hour over an urban underpass causes knee-deep water that stalls traffic for 3 hours. If municipal pumps de-water it quickly, no formal disaster bulletin is generated, yet significant flood inundation occurred.
2. **Missing Reporting Channels**: Disadvantaged or informal settlements frequently suffer severe water stagnation that is never featured in municipal press releases.
3. **Threshold Ambiguity**: Without explicit sensor and municipal operational logs, it is impossible to distinguish between a dry day, a light rain day with normal drainage, and an unrecorded flood.

> [!CAUTION]
> **Cardinal Invariant**: A period or date without an explicit flood entry must **NEVER** automatically be labeled `NO_FLOOD` or `DOCUMENTED_NON_FLOOD`. It must be classified as `UNKNOWN_OR_UNCLASSIFIED` until verified evidence proves normal, non-inundated conditions.

---

## 2. Formal Five-State Observation Schema

To eliminate selection bias without fabricating data, SafeMap AI establishes a five-state classification taxonomy:

```
                                 Observation Epoch (Date / Time-Window)
                                                   │
                 ┌─────────────────────────────────┴─────────────────────────────────┐
                 │                                                                   │
         Telemetry Present?                                                  Telemetry Missing?
                 │                                                                   │
        ┌────────┴────────┐                                                          │
        │                 │                                                          │
   Physical Ground     Model Reanalysis                                              ▼
   Observations?       Only?                                              MISSING_OBSERVATION
        │                 │                                             (Sensor offline / dropout)
        │                 ▼
        │          MODELLED_ESTIMATE
        │        (GloFAS / ERA5 reanalysis)
        │
   ┌────┴──────────────────────────┐
   │                               │
Event Occurred?             Zero Flooding Claimed?
   │                               │
   ▼                               ▼
CONFIRMED_FLOOD              Ground Verified by Evidence Rule?
(Verified physical ground          │
 telemetry + damage/inundation)    ├── YES ────────► DOCUMENTED_NON_FLOOD
                                   │                 (Dual-source verification of zero inundation)
                                   └── NO  ────────► UNKNOWN_OR_UNCLASSIFIED
                                                     (No disaster declared, but ground truth unverified)
```

### State Definitions

| State Code | Scientific Semantic | Required Evidentiary Proof | Role in Model Validation |
|:---|:---|:---|:---|
| **`CONFIRMED_FLOOD`** | Genuine, verified flood event resulting in surface inundation, breach, or damage. | 1. Direct meteorological observation (station rain gauge or AWS).<br>2. Physical or official damage verification (DRF logs, municipal disaster assessment, or satellite SAR inundation mask). | True Positive ($TP$) / False Negative ($FN$) ground truth. |
| **`DOCUMENTED_NON_FLOOD`** | Verified non-flood epoch with confirmed normal hydrological conditions. | 1. Calibrated precipitation record ($< 10.0\text{ mm}$ for non-rain baseline; or documented rain event with verified zero overflow).<br>2. Explicit municipal logs confirming zero water-logging complaints, zero DRF de-watering deployments, and normal traffic flow; OR cloud-free satellite clear-sky / zero open-water mask. | True Negative ($TN$) / False Positive ($FP$) ground truth. |
| **`UNKNOWN_OR_UNCLASSIFIED`** | Period with precipitation or normal calendar date, but lacking explicit municipal or satellite ground verification of flood status. | Moderate/heavy rain occurred ($> 15\text{ mm}$), but DRF logs are unavailable or incomplete. | **Excluded from evaluation metrics**. Cannot be assumed true negative. |
| **`MISSING_OBSERVATION`** | Date or interval where hydrometeorological sensors were non-operational or telemetry transmission failed. | Documented data gap (sensor flag = 9 or null). | **Excluded from evaluation metrics**. Treated as unobserved data gap. |
| **`MODELLED_ESTIMATE`** | Reanalysis or simulated output where ground sensors do not exist. | Copernicus GloFAS or ECMWF ERA5 gridded model outputs. | Independent benchmark candidate; never ground-truth label. |

---

## 3. Strict Evidence Rules for `DOCUMENTED_NON_FLOOD`

To certify a calendar date as `DOCUMENTED_NON_FLOOD`, a record must satisfy **Rule A** or **Rule B**:

### Rule A: Certified Dry or Trace Day
1. **Meteorological Evidence**: All reporting stations in the target catchment record 24-hour precipitation $\le 2.5\text{ mm}$ (IMD definition of non-rainy day).
2. **Reservoir Evidence**: Osman Sagar and Himayat Sagar flood gates remained 100% closed, with zero outflow release into the Musi River.
3. **Operational Evidence**: GHMC Disaster Response Force logs record zero monsoon emergency calls.

### Rule B: Certified Wet-Weather Non-Flood Control Day
*(Critical for false-alarm rate calibration: heavy rain that did NOT produce flooding due to adequate stormwater capacity).*
1. **Meteorological Evidence**: Recorded 24-hour rainfall between $15.0\text{ mm}$ and $64.4\text{ mm}$ (moderate rain) or $64.5\text{ mm}$ and $115.5\text{ mm}$ (heavy rain) at one or more AWS stations.
2. **Municipal Operational Verification**: Official GHMC Monsoon Control Room logs for the corresponding 24-hour period explicitly confirm:
   - Zero emergency de-watering pump deployments.
   - Zero causeway submergences or traffic diversions along the Musi corridor.
   - No colony inundation reports across the 30 municipal circles.
3. **Attribution**: Citation of the specific daily GHMC DRF monsoon incident register.

---

## 4. Minimum Sample Size Requirements for Legitimate Validation

In accordance with statistical power calculations ($1 - \beta \ge 0.80$ at $\alpha = 0.05$):

| Evaluation Metric | Current Dataset ($N=8$ Floods, $N=0$ Controls) | Minimum Required Dataset for Scientific Validation |
|:---|:---:|:---:|
| **Sample Size ($N$)** | 8 | $\ge 500$ daily observation records across 3 to 5 continuous monsoon seasons. |
| **Positive Flood Events** | 8 | $\ge 25$ distinct documented flood/inundation episodes. |
| **Negative Controls** | **0** | $\ge 475$ verified `DOCUMENTED_NON_FLOOD` days (comprising dry days and moderate rain non-flood days). |
| **Wilson 95% CI Width** | **51.9%** (Statistical Noise) | $\le 8.0\%$ (Narrow, statistically defensible margin of error). |
| **Specificity Computable?** | **NO** (`UNDEFINED`) | **YES** (Permits true False Alarm Rate calibration). |
| **ROC-AUC Computable?** | **NO** (Mathematically invalid) | **YES** (Permits legitimate threshold optimization). |

---

## 5. Prohibited Practices

1. **Synthetic Negative Generation**: Fabricating artificial "zero-rain" days or random non-flood rows is strictly prohibited.
2. **Silent Negative Assumption**: Converting untracked historical dates into negative labels without official municipal records is prohibited.
3. **Threshold Inversion**: Assuming that any day with rainfall $< 50\text{ mm}$ had zero flooding is prohibited (e.g. localized drainage blockages can flood underpasses with 30 mm of rain).
