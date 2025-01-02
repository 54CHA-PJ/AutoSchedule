from export_to_client import main_client
from create_ics import main_ics
from colorama import init, Fore, Style

init(autoreset=True)

if __name__ == "__main__":
    
    print(
        Fore.YELLOW 
        + "\n----------------------------------------\n"
        + "Reading the schedule..." 
        + "\n----------------------------------------\n"
        + Style.RESET_ALL)
    main_ics()
    print(
        Fore.YELLOW 
        + "\n----------------------------------------\n"
        + "Exporting to Google Calendar..." 
        + "\n----------------------------------------\n"
        + Style.RESET_ALL)
    main_client()