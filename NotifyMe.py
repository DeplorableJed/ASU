from selenium import webdriver # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from webdriver_manager.chrome import ChromeDriverManager # type: ignore
from tabulate import tabulate # type: ignore
import time
import subprocess
import random

VERBOSE = False  # Set to True for detailed output, False to suppress
message_counter = 0  # Initialize message counters

def log(message):
    """Prints a message only if VERBOSE mode is enabled."""
    if VERBOSE:
        print(message)

def save_html_to_file(driver, filename="raw_page.html"):
    """Saves the current page source to an HTML file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    log(f"Raw HTML saved to '{filename}'.")

def send_imessage(phone_numbers, message):
    """Sends an iMessage to multiple phone numbers using AppleScript."""
    global message_counter  # Use the global counter
    for phone_number in phone_numbers:
        applescript = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{phone_number.strip()}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        try:
            subprocess.run(['osascript', '-e', applescript], check=True)
            print(f"Notification: Message sent to {phone_number}.")
            message_counter += 1  # Increment message counter
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to send message to {phone_number}: {e}")

def parse_seats(seat_text):
    """Parses the seat availability text into an integer."""
    try:
        seats_available = int(seat_text.split()[0])
        return seats_available
    except (IndexError, ValueError):
        log(f"Warning: Could not parse seat text: {seat_text}")
        return 0  # Default to 0 if parsing fails

def highlight_text(text):
    """Wraps the given text with ANSI escape codes to highlight it."""
    return f"\033[93m{text}\033[0m"  # ANSI yellow

def get_class_list(subject, catalog_nbr, highlight_class_numbers, phone_numbers):
    """Fetches the class list and sends notifications if seats are available."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        log("Initializing WebDriver...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        log("WebDriver initialized successfully.")

        base_url = "https://catalog.apps.asu.edu/catalog/classes/classlist"
        params = (
            f"?campus=TEMPE&campusOrOnlineSelection=A&catalogNbr={catalog_nbr}"
            f"&honors=F&promod=F&searchType=all&subject={subject}&term=2257"
        )
        full_url = base_url + params

        log(f"Loading URL: {full_url}")
        driver.get(full_url)
        time.sleep(2)  # Ensure the page is fully loaded

        sections = driver.find_elements(By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div[5]/div/div/div/div")
        print(f"Found {len(sections)} class sections.")

        data = []
        for section in sections:
            try:
                course_number = section.find_element(By.XPATH, ".//div[contains(@class, 'number')]").text.strip()
                try:
                    instructor = section.find_element(By.XPATH, ".//div[contains(@class, 'instructor')]/a").text.strip()
                except:
                    instructor = section.find_element(By.XPATH, ".//div[contains(@class, 'instructor')]").text.strip()
                seat_text = section.find_element(By.XPATH, ".//div[contains(@class, 'seats')]").text.strip()

                available_seats = parse_seats(seat_text)

                # Highlight the row if the course is in the list of highlighted courses
                if course_number in highlight_class_numbers:
                    data.append([highlight_text(course_number),
                                 highlight_text(instructor),
                                 highlight_text(seat_text)])
                else:
                    data.append([course_number, instructor, seat_text])

                # Send notification if any selected course has available seats
                if available_seats > 0 and course_number in highlight_class_numbers:
                    message = f"Seats are available for {subject}-{catalog_nbr}-{course_number}: {available_seats} seats!"
                    send_imessage(phone_numbers, message)
                    print("*" * 80)
                    print(message)
                    print("*" * 80)

            except Exception as e:
                log(f"Warning: Skipping section due to missing data: {e}")
                continue

        # Print the table after processing all sections
        headers = ["Course Number", "Instructor", "Seats"]
        print(tabulate(data, headers=headers, tablefmt="pretty"))

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        driver.quit()
        log("WebDriver session ended.")

def main():
    """Runs the class availability checker in a continuous loop."""
    subject = input("Enter the subject code (e.g., PHY) [default: PHY]: ").strip() or "PHY"
    catalog_nbr = input("Enter the catalog number (e.g., 131) [default: 131]: ").strip() or "131"
    highlight_class_numbers = input(
        "Enter the class numbers to highlight (comma-separated NO spaces) [default: 14101]: "
    ).strip() or "61694"
    highlight_class_numbers = highlight_class_numbers.split(",")  # Split into a list
    phone_numbers = input(
        "Enter the + format phone numbers to notify (comma-separated NO spaces) [default: +12065658179,+12066837599]: "
    ).strip() or "+12065658179,+12066837599"
    phone_numbers = phone_numbers.split(",")  # Split into a list

    print("Starting continuous monitoring... Press Ctrl+C to stop.")

    try:
        while True:
            get_class_list(subject, catalog_nbr, highlight_class_numbers, phone_numbers)
            print(f"Total messages sent so far: {message_counter}")  # Print message counter
            wait_time = random.randint(45, 60)  # Random wait between 45 and 60 seconds
            print(f"Waiting {wait_time} seconds before the next check...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

if __name__ == "__main__":
    main()