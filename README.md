# ULEZ Compliance Checker

A Python tool to check whether a UK vehicle meets ULEZ (Ultra Low Emission Zone), LEZ (Low Emission Zone), Congestion Charge, and HGV compliance standards. It scrapes live data from TfL and the national Clean Air Zone service.

Works as both a **CLI quick-check tool** and an **importable library** that returns structured JSON data for use in other programs.

(Outdated screenshot from previous version but you should get the gist of it)
![Example Outputs](https://raw.githubusercontent.com/mishka/ULEZ-ComplianceChecker/main/example.png)

---

## Features

- Live TfL vehicle lookup via Playwright (headless browser)
- HGV compliance via TfL API
- National Clean Air Zone (CAZ) lookup across all UK cities
- Cross-zone ULEZ deduction fallback when direct TfL scrape is unavailable
- Colour-coded terminal output via `colorama`
- Importable `check_vehicle()` function returning a fully structured dict

---

## Installation

Requires Python 3.8+. Install dependencies:

```bash
pip install requests colorama beautifulsoup4 playwright
playwright install chromium
```

Clone the repository:

```bash
git clone https://github.com/mishka/ULEZ-ComplianceChecker
cd ULEZ-ComplianceChecker
```

---

## CLI Usage

Pass a UK vehicle registration as an argument:

```bash
python compliance_checker.py AB12CDE
```

The terminal will print a full colour-coded compliance report covering vehicle details, London zone chargeability, HGV status, and national CAZ results.

---

## Library Usage

Import `check_vehicle` and pass a registration. It returns a plain Python dict with all compliance data — no printing, no side effects.

```python
from compliance_checker import check_vehicle

data = check_vehicle("AB12CDE")

# Quick checks
print(data["london"]["ulez_chargeable"])      # True / False / None
print(data["vehicle"]["make"])                # e.g. "FORD"
print(data["national_caz"]["Birmingham"])     # e.g. "No Charge"
print(data["hgv"])                            # None if not an HGV
print(data["errors"])                         # List of non-fatal fetch failures
```

---

## Return Value — JSON Schema

`check_vehicle(vrm)` always returns a dict with the following top-level keys. All keys are always present; values are `None` when data could not be retrieved.

```json
{
  "vrm": "AB12CDE",
  "vehicle": { ... },
  "london": { ... },
  "hgv": { ... },
  "national_caz": { ... },
  "ulez_cross_zone_deduction": null,
  "errors": []
}
```

### `vrm`
`string` — The normalised registration mark used for all lookups (uppercase, stripped of whitespace).

---

### `vehicle`
Basic vehicle identity information parsed from the TfL results page.

| Key | Type | Description |
|---|---|---|
| `make` | `string \| null` | Manufacturer, e.g. `"FORD"` |
| `model` | `string \| null` | Model name, e.g. `"FOCUS"` |
| `colour` | `string \| null` | Registered colour, e.g. `"Blue"` |
| `tax_code` | `string \| null` | Vehicle tax classification code, e.g. `"11"` |

---

### `london`
London-specific zone compliance and chargeability flags.

| Key | Type | Description |
|---|---|---|
| `ulez_chargeable` | `bool \| null` | `true` if the vehicle must pay the ULEZ daily charge |
| `ulez_exempt` | `bool \| null` | `true` if the vehicle holds an official ULEZ exemption |
| `ulez_non_chargeable` | `bool \| null` | `true` if the vehicle is confirmed not subject to ULEZ charges |
| `ulez_vehicle_list_type` | `string \| null` | TfL vehicle list category, e.g. `"L"` |
| `cc_chargeable` | `bool \| null` | `true` if subject to the Congestion Charge |
| `lez_chargeable` | `bool \| null` | `true` if subject to the Low Emission Zone charge |
| `es_chargeable` | `bool \| null` | `true` if subject to an Emission Surcharge |
| `in_autopay` | `bool \| null` | `true` if the vehicle is enrolled in Auto Pay |
| `zone_charges` | `object` | Detailed rate breakdown for CC and Tunnels (see below) |

#### `london.zone_charges`

| Key | Type | Description |
|---|---|---|
| `congestion_charge` | `object \| null` | Present when a CC entry is found on the results page |
| `tunnel_charge` | `object \| null` | Present when a Blackwall/Silvertown Tunnel entry is found |

Each zone charge object has:

```json
{
  "title": "Congestion Charge",
  "charge": "£18.00",
  "hours": "07:00-18:00 Mon-Fri | 12:00-18:00 Sat-Sun",
  "rates": {
    "autopay": "£18.00",
    "standard": "£18.00",
    "late_payment": "£21.00"
  }
}
```

```json
{
  "title": "Blackwall & Silvertown Tunnels Charge",
  "charge": "£1.50",
  "hours": "06:00-22:00 Daily (Peak: Wkday 06-10 North / 16-19 South)",
  "rates": {
    "autopay_off_peak": "£1.50",
    "autopay_peak": "£4.00"
  }
}
```

---

### `hgv`
`object | null` — `null` if the vehicle is not an HGV or the lookup fails. Otherwise:

| Key | Type | Description |
|---|---|---|
| `star_rating` | `int \| null` | DVS safety star rating (0–5) |
| `is_exempt` | `bool \| null` | Whether the HGV is exempt from relevant charges |
| `lez_2020` | `bool \| null` | Whether the vehicle meets LEZ 2020 standards |
| `is_subject_to_dvs` | `bool \| null` | Whether the Direct Vision Standard applies |
| `is_evidence_required` | `bool \| null` | Whether compliance evidence must be supplied |
| `euro_class_rating` | `string \| null` | Euro emission class, e.g. `"Euro VI"` |
| `country_code` | `string \| null` | Registration country, e.g. `"GB"` |
| `vehicle_type` | `string \| null` | EU vehicle category, e.g. `"N3"` |

---

### `national_caz`
`object | null` — `null` if the national CAZ lookup fails. Otherwise a dict keyed by city name, each value containing both a boolean flag and the raw charge string from the government service:

| Key | Type | Description |
|---|---|---|
| `is_chargeable` | `bool` | `true` if the vehicle incurs a charge in this zone, `false` if exempt |
| `charge` | `string` | The raw label returned by the CAZ service, e.g. `"No Charge"` or `"Charge applies"` |

```json
{
  "Bath":       { "is_chargeable": false, "charge": "No Charge" },
  "Birmingham": { "is_chargeable": true,  "charge": "Charge applies" },
  "Bradford":   { "is_chargeable": false, "charge": "No Charge" },
  "Bristol":    { "is_chargeable": true,  "charge": "Charge applies" },
  "London (ULEZ)": { "is_chargeable": true, "charge": "Charge applies" },
  "Newcastle":  { "is_chargeable": false, "charge": "No Charge" },
  "Portsmouth": { "is_chargeable": false, "charge": "No Charge" },
  "Sheffield":  { "is_chargeable": false, "charge": "No Charge" }
}
```

Using the bool for logic and the string for display means you get the best of both:

```python
# Fast bool check
if data["national_caz"]["Birmingham"]["is_chargeable"]:
    print("Charge applies in Birmingham")

# Human-readable label when needed
print(data["national_caz"]["Birmingham"]["charge"])  # "Charge applies"
```

---

### `ulez_cross_zone_deduction`
`string | null` — Only populated when the primary TfL UI scrape fails and the tool falls back to inferring ULEZ compliance from national CAZ results. Possible values:

| Value | Meaning |
|---|---|
| `"compliant"` | Vehicle shows no charge in Birmingham and Bristol Class D zones — inferred to meet ULEZ standards |
| `"non_compliant"` | Vehicle incurs charges in Class D zones — inferred not to meet ULEZ standards |
| `"insufficient_data"` | Not enough national data to draw a conclusion |
| `null` | TfL scrape succeeded; no deduction was needed |

---

### `errors`
`array of strings` — Non-fatal errors accumulated during the lookup. The function always returns a result even when some sources fail. Check this field to understand what data may be missing.

Example:
```json
[
  "HGV compliance lookup failed or vehicle is not an HGV.",
  "National CAZ lookup failed."
]
```

---

## Full Example Response

```python
from compliance_checker import check_vehicle
import json

data = check_vehicle("X882SRM")
print(json.dumps(data, indent=2))
```

```json
{
  "vrm": "X882SRM",
  "vehicle": {
    "make": "SUBARU",
    "model": "IMPREZA P1",
    "colour": "Blue",
    "tax_code": "11"
  },
  "london": {
    "ulez_chargeable": true,
    "ulez_exempt": false,
    "ulez_non_chargeable": false,
    "ulez_vehicle_list_type": "N/A",
    "cc_chargeable": false,
    "lez_chargeable": false,
    "es_chargeable": false,
    "in_autopay": false,
    "zone_charges": {
      "congestion_charge": null,
      "tunnel_charge": null
    }
  },
  "hgv": null,
  "national_caz": {
    "Bath":          { "is_chargeable": false, "charge": "No Charge" },
    "Birmingham":    { "is_chargeable": true,  "charge": "Charge applies" },
    "Bradford":      { "is_chargeable": false, "charge": "No Charge" },
    "Bristol":       { "is_chargeable": true,  "charge": "Charge applies" },
    "London (ULEZ)": { "is_chargeable": true,  "charge": "Charge applies" },
    "Newcastle":     { "is_chargeable": false, "charge": "No Charge" },
    "Portsmouth":    { "is_chargeable": false, "charge": "No Charge" },
    "Sheffield":     { "is_chargeable": false, "charge": "No Charge" }
  },
  "ulez_cross_zone_deduction": null,
  "errors": [
    "HGV compliance lookup failed or vehicle is not an HGV."
  ]
}
```

---

## Output Field Reference (CLI)

The CLI output mirrors the JSON structure above. For a full description of each printed field, refer to the key descriptions in the schema above.

---

## Notes

- The TfL UI scrape uses Playwright with a headless Chromium browser. Keep `playwright install chromium` up to date if the scraper starts failing.
- The national CAZ service (`drive-clean-air-zone.service.gov.uk`) is a UK government service; its availability is outside this project's control.
- When `ulez_chargeable` is `null` and `ulez_cross_zone_deduction` is also `null`, both data sources were unavailable for this registration.
