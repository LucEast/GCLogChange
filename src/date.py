import os
import getpass
import csv
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def login(email, password):
    logging.info("Versuche, sich einzuloggen...")
    login_url = 'https://www.geocaching.com/account/signin?returnUrl=%2fplay'
    session = requests.Session()
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form')
    login_data = {tag['name']: tag.get('value', '') for tag in form.find_all('input') if 'name' in tag.attrs}
    login_data['UsernameOrEmail'] = email
    login_data['Password'] = password
    session.post(login_url, data=login_data)
    logging.info("Erfolgreich eingeloggt.")
    return session

def get_logs(session):
    logging.info("Rufe Log-Einträge ab...")
    logs_url = 'https://www.geocaching.com/my/logs.aspx?s=1'
    response = session.get(logs_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    log_dict = {}

    # Nach der Tabelle mit der Klasse "Table" suchen
    table = soup.find('table', class_='Table')
    if not table:
        logging.error("Keine Tabelle mit der Klasse 'Table' gefunden.")
        return log_dict

    # Alle Zeilen der Tabelle durchsuchen
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 6:
            found_date = cells[2].get_text(strip=True)
            link = cells[3].find_all('a', href=True)
            log_link = cells[5].find('a', href=True)
            if link and log_link:
                # Den Link finden, der nicht die Klasse 'ImageLink' hat
                for a in link:
                    if 'ImageLink' not in a.get('class', []):
                        gc_code = a['href'].split('/')[-1]
                        cache_name = a.get_text(strip=True)
                        gl_code = log_link['href'].split('/')[-1]
                        log_dict[cache_name] = {
                            'found_date': found_date,
                            'gc_code': gc_code,
                            'gl_code': gl_code
                        }
                        break
    
    logging.info(f"{len(log_dict)} eindeutige Log-Einträge gefunden.")
    return log_dict

def sort_logs(log_dict, cutoff_date):
    logging.info("Sortiere Log-Einträge...")
    logs_before_cutoff = []
    logs_after_cutoff = []

    for cache_name, log_info in log_dict.items():
        found_date_str = log_info['found_date']
        found_date = datetime.strptime(found_date_str, '%d.%m.%Y')
        log_link = f'https://www.geocaching.com/geocache/{log_info["gc_code"]}'
        log_text = cache_name
        gc_code = log_info['gc_code']
        gl_code = log_info['gl_code']

        if found_date < cutoff_date:
            logs_before_cutoff.append((log_link, found_date_str, log_text, gc_code, gl_code))
        else:
            logs_after_cutoff.append((log_link, found_date_str, log_text, gc_code, gl_code))
    
    logs_before_cutoff.sort(key=lambda x: x[2])  # Sort by log text alphabetically
    logging.info("Log-Einträge sortiert.")
    return logs_before_cutoff, logs_after_cutoff

def update_logs(session, sorted_logs, cutoff_date, dry_run=False):
    logging.info("Aktualisiere Log-Einträge...")
    with open('original_logs.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Log Link', 'Original Date', 'Original Text', 'GC Code', 'GL Code'])
        
        # Liste umgekehrt sortieren, um sicherzustellen, dass die alphabetische Reihenfolge beibehalten wird
        sorted_logs.reverse()

        new_date = cutoff_date - timedelta(days=1)  # Beginne einen Tag vor dem cutoff_date
        
        for log_link, log_date_str, log_text, gc_code, gl_code in sorted_logs:
            writer.writerow([log_link, log_date_str, log_text, gc_code, gl_code])
            if dry_run:
                logging.info(f"[Dry Run] Würde Log aktualisieren: {log_link} mit neuem Datum {new_date.strftime('%Y-%m-%dT%H:%M:%S')}")
            else:
                edit_url = f"https://www.geocaching.com/live/geocache/{gc_code}/log/{gl_code}/edit?logType=2"
                edit_response = session.get(edit_url)
                edit_soup = BeautifulSoup(edit_response.text, 'html.parser')
                
                # Den JSON-Wert 'logDate' ändern
                script_tag = edit_soup.find('script', text=lambda text: text and 'logDate' in text)
                if script_tag:
                    script_content = script_tag.string
                    new_log_date = new_date.strftime('%Y-%m-%dT%H:%M:%S')
                    updated_script_content = script_content.replace('"logDate": "', f'"logDate": "{new_log_date}')
                    script_tag.string.replace_with(updated_script_content)
                    new_date -= timedelta(days=1)  # Gehe einen Tag zurück für das nächste Datum
                else:
                    logging.warning(f"Kein 'logDate' JSON-Wert gefunden für: {log_link}")
                    continue
                
                # Die Formular-Daten sammeln und senden
                form = edit_soup.find('form')
                form_data = {tag['name']: tag.get('value', '') for tag in form.find_all('input') if 'name' in tag.attrs}
                form_data.update({tag['name']: tag.text for tag in form.find_all('span') if 'name' in tag.attrs})
                form_data['log-date'] = new_log_date

                # Das Formular absenden
                session.post(edit_url, data=form_data)
                logging.info(f'Log aktualisiert: {log_link} mit neuem Datum {new_log_date}')

    if not dry_run:
        confirm = input("Möchtest du wirklich fortfahren und die Logs aktualisieren? (j/n): ").strip().lower() == 'j'
        if confirm:
            new_date = cutoff_date - timedelta(days=1)  # Beginne einen Tag vor dem cutoff_date
            for log_link, log_date_str, log_text, gc_code, gl_code in sorted_logs:
                edit_url = f"https://www.geocaching.com/live/geocache/{gc_code}/log/{gl_code}/edit?logType=2"
                edit_response = session.get(edit_url)
                edit_soup = BeautifulSoup(edit_response.text, 'html.parser')
                
                # Den JSON-Wert 'logDate' ändern
                script_tag = edit_soup.find('script', text=lambda text: text and 'logDate' in text)
                if script_tag:
                    script_content = script_tag.string
                    new_log_date = new_date.strftime('%Y-%m-%dT%H:%M:%S')
                    updated_script_content = script_content.replace('"logDate": "', f'"logDate": "{new_log_date}')
                    script_tag.string.replace_with(updated_script_content)
                    new_date -= timedelta(days=1)  # Gehe einen Tag zurück für das nächste Datum
                else:
                    logging.warning(f"Kein 'logDate' JSON-Wert gefunden für: {log_link}")
                    continue
                
                # Die Formular-Daten sammeln und senden
                form = edit_soup.find('form')
                form_data = {tag['name']: tag.get('value', '') for tag in form.find_all('input') if 'name' in tag.attrs}
                form_data.update({tag['name']: tag.text for tag in form.find_all('span') if 'name' in tag.attrs})
                form_data['log-date'] = new_log_date

                # Das Formular absenden
                session.post(edit_url, data=form_data)
                logging.info(f'Log aktualisiert: {log_link} mit neuem Datum {new_log_date}')
        else:
            logging.info("Aktualisierung der Logs abgebrochen.")
            
