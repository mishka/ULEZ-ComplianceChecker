# ULEZ Compliance Checker

This Python tool allows you to check if a vehicle meets ULEZ (Ultra Low Emission Zone) standards and HGV (Heavy Goods Vehicle) compliance. It fetches data from relevant APIs, formats the results with color-coded output for easy interpretation, and provides a summary of compliance status. Features include:

- Random user agents for each request
- Dynamic color formatting using the `colorama` library
- Detailed output with summary for ULEZ compliance
- Ability to handle command-line input for vehicle registration

![Example Outputs](https://raw.githubusercontent.com/mishka/ULEZ-ComplianceChecker/main/example.png)

## Installation

To use this tool, you need to have Python installed. You can install the required dependencies via pip:

```bash
pip install requests colorama fake_useragent
```

Then simply clone the repository and run it:
```bash
git clone https://github.com/mishka/ULEZ-ComplianceChecker
```

## Usage

Run the script with the vehicle registration number as an argument:
```bash
python ulezchecker.py VEHICLE_REGISTRATION
```

# Output Description

This section provides a detailed description of each field in the output. Each field represents specific information about the vehicle's registration and compliance with emission-related charges.

### Vehicle Information

- **Vehicle Registration**
  - **Description:** A unique identifier assigned to the vehicle by the vehicle registration authority.
  - **Example:** `X882SRM`

- **Make**
  - **Description:** The manufacturer or brand of the vehicle.
  - **Example:** `SUBARU`

- **Model**
  - **Description:** The specific model name or type of the vehicle produced by the manufacturer.
  - **Example:** `IMPREZA P1`

- **Color**
  - **Description:** The color of the vehicle as registered.
  - **Example:** `Blue`

- **Tax Code**
  - **Description:** A code used for vehicle tax classification purposes, which may affect charges and exemptions.
  - **Example:** `11`

### Chargeability

- **CC Chargeable**
  - **Description:** Indicates whether the vehicle is subject to the Congestion Charge (CC). This charge applies in certain urban areas with high traffic congestion.
  - **Value:** `Yes` means the vehicle is chargeable; `No` means it is not.

- **LEZ Chargeable**
  - **Description:** Indicates whether the vehicle is subject to the Low Emission Zone (LEZ) charge. The LEZ aims to reduce emissions from older, more polluting vehicles.
  - **Value:** `Yes` means the vehicle is chargeable; `No` means it is not.

- **ULEZ Chargeable**
  - **Description:** Indicates whether the vehicle is subject to the Ultra Low Emission Zone (ULEZ) charge. The ULEZ targets high-polluting vehicles to reduce air pollution.
  - **Value:** `Yes` means the vehicle is chargeable; `No` means it is not.

- **ES Chargeable**
  - **Description:** Indicates whether the vehicle is subject to other emission-related charges (e.g., Environmental Zones). This may vary depending on local regulations.
  - **Value:** `Yes` means the vehicle is chargeable; `No` means it is not.

### ULEZ Information

- **In Auto Pay**
  - **Description:** Indicates whether the vehicle is enrolled in an automatic payment scheme for ULEZ charges. If enrolled, the charge is automatically paid without requiring manual intervention.
  - **Value:** `Yes` means it is enrolled; `No` means it is not.

- **ULEZ Exempt**
  - **Description:** Indicates whether the vehicle is officially exempt from ULEZ charges. Exempt vehicles do not need to pay the ULEZ charge, even if they would otherwise be chargeable.
  - **Value:** `Yes` means the vehicle is exempt; `No` means it is not.

- **ULEZ Vehicle List Type**
  - **Description:** Categorizes the vehicle under a specific list type used for ULEZ compliance purposes. This classification helps determine the vehicle’s eligibility for exemption or charge.
  - **Example Value:** `L` denotes the type of list the vehicle is categorized under.

- **ULEZ Non-Chargeable**
  - **Description:** Confirms whether the vehicle is not subject to ULEZ charges. This field is a direct indication of the vehicle’s status regarding chargeability.
  - **Value:** `Yes` means the vehicle is non-chargeable; `No` means it is chargeable.

### HGV Compliance Information

- **Star Rating**
  - **Description:** A rating system for heavy goods vehicles (HGVs) that indicates their safety and emissions performance. Not applicable to passenger vehicles.
  - **Value:** `None` indicates no rating is available or applicable.

- **Is Exempt**
  - **Description:** Indicates whether the vehicle is exempt from heavy goods vehicle charges or regulations. This typically applies to compliance with specific HGV regulations.
  - **Value:** `Yes` means it is exempt; `No` means it is not.

- **LEZ 2020**
  - **Description:** Indicates whether the vehicle meets the Low Emission Zone standards set for 2020, applicable to HGVs. For a passenger vehicle, this field is not applicable.
  - **Value:** `Yes` or `No` would indicate compliance or non-compliance.

- **Is Subject to DVS**
  - **Description:** Refers to whether the vehicle is subject to the Direct Vision Standard (DVS) requirements for HGVs. This standard measures how much a driver can see directly from the vehicle’s cab.
  - **Value:** `Yes` means it is subject; `No` means it is not.

- **Is Evidence Required**
  - **Description:** Indicates if documentation or evidence is required to prove compliance with HGV regulations.
  - **Value:** `Yes` means evidence is required; `No` means it is not.

- **Euro Class Rating**
  - **Description:** Represents the Euro emission standard of the vehicle, which determines its environmental performance and compliance. Not applicable to passenger vehicles in this case.
  - **Example Value:** `None` indicates no rating is available or applicable.

- **Country Code**
  - **Description:** The country code where the vehicle is registered. This field helps identify the vehicle’s registration origin.
  - **Example Value:** `GB` for Great Britain.

- **Vehicle Type**
  - **Description:** The classification of the vehicle according to European standards, which categorizes it based on its design and use.
  - **Example Value:** `M1` denotes a passenger vehicle.
