# Varmepumpe Kontrollpanel med Sensibo Sky

Dette prosjektet er et kontrollpanel for en varmepumpe som bruker Sensibo Sky. Applikasjonen er bygget med Flask og kan distribueres på en hvilken som helst server som støtter Flask og Nginx.

## Innhold

- [Funksjoner](#funksjoner)
- [Installasjon](#installasjon)
- [Distribusjon på AWS](#distribusjon-på-aws)
- [Bruk](#bruk)
- [Bidrag](#bidrag)
- [Lisens](#lisens)

## Funksjoner

- Viser gjeldende strømpris.
- Automatisk kontroll av varmepumpen basert på strømpris.
- Mulighet til å sette en prisgrense for automatisk kontroll.
- Bruker Sensibo API for å styre varmepumpen.
- Valg av pris klasse (SE1, SE2, SE3, SE4).

## Installasjon

Følg disse trinnene for å installere og kjøre prosjektet lokalt:

1. Klon repositoryet:
    ```bash
    git clone https://github.com/Rakiso/varmepumpe_sensibo_SE.git
    cd varmepumpe_sensibo_SE
    ```

2. Sett opp et virtuelt miljø og installer avhengigheter:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3. Opprett en `.env`-fil i rotkatalogen og legg til nødvendige miljøvariabler:
    ```env
    SENSIBO_API_KEY=din_sensibo_api_key
    SENSIBO_DEVICE_ID=din_sensibo_device_id
    FLASK_SECRET_KEY=din_flask_secret_key
    ADMIN_PASSWORD=admin_passord
    ```

4. Start Flask-applikasjonen:
    ```bash
    flask run --host=127.0.0.1 --port=5001
    ```

## Distribusjon på AWS

Følg disse trinnene for å distribuere prosjektet på en AWS EC2-instans:

1. Opprett en EC2-instans og koble til den via SSH.

2. Last opp `deploy_aws.sh`-skriptet til EC2-instansen.

3. Kjør distribusjonsskriptet:
    ```bash
    chmod +x deploy_aws.sh
    ./deploy_aws.sh
    ```

## Bruk

1. Åpne nettleseren og naviger til serverens IP-adresse eller domenenavn.
2. Logg inn med admin-passordet.
3. Velg pris klasse og sett prisgrensen.
4. Kontroller varmepumpen basert på strømprisen.

## Bidrag

Bidrag er velkomne! Følg disse trinnene for å bidra til prosjektet:

1. Fork repositoryet.
2. Opprett en ny branch (`git checkout -b feature/ny-funksjon`).
3. Gjør endringene dine og commit (`git commit -am 'Legg til ny funksjon'`).
4. Push til branchen (`git push origin feature/ny-funksjon`).
5. Opprett en Pull Request.

## Lisens

Dette prosjektet er lisensiert under MIT-lisensen. Se [LICENSE](LICENSE) for mer informasjon.