def restore_logs(session, csv_path, dry_run=False):
    logging.info("Stelle ursprüngliche Log-Daten wieder her...")
    
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            log_link = row['Log Link']
            original_date = row['Original Date']
            log_text = row['Original Text']
            gc_code = row['GC Code']
            gl_code = row['GL Code']
            
            if dry_run:
                logging.info(f"[Dry Run] Würde Log zurücksetzen: {log_link} auf ursprüngliches Datum {original_date}")
            else:
                edit_url = f"https://www.geocaching.com/live/geocache/{gc_code}/log/{gl_code}/edit?logType=2"
                edit_response = session.get(edit_url)
                edit_soup = BeautifulSoup(edit_response.text, 'html.parser')
                
                # Das Datum im `span`-Element mit der Klasse 'flatpickr-day selected' ändern
                day_span = edit_soup.find('span', {'class': 'flatpickr-day selected'})
                if day_span:
                    day_span['aria-label'] = original_date
                    day_span.string = str(datetime.strptime(original_date, '%B %d, %Y').day)
                else:
                    logging.warning(f"Kein 'flatpickr-day selected' Span gefunden für: {log_link}")
                    continue
                
                # Die Formular-Daten sammeln und senden
                form = edit_soup.find('form')
                form_data = {tag['name']: tag.get('value', '') for tag in form.find_all('input') if 'name' in tag.attrs}
                form_data.update({tag['name']: tag.text for tag in form.find_all('span') if 'name' in tag.attrs})
                form_data['log-date'] = original_date

                # Das Formular absenden
                session.post(edit_url, data=form_data)
                logging.info(f'Log zurückgesetzt: {log_link} auf ursprüngliches Datum {original_date}')

def main():
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="Geocache Log Sortierung und Wiederherstellung")
        parser.add_argument('--email', required=True, help="Deine Geocaching Email")
        parser.add_argument('--password', required=True, help="Dein Geocaching Passwort")
        parser.add_argument('--cutoff-date', help="Das Stichtdatum im Format dd/mm/yyyy")
        parser.add_argument('--dry-run', action='store_true', help="Führe einen Dry-Run durch")
        parser.add_argument('--restore', help="Pfad zur CSV-Datei zum Wiederherstellen der ursprünglichen Daten")
        
        args = parser.parse_args()
        
        email = args.email
        password = args.password
        dry_run = args.dry_run
        
        session = login(email, password)
        
        if args.restore:
            restore_logs(session, args.restore, dry_run=dry_run)
        else:
            if not args.cutoff_date:
                raise ValueError("Das Stichtdatum muss angegeben werden, wenn keine Wiederherstellung durchgeführt wird")
            
            cutoff_date = datetime.strptime(args.cutoff_date, '%d/%m/%Y')
            
            log_dict = get_logs(session)
            sorted_logs, _ = sort_logs(log_dict, cutoff_date)
            update_logs(session, sorted_logs, cutoff_date, dry_run=dry_run)
    except Exception as e:
        logging.error(f'Fehler: {e}')

if __name__ == "__main__":
    main()