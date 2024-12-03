# Varmepumpe Kontrollsystem

Styring av varmepumpe basert på strømpris for SE3-regionen. Systemet automatiserer styringen av en Sensibo-kontrollert varmepumpe basert på gjeldende strømpriser.

## Funksjoner

- Automatisk styring basert på strømpris
- Temperaturkontroll
- Manuell overstyring
- Prisvarsling
- Visualisering av gjeldende strømpris
- Sikker innlogging
- Responsivt web-grensesnitt

## Lokal Installasjon

``bash
# Klone prosjektet
git clone git@github.com:rakiso/varmepumpe_kontroll.git
cd varmepumpe_kontroll

# Opprett virtuelt miljø
python -m venv venv
source venv/bin/activate

# Installer avhengigheter
pip install -r requirements.txt

# Sett opp miljøvariabler
cp .env.example .env
# Rediger .env med dine innstillinger

SENSIBO_API_KEY=your_api_key
SENSIBO_DEVICE_ID=your_device_id
PRIS_KLASSE=SE3
MIN_TEMP=10
DEFAULT_TEMP=22
PRIS_START=5
PRIS_STOPP=10
ADMIN_PASSWORD=your_secure_password

# 1. Overfør filer til EC2
scp -i ~/.ssh/your-key.pem -r * ubuntu@your-ec2-ip:~/varmepumpe_kontroll/

# 2. SSH til EC2
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# 3. Sett opp på EC2
cd varmepumpe_kontroll
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Start med gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5001 app:app

Teknologier

Python/Flask
Gunicorn
Sensibo API
elprisetjustnu.se API
AWS EC2 (valgfritt)

Sikkerhet
Passordbeskyttet grensesnitt
CORS beskyttelse
Miljøvariabler for sensitive data

Bruk
Åpne applikasjonen i nettleseren
Logg inn med administratorpassord
Overvåk strømpriser og varmepumpestatus
Juster temperatur og prisgrenser etter behov
Lisens
MIT ```