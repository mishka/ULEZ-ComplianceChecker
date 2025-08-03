import sys
import requests
from colorama import Fore, Style, init
from fake_useragent import UserAgent

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

class VehicleComplianceChecker:
    VEHICLE_LOOKUP_URL = 'https://mobileapim.tfl.gov.uk/Prod/unirucCapitaFacade/VRMLookup'
    HGV_COMPLIANCE_URL = 'https://api.tfl.gov.uk/Dvs2/api/hgv/{}'
    user_agent = UserAgent()

    def __init__(self, vrm):
        self.vrm = vrm

    def fetch_vehicle_info(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://tfl.gov.uk',
            'Referer': 'https://tfl.gov.uk/',
            'User-Agent': self.user_agent.random,
        }
        data = {'vrmLookupRequest': {'vRM': self.vrm, 'country': 'UK', 'date': {}}}
        try:
            response = requests.post(self.VEHICLE_LOOKUP_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def fetch_hgv_compliance(self):
        headers = {
            'Accept': '*/*',
            'Origin': 'https://tfl.gov.uk',
            'User-Agent': self.user_agent.random,
        }
        try:
            response = requests.get(self.HGV_COMPLIANCE_URL.format(self.vrm), headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

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
        info = [
            colour_text('HGV Compliance Information:', 'heading'),
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

def main():
    if len(sys.argv) < 2:
        print('Usage: python ulezchecker.py VEHICLE_LICENSE_NUMBER')
        sys.exit(1)

    vehicle_registration_mark = sys.argv[1].strip().upper()
    checker = VehicleComplianceChecker(vehicle_registration_mark)

    hgv_compliance = checker.fetch_hgv_compliance()
    if not hgv_compliance:
        print(colour_text('Warning: The entered license plate is not valid.', 'warn'))
        sys.exit(1)

    vehicle_info = checker.fetch_vehicle_info()
    if vehicle_info:
        details = vehicle_info.get('vrmLookupResponse', {}).get('vehicleDetails', {})
        checker.display_vehicle_info(details)
        checker.display_hgv_compliance_info(hgv_compliance)
        checker.display_summary(details)

if __name__ == '__main__':
    main()
