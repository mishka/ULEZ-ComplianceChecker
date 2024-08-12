import sys
import requests
from colorama import Fore, Style, init
from fake_useragent import UserAgent


# Initialize colorama
init(autoreset=True)


class VehicleComplianceChecker:
    def __init__(self, vrm):
        self.vrm = vrm
        self.VEHICLE_LOOKUP_URL = "https://mobileapim.tfl.gov.uk/Prod/unirucCapitaFacade/VRMLookup"
        self.HGV_COMPLIANCE_URL = "https://api.tfl.gov.uk/Dvs2/api/hgv/{}"
        self.user_agent = UserAgent()


    def fetch_vehicle_info(self):
        """Fetch vehicle information from TFL API."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://tfl.gov.uk",
            "Referer": "https://tfl.gov.uk/",
            "User-Agent": self.user_agent.random,
        }

        data = {"vrmLookupRequest": {"vRM": self.vrm, "country": "UK", "date": {}}}

        try:
            response = requests.post(self.VEHICLE_LOOKUP_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching vehicle information: {e}")
            return None


    def fetch_hgv_compliance(self):
        """Fetch HGV compliance information from TFL API."""
        headers = {
            "Accept": "*/*",
            "Origin": "https://tfl.gov.uk",
            "User-Agent": self.user_agent.random,
        }

        try:
            response = requests.get(self.HGV_COMPLIANCE_URL.format(self.vrm), headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return None


    def format_value(self, value, chargeability=False):
        """Format the value with appropriate color and text."""
        if value is None:
            return f"{Fore.LIGHTYELLOW_EX}None{Style.RESET_ALL}"
        elif isinstance(value, bool):
            if chargeability:
                return f"{Fore.LIGHTRED_EX if value else Fore.LIGHTGREEN_EX}{'Yes' if value else 'No'}{Style.RESET_ALL}"
            return f"{Fore.LIGHTGREEN_EX if value else Fore.LIGHTRED_EX}{'Yes' if value else 'No'}{Style.RESET_ALL}"
        elif isinstance(value, int) and value in [0, 1]:
            if chargeability:
                return f"{Fore.LIGHTRED_EX if value == 1 else Fore.LIGHTGREEN_EX}{'Yes' if value == 1 else 'No'}{Style.RESET_ALL}"
            return f"{Fore.LIGHTGREEN_EX if value == 1 else Fore.LIGHTRED_EX}{'Yes' if value == 1 else 'No'}{Style.RESET_ALL}"
        else:
            return f"{Fore.LIGHTMAGENTA_EX}{value}{Style.RESET_ALL}"


    def display_vehicle_info(self, vehicle_info):
        """Format and display vehicle information."""
        if vehicle_info:
            details = vehicle_info.get('vrmLookupResponse', {}).get('vehicleDetails', {})
            formatted_info = (
                f"{Fore.CYAN}Vehicle Information:{Style.RESET_ALL}\n"
                f"{Fore.WHITE}Vehicle Registration:{Style.RESET_ALL} {self.format_value(details.get('vRM', 'N/A'))}\n"
                f"{Fore.WHITE}Make:{Style.RESET_ALL} {self.format_value(details.get('make', 'N/A'))}\n"
                f"{Fore.WHITE}Model:{Style.RESET_ALL} {self.format_value(details.get('model', 'N/A'))}\n"
                f"{Fore.WHITE}Color:{Style.RESET_ALL} {self.format_value(details.get('colour', 'N/A'))}\n"
                f"{Fore.WHITE}Tax Code:{Style.RESET_ALL} {self.format_value(details.get('taxCode', 'N/A'))}\n"
                f"{Fore.WHITE}Chargeability:{Style.RESET_ALL}\n"
                f"{Fore.WHITE}  - CC Chargeable:{Style.RESET_ALL} {self.format_value(details.get('chargeability', {}).get('isCcChargeable'), chargeability=True)}\n"
                f"{Fore.WHITE}  - LEZ Chargeable:{Style.RESET_ALL} {self.format_value(details.get('chargeability', {}).get('isLezChargeable'), chargeability=True)}\n"
                f"{Fore.WHITE}  - ULEZ Chargeable:{Style.RESET_ALL} {self.format_value(details.get('chargeability', {}).get('isUlezChargeable'), chargeability=True)}\n"
                f"{Fore.WHITE}  - ES Chargeable:{Style.RESET_ALL} {self.format_value(details.get('chargeability', {}).get('isEsChargeable'), chargeability=True)}\n"
                f"{Fore.WHITE}In Auto Pay:{Style.RESET_ALL} {self.format_value(details.get('inAutoPay'))}\n"
                f"{Fore.WHITE}ULEZ Exempt:{Style.RESET_ALL} {self.format_value(details.get('isULEZExempt'))}\n"
                f"{Fore.WHITE}ULEZ Vehicle List Type:{Style.RESET_ALL} {self.format_value(details.get('uLEZVehicleListType', 'N/A'))}\n"
                f"{Fore.WHITE}ULEZ Non-Chargeable:{Style.RESET_ALL} {self.format_value(details.get('isULEZNonChargeable'))}\n"
            )
            print(formatted_info)
            return details


    def display_hgv_compliance_info(self, compliance_info):
        """Format and display HGV compliance information."""
        if compliance_info:
            formatted_info = (
                f"{Fore.CYAN}HGV Compliance Information:{Style.RESET_ALL}\n"
                f"{Fore.WHITE}Star Rating:{Style.RESET_ALL} {self.format_value(compliance_info.get('starRating'))}\n"
                f"{Fore.WHITE}Is Exempt:{Style.RESET_ALL} {self.format_value(compliance_info.get('isExempt'))}\n"
                f"{Fore.WHITE}LEZ 2020:{Style.RESET_ALL} {self.format_value(compliance_info.get('lez2020'))}\n"
                f"{Fore.WHITE}Is Subject to DVS:{Style.RESET_ALL} {self.format_value(compliance_info.get('isSubjectToDvs'))}\n"
                f"{Fore.WHITE}Is Evidence Required:{Style.RESET_ALL} {self.format_value(compliance_info.get('isEvidenceRequired'))}\n"
                f"{Fore.WHITE}Euro Class Rating:{Style.RESET_ALL} {self.format_value(compliance_info.get('euroClassRating'))}\n"
                f"{Fore.WHITE}Country Code:{Style.RESET_ALL} {self.format_value(compliance_info.get('countryCode', 'N/A'))}\n"
                f"{Fore.WHITE}Vehicle Type:{Style.RESET_ALL} {self.format_value(compliance_info.get('vehicleType', 'N/A'))}\n"
            )
            print(formatted_info)


    def display_summary(self, details):
        """Display a summary of whether the vehicle meets ULEZ standards."""
        is_ulez_chargeable = details.get('chargeability', {}).get('isUlezChargeable', False)
        if is_ulez_chargeable:
            print(f"{Fore.LIGHTRED_EX}This vehicle does not meet the ULEZ emissions standards.{Style.RESET_ALL}")
        else:
            print(f"{Fore.LIGHTGREEN_EX}This vehicle meets the ULEZ emissions standards.{Style.RESET_ALL}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python ulezchecker.py VEHICLE_LICENSE_NUMBER")
        sys.exit(1)

    vehicle_registration_mark = sys.argv[1]

    checker = VehicleComplianceChecker(vehicle_registration_mark)

    # Check HGV compliance
    hgv_compliance = checker.fetch_hgv_compliance()
    if not hgv_compliance:
        print(f"{Fore.LIGHTRED_EX}Warning:{Style.RESET_ALL} The entered license plate is not valid.")
        quit()

    # If the license plate is valid, check low emission zone compliance
    vehicle_info = checker.fetch_vehicle_info()
    if vehicle_info:
        details = checker.display_vehicle_info(vehicle_info)
        checker.display_hgv_compliance_info(hgv_compliance)
        checker.display_summary(details)

if __name__ == "__main__":
    main()
