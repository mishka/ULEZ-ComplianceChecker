import sys
import json
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from playwright.sync_api import sync_playwright

# Initialize colorama
init(autoreset=True)

COLOURS = {
    'yes': Fore.LIGHTGREEN_EX,
    'no': Fore.LIGHTRED_EX,
    'none': Fore.LIGHTYELLOW_EX,
    'label': Fore.WHITE,
    'heading': Fore.CYAN,
    'value': Fore.LIGHTMAGENTA_EX,
    'warn': Fore.LIGHTRED_EX
}

MAC_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

def colour_text(text, colour):
    return f'{COLOURS.get(colour, "")}{text}{Style.RESET_ALL}'

def format_value(value, chargeability=False):
    if value is None:
        return colour_text('None', 'none')
    if isinstance(value, bool) or (isinstance(value, int) and value in [0, 1]):
        val = bool(value)
        if chargeability:
            return colour_text('Yes', 'no') if val else colour_text('No', 'yes')
        return colour_text('Yes', 'yes') if val else colour_text('No', 'no')
    return colour_text(str(value), 'value')


class TfLComplianceChecker:
    HGV_COMPLIANCE_URL = 'https://api.tfl.gov.uk/Dvs2/api/hgv/{}'

    def __init__(self, vrm):
        self.vrm = vrm

    def fetch_vehicle_info_via_ui(self):
        """
        Executes user behavior matching the TfL Multi-Page Form Wizard:
        1. Fill VRM, Click UK Radio, Click Find Vehicle.
        2. Wait for Confirmation page, click Confirm Vehicle.
        3. Wait for Results page, pull HTML structure.
        """
        html_payload = None

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=MAC_USER_AGENT)
                page = context.new_page()

                # --- STEP 1: LANDING PAGE ---
                page.goto('https://tfl.gov.uk/modes/driving/check-your-vehicle/', wait_until='load')

                # Close cookies to prevent layout blockage
                try:
                    cookie_btn = page.locator('#cb-accept, button:has-text("Accept all cookies")').first
                    if cookie_btn.is_visible(timeout=1500):
                        cookie_btn.click()
                except Exception:
                    pass

                # Input the VRM
                page.wait_for_selector('#vrm', timeout=5000)
                page.fill('#vrm', self.vrm)

                # Select UK
                page.click('#countrySelectionUkLabel, label[for="countrySelectionUk"]')

                # Submit first form step
                with page.expect_navigation(wait_until='load', timeout=10000):
                    page.click('#entervrm-submit')

                # --- STEP 2: CONFIRMATION PAGE ---
                page.wait_for_url('**/VehicleConfirmation', timeout=5000)

                with page.expect_navigation(wait_until='load', timeout=10000):
                    page.click('#confirm-vehicle-submit')

                # --- STEP 3: RESULTS PAGE ---
                page.wait_for_url('**/Results', timeout=5000)
                page.wait_for_selector('#main, .results-page', timeout=5000)

                html_payload = page.locator('#main').inner_html()
                browser.close()
                return html_payload

            except Exception:
                return None

    def fetch_hgv_compliance(self):
        headers = {
            'Accept': '*/*',
            'Origin': 'https://tfl.gov.uk',
            'User-Agent': MAC_USER_AGENT,
        }
        try:
            response = requests.get(self.HGV_COMPLIANCE_URL.format(self.vrm), headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def parse_html_to_original_schema(self, html_payload):
        if not html_payload:
            return None

        soup = BeautifulSoup(html_payload, 'html.parser')

        # Pull vehicle details elements
        vrm_text = soup.find(id='vehicle-vrm')
        vrm_val = vrm_text.text.strip() if vrm_text else self.vrm

        desc_text = soup.find(id='vehicle-colour-make-model')
        colour, make, model = 'N/A', 'N/A', 'N/A'

        if desc_text:
            parts = desc_text.text.strip().split(' ')
            if len(parts) >= 1:
                colour = parts[0]
            if len(parts) >= 2:
                make = parts[1]
            if len(parts) >= 3:
                model = ' '.join(parts[2:])

        # Determine structural compliance parameters
        ulez_compliant_div = soup.find('div', class_='result-module', attrs={'data-module': 'Ulez-compliant'})
        main_text = soup.get_text().lower()

        is_ulez_chargeable = True
        if ulez_compliant_div or "meets the ulez" in main_text:
            is_ulez_chargeable = False

        # Build original schema mapping object
        details = {
            'vRM': vrm_val,
            'make': make,
            'model': model,
            'colour': colour,
            'taxCode': 'N/A',
            'chargeability': {
                'isCcChargeable': "congestion charge" in main_text and "£" in main_text,
                'isLezChargeable': "lez charge" in main_text,
                'isUlezChargeable': is_ulez_chargeable,
                'isEsChargeable': False
            },
            'inAutoPay': "pay by auto pay" in main_text,
            'isULEZExempt': False,
            'uLEZVehicleListType': 'N/A',
            'isULEZNonChargeable': not is_ulez_chargeable,
            'raw_soup': soup  # Pass soup object forward to allow contextual data extraction
        }
        return details

    def extract_zone_charges(self, soup):
        """Returns CC and Tunnel charge data as a dict (used for both display and lib output)."""
        zones = {}

        cc_module = soup.find('div', class_='congestionCharge')
        if cc_module:
            cc_title = cc_module.find('h3')
            cc_charge = cc_module.find('h4', class_='charge')
            zones['congestion_charge'] = {
                'title': cc_title.text.strip() if cc_title else 'Congestion Charge',
                'charge': cc_charge.text.strip() if cc_charge else None,
                'hours': '07:00-18:00 Mon-Fri | 12:00-18:00 Sat-Sun',
                'rates': {
                    'autopay': '£18.00',
                    'standard': '£18.00',
                    'late_payment': '£21.00'
                }
            }

        tunnel_module = soup.find('div', class_='tunnelCharge')
        if tunnel_module:
            tunnel_title = tunnel_module.find('h3')
            tunnel_charge = tunnel_module.find('h4', class_='charge')
            zones['tunnel_charge'] = {
                'title': tunnel_title.text.strip() if tunnel_title else 'Blackwall & Silvertown Tunnels Charge',
                'charge': tunnel_charge.text.strip() if tunnel_charge else None,
                'hours': '06:00-22:00 Daily (Peak: Wkday 06-10 North / 16-19 South)',
                'rates': {
                    'autopay_off_peak': '£1.50',
                    'autopay_peak': '£4.00'
                }
            }

        return zones

    def display_additional_zone_charges(self, soup):
        """Scrapes, minimizes, and safely displays secondary context for CC & Tunnels."""
        print(colour_text('Other Zone Charges Breakdown:', 'heading'))
        zones = self.extract_zone_charges(soup)

        if 'congestion_charge' in zones:
            z = zones['congestion_charge']
            print(f" * {colour_text(z['title'], 'label')} -> {colour_text(z['charge'] or 'Rate Found', 'value')}")
            print(f"   {colour_text('Times:', 'none')} {z['hours']}")
            print(f"   {colour_text('Rates:', 'none')} AutoPay: {z['rates']['autopay']} / Standard: {z['rates']['standard']} upfront, {z['rates']['late_payment']} late payment")

        if 'tunnel_charge' in zones:
            z = zones['tunnel_charge']
            print(f" * {colour_text(z['title'], 'label')} -> {colour_text(z['charge'] or 'Rate Found', 'value')}")
            print(f"   {colour_text('Times:', 'none')} {z['hours']}")
            print(f"   {colour_text('Rates:', 'none')} AutoPay: {z['rates']['autopay_off_peak']} (Off-Peak) / {z['rates']['autopay_peak']} (Peak)")
        print()

    def display_vehicle_info(self, details):
        info = [
            colour_text('Vehicle Information:', 'heading'),
            f"{colour_text('Registration:', 'label')} {format_value(details.get('vRM', 'N/A'))}",
            f"{colour_text('Make:', 'label')} {format_value(details.get('make', 'N/A'))}",
            f"{colour_text('Model:', 'label')} {format_value(details.get('model', 'N/A'))}",
            f"{colour_text('Colour:', 'label')} {format_value(details.get('colour', 'N/A'))}",
            f"{colour_text('Tax Code:', 'label')} {format_value(details.get('taxCode', 'N/A'))}",
            f"{colour_text('Chargeability:', 'label')}",
            f" - {colour_text('CC Chargeable:', 'label')} {format_value(details.get('chargeability', {}).get('isCcChargeable'), chargeability=True)}",
            f" - {colour_text('LEZ Chargeable:', 'label')} {format_value(details.get('chargeability', {}).get('isLezChargeable'), chargeability=True)}",
            f" - {colour_text('ULEZ Chargeable:', 'label')} {format_value(details.get('chargeability', {}).get('isUlezChargeable'), chargeability=True)}",
            f" - {colour_text('ES Chargeable:', 'label')} {format_value(details.get('chargeability', {}).get('isEsChargeable'), chargeability=True)}",
            f"{colour_text('In Auto Pay:', 'label')} {format_value(details.get('inAutoPay'))}",
            f"{colour_text('ULEZ Exempt:', 'label')} {format_value(details.get('isULEZExempt'))}",
            f"{colour_text('ULEZ Vehicle List Type:', 'label')} {format_value(details.get('uLEZVehicleListType', 'N/A'))}",
            f"{colour_text('ULEZ Non-Chargeable:', 'label')} {format_value(details.get('isULEZNonChargeable'))}",
            ""
        ]
        print('\n'.join(info))

    def display_hgv_compliance_info(self, compliance):
        if not compliance:
            return
        info = [
            colour_text('London HGV Compliance Information:', 'heading'),
            f"{colour_text('Star Rating:', 'label')} {format_value(compliance.get('starRating'))}",
            f"{colour_text('Is Exempt:', 'label')} {format_value(compliance.get('isExempt'))}",
            f"{colour_text('LEZ 2020:', 'label')} {format_value(compliance.get('lez2020'))}",
            f"{colour_text('Is Subject to DVS:', 'label')} {format_value(compliance.get('isSubjectToDvs'))}",
            f"{colour_text('Is Evidence Required:', 'label')} {format_value(compliance.get('isEvidenceRequired'))}",
            f"{colour_text('Euro Class Rating:', 'label')} {format_value(compliance.get('euroClassRating'))}",
            f"{colour_text('Country Code:', 'label')} {format_value(compliance.get('countryCode', 'N/A'))}",
            f"{colour_text('Vehicle Type:', 'label')} {format_value(compliance.get('vehicleType', 'N/A'))}",
            ""
        ]
        print('\n'.join(info))

    def display_summary(self, details):
        is_ulez_chargeable = details.get('chargeability', {}).get('isUlezChargeable', False)
        if is_ulez_chargeable:
            print(colour_text('This vehicle does not meet the ULEZ emissions standards.', 'warn'))
        else:
            print(colour_text('This vehicle meets the ULEZ emissions standards.', 'yes'))
        print()


class CAZComplianceChecker:
    BASE_URL = 'https://vehiclecheck.drive-clean-air-zone.service.gov.uk'

    def __init__(self, vrm):
        self.vrm = vrm
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': MAC_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Origin': self.BASE_URL,
            'Referer': f"{self.BASE_URL}/vehicle_checkers/enter_details"
        })

    def _get_csrf_token(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        if meta_tag:
            return meta_tag['content']
        return None

    def check_compliance(self):
        try:
            enter_url = f"{self.BASE_URL}/vehicle_checkers/enter_details"
            resp1 = self.session.get(enter_url, timeout=10)
            resp1.raise_for_status()
            csrf_token = self._get_csrf_token(resp1.text)

            data1 = {
                'authenticity_token': csrf_token,
                'vrn': self.vrm,
                'registration-country': 'UK',
                'commit': 'Continue'
            }
            resp2 = self.session.post(enter_url, data=data1, timeout=10)
            resp2.raise_for_status()

            confirm_url = f"{self.BASE_URL}/vehicle_checkers/confirm_details"
            resp3 = self.session.get(confirm_url, timeout=10)
            resp3.raise_for_status()
            csrf_token2 = self._get_csrf_token(resp3.text)

            data2 = {
                'authenticity_token': csrf_token2,
                'confirm_details_form[undetermined]': 'false',
                'confirm_details_form[gpw_make_mismatch]': 'false',
                'confirm_details_form[whitelist_category]': '',
                'confirm_details_form[external_status]': '',
                'confirm_details_form[confirm_details]': 'yes',
                'commit': 'Confirm'
            }
            self.session.headers.update({'Referer': confirm_url})
            resp4 = self.session.post(confirm_url, data=data2, timeout=10)
            resp4.raise_for_status()

            results_url = f"{self.BASE_URL}/air_zones/compliance"
            resp5 = self.session.get(results_url, timeout=10)
            resp5.raise_for_status()

            return self._parse_results(resp5.text)
        except Exception:
            return None

    def _parse_results(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', id='compliance-table')
        if not table:
            return None

        results = {}
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    city = cols[0].get_text(separator=' ', strip=True)
                    charge = cols[1].get_text(strip=True)
                    results[city] = {
                        'is_chargeable': 'No Charge' not in charge,
                        'charge': charge
                    }
        return results

    def display_results(self, results):
        if not results:
            return
        print(colour_text('National Clean Air Zone (CAZ) Information:', 'heading'))
        for city, data in results.items():
            city_padded = f" - {city}:".ljust(45)
            charge_formatted = colour_text(data['charge'], 'no' if data['is_chargeable'] else 'yes')
            print(f"{colour_text(city_padded, 'label')} {charge_formatted}")
        print()


# ---------------------------------------------------------------------------
# Public library interface
# ---------------------------------------------------------------------------

def check_vehicle(vrm: str) -> dict:
    """
    Fetch full compliance data for a UK vehicle registration mark.

    Returns a structured dict suitable for programmatic use. All keys are
    always present; values are None when data could not be retrieved.

    Schema
    ------
    {
        "vrm": str,
        "vehicle": {
            "make": str | None,
            "model": str | None,
            "colour": str | None,
            "tax_code": str | None
        },
        "london": {
            "ulez_chargeable": bool | None,
            "ulez_exempt": bool | None,
            "ulez_non_chargeable": bool | None,
            "ulez_vehicle_list_type": str | None,
            "cc_chargeable": bool | None,
            "lez_chargeable": bool | None,
            "es_chargeable": bool | None,
            "in_autopay": bool | None,
            "zone_charges": {
                "congestion_charge": {
                    "title": str,
                    "charge": str | None,
                    "hours": str,
                    "rates": { "autopay": str, "standard": str, "late_payment": str }
                } | None,
                "tunnel_charge": {
                    "title": str,
                    "charge": str | None,
                    "hours": str,
                    "rates": { "autopay_off_peak": str, "autopay_peak": str }
                } | None
            }
        },
        "hgv": {
            "star_rating": int | None,
            "is_exempt": bool | None,
            "lez_2020": bool | None,
            "is_subject_to_dvs": bool | None,
            "is_evidence_required": bool | None,
            "euro_class_rating": str | None,
            "country_code": str | None,
            "vehicle_type": str | None
        } | None,
        "national_caz": {
            "<city>": {
                "is_chargeable": bool,
                "charge": str
            },
            ...
        } | None,
        "ulez_cross_zone_deduction": str | None,
        "errors": []
    }
    """
    vrm = vrm.strip().upper()
    errors = []

    result = {
        "vrm": vrm,
        "vehicle": {
            "make": None,
            "model": None,
            "colour": None,
            "tax_code": None
        },
        "london": {
            "ulez_chargeable": None,
            "ulez_exempt": None,
            "ulez_non_chargeable": None,
            "ulez_vehicle_list_type": None,
            "cc_chargeable": None,
            "lez_chargeable": None,
            "es_chargeable": None,
            "in_autopay": None,
            "zone_charges": {
                "congestion_charge": None,
                "tunnel_charge": None
            }
        },
        "hgv": None,
        "national_caz": None,
        "ulez_cross_zone_deduction": None,
        "errors": errors
    }

    # --- TfL: vehicle details + ULEZ/CC/LEZ ---
    tfl = TfLComplianceChecker(vrm)

    hgv_data = tfl.fetch_hgv_compliance()
    if hgv_data:
        result["hgv"] = {
            "star_rating": hgv_data.get("starRating"),
            "is_exempt": hgv_data.get("isExempt"),
            "lez_2020": hgv_data.get("lez2020"),
            "is_subject_to_dvs": hgv_data.get("isSubjectToDvs"),
            "is_evidence_required": hgv_data.get("isEvidenceRequired"),
            "euro_class_rating": hgv_data.get("euroClassRating"),
            "country_code": hgv_data.get("countryCode"),
            "vehicle_type": hgv_data.get("vehicleType")
        }
    else:
        errors.append("HGV compliance lookup failed or vehicle is not an HGV.")

    ui_html = tfl.fetch_vehicle_info_via_ui()
    details = tfl.parse_html_to_original_schema(ui_html)

    if details:
        chargeability = details.get("chargeability", {})
        result["vehicle"] = {
            "make": details.get("make"),
            "model": details.get("model"),
            "colour": details.get("colour"),
            "tax_code": details.get("taxCode")
        }
        result["london"].update({
            "ulez_chargeable": chargeability.get("isUlezChargeable"),
            "ulez_exempt": details.get("isULEZExempt"),
            "ulez_non_chargeable": details.get("isULEZNonChargeable"),
            "ulez_vehicle_list_type": details.get("uLEZVehicleListType"),
            "cc_chargeable": chargeability.get("isCcChargeable"),
            "lez_chargeable": chargeability.get("isLezChargeable"),
            "es_chargeable": chargeability.get("isEsChargeable"),
            "in_autopay": details.get("inAutoPay"),
            "zone_charges": tfl.extract_zone_charges(details["raw_soup"])
        })
    else:
        errors.append("TfL UI scrape failed; London zone details unavailable.")

    # --- National CAZ ---
    caz = CAZComplianceChecker(vrm)
    caz_results = caz.check_compliance()

    if caz_results:
        result["national_caz"] = caz_results

        # Cross-zone ULEZ deduction (only used as fallback when TfL scrape fails)
        if not details:
            birmingham = caz_results.get("Birmingham", {})
            bristol = caz_results.get("Bristol", {})
            bham_chargeable = birmingham.get("is_chargeable")
            bris_chargeable = bristol.get("is_chargeable")

            if bham_chargeable is False and bris_chargeable is False:
                result["ulez_cross_zone_deduction"] = "compliant"
                result["london"]["ulez_chargeable"] = False
            elif bham_chargeable is True or bris_chargeable is True:
                result["ulez_cross_zone_deduction"] = "non_compliant"
                result["london"]["ulez_chargeable"] = True
            else:
                result["ulez_cross_zone_deduction"] = "insufficient_data"
    else:
        errors.append("National CAZ lookup failed.")

    return result


# ---------------------------------------------------------------------------
# CLI entry point — behaviour unchanged
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print('Usage: python compliance_checker.py VEHICLE_LICENSE_NUMBER')
        sys.exit(1)

    vrm = sys.argv[1].strip().upper()
    print(colour_text(f"\n--- Gathering Full Compliance Report for {vrm} ---\n", 'none'))

    # 1. Run Transport for London (TfL) Scraper Matrix
    tfl_checker = TfLComplianceChecker(vrm)
    hgv_compliance = tfl_checker.fetch_hgv_compliance()
    ui_html_payload = tfl_checker.fetch_vehicle_info_via_ui()

    details = tfl_checker.parse_html_to_original_schema(ui_html_payload)

    if details:
        tfl_checker.display_vehicle_info(details)
        tfl_checker.display_additional_zone_charges(details['raw_soup'])

        if hgv_compliance:
            tfl_checker.display_hgv_compliance_info(hgv_compliance)
        tfl_checker.display_summary(details)
    else:
        print(colour_text('Warning: Direct London ULEZ UI lookup failed. Deploying cross-zone logic...', 'warn') + '\n')

    # 2. Run National Clean Air Zone (CAZ) Checks
    caz_checker = CAZComplianceChecker(vrm)
    caz_results = caz_checker.check_compliance()

    if caz_results:
        caz_checker.display_results(caz_results)

        # Fallback matrix evaluation if the direct scraper completely breaks
        if not details:
            print(colour_text('London ULEZ Secondary Fallback Analysis:', 'heading'))
            birmingham = caz_results.get('Birmingham', {})
            bristol = caz_results.get('Bristol', {})
            bham_chargeable = birmingham.get('is_chargeable')
            bris_chargeable = bristol.get('is_chargeable')

            if bham_chargeable is False and bris_chargeable is False:
                print(colour_text('Deduction: This vehicle registers "No Charge" across National Class D car zones (Birmingham & Bristol).', 'label'))
                print(colour_text('Result: This vehicle cross-complies with standard requirements (Euro 4 Petrol / Euro 6 Diesel). It MEETS London ULEZ criteria.', 'yes'))
            elif bham_chargeable is True or bris_chargeable is True:
                print(colour_text('Deduction: This vehicle incurs charges inside Class D Clean Air zones.', 'label'))
                print(colour_text('Result: This vehicle does not cross-comply with standard requirements. It DOES NOT meet London ULEZ criteria.', 'warn'))
            else:
                print(colour_text('Result: Insufficient national Class D matrix data to confidently verify cross-zone compliance.', 'none'))
            print()
    else:
        print(colour_text('Warning: Could not fetch fallback National CAZ metrics.', 'warn') + '\n')

    print(colour_text("--- End of Report ---\n", 'none'))


if __name__ == '__main__':
    main()
