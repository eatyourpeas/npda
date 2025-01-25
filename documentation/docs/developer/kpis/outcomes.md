# (44-49) Outcomes

## 44. Mean HbA1c

### Calculation

**Numerator**: Mean of HbA1c measurements (item 17) within the audit period, excluding measurements taken within 90 days of diagnosis

**Denominator**: Total number of eligible patients (measure 1)

**Notes**: The median for each patient is calculated. We then calculate the mean of the medians. Django does not support Median aggregation function, so this is done manually through a custom `calculate_median` method.

**Data Items**: 17

---

## 45. Median HbA1c

### Calculation

**Numerator**: Median of HbA1c measurements (item 17) within the audit period, excluding measurements taken within 90 days of diagnosis

**Denominator**: Total number of eligible patients (measure 1)

**Notes**: The median for each patient is calculated. We then calculate the median of the medians. Only `eligible` and `ineligible` patient querysets are valid; others should be discarded.

**Data Items**: 17

---

## 46. Number of admissions

### Calculation

**Numerator**: Total number of admissions with a valid reason for admission (item 50) AND with a start date (item 48) OR discharge date (item 49) within the audit period

**Denominator**: Total number of eligible patients (measure 1)

**Notes**: There can be more than one admission per patient, but eliminate duplicate entries.

**Data Items**: 48, 49, 50

---

## 47. Number of DKA admissions

### Calculation

**Numerator**: Total number of admissions with a reason for admission (item 50) that is 2 = DKA AND with a start date (item 48) OR discharge date (item 49) within the audit period

**Denominator**: Total number of eligible patients (measure 1)

**Notes**: There can be more than one admission per patient, but eliminate duplicate entries.

**Data Items**: 48, 49, 50

---

## 48. Required additional psychological support

### Calculation

**Numerator**: Total number of eligible patients with at least one entry for Psychological Support (item 39) that is 1 = Yes within the audit period (based on visit date)

**Denominator**: Total number of eligible patients (measure 1)

**Data Items**: 39

---

## 49. Albuminuria present

### Calculation

**Numerator**: Total number of eligible patients whose most recent entry for Albuminuria Stage (item 31) based on observation date (item 30) is 2 = Microalbuminuria or 3 = Macroalbuminuria

**Denominator**: Total number of eligible patients (measure 1)

**Data Items**: 30, 31

---
