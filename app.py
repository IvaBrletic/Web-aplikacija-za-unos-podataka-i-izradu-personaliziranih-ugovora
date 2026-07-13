from flask import (
    Flask,
    render_template,
    request,
    send_file,
    redirect,
    url_for,
    session
)
import sqlite3
import os

from datetime import datetime, date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "promijeni-ovaj-tajni-kljuc-za-zavrsni-rad"
)

def provjeri_iban(iban):
    # Provjera duljine IBAN-a
    if not iban:
        return False

    iban = iban.replace(" ", "").upper()  # Ukloni razmake i pretvori u velika slova

    if(len(iban) != 21):
        return False
    if not iban.startswith("HR"):
        return False
    if not iban[2:].isdigit():
        return False
    return True

def admin_prijava_obavezna(funkcija):
    @wraps(funkcija)
    def omotac(*args, **kwargs):
        if not session.get("admin_prijavljen"):
            return redirect(url_for("admin_login"))

        return funkcija(*args, **kwargs)

    return omotac

def kreiraj_bazu():
    conn = sqlite3.connect ("ugovori.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zupanije(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naziv TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mjesta(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naziv TEXT NOT NULL,
        postanski_broj TEXT NOT NULL,
        zupanija_id INTEGER,
        FOREIGN KEY (zupanija_id) REFERENCES zupanije(id)
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS korisnici(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ime TEXT NOT NULL,
        prezime TEXT NOT NULL,
        naziv_tvrtke TEXT NOT NULL,
        oib TEXT NOT NULL,
        datum_rodjenja TEXT NOT NULL,
        email TEXT NOT NULL,
        telefon TEXT NOT NULL,
        adresa TEXT NOT NULL,
        zupanija_id INTEGER,
        mjesto_id INTEGER,
        kontakt_oib TEXT,
        kontakt_adresa TEXT,
        kontakt_drzavljanstvo TEXT,
        kontakt_datum_rodenja TEXT,
        kontakt_funkcija TEXT,
        kontakt_broj_osobne_iskaznice TEXT,
        kontakt_datum_isteka_osobne_iskaznice TEXT,
        kontakt_mjesto_izdavanja_osobne_iskaznice TEXT,
        FOREIGN KEY (zupanija_id) REFERENCES zupanije(id),
        FOREIGN KEY (mjesto_id) REFERENCES mjesta(id)
    )
    """)

    novi_stupci = [
        "kontakt_oib TEXT",
        "kontakt_adresa TEXT",
        "kontakt_drzavljanstvo TEXT",
        "kontakt_drugo_drzavljanstvo TEXT",
        "kontakt_datum_rodenja TEXT",
        "kontakt_funkcija TEXT",
        "kontakt_broj_osobne_iskaznice TEXT",
        "kontakt_datum_isteka_osobne_iskaznice TEXT",
        "kontakt_mjesto_izdavanja_osobne_iskaznice TEXT",
        "vlasnik_drugo_drzavljanstvo TEXT"
    ]
    for stupac in novi_stupci:
        try:
            cursor.execute(f"ALTER TABLE korisnici ADD COLUMN {stupac}")
        except sqlite3.OperationalError:
            pass  # Stupac već postoji, preskoči


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dodatni_vlasnici(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        korisnik_id INTEGER,
        ime_prezime TEXT,
        oib TEXT,
        drzavljanstvo TEXT,
        drzava_prebivalista TEXT,
        kontakt_telefon TEXT,
        broj_osobne_iskaznice TEXT,
        datum_isteka_osobne_iskaznice TEXT,
        mjesto_izdavanja_osobne_iskaznice TEXT,
        datum_rodenja TEXT,
        funkcija TEXT,
        udio_vlasnistva REAL,
        politicki_izlozena INTEGER,
        FOREIGN KEY (korisnik_id) REFERENCES korisnici(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prodajna_mjesta(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        korisnik_id INTEGER,
        naziv TEXT,
        adresa TEXT,
        kontakt_osoba TEXT,
        vrsta_robe_usluga TEXT,
        email TEXT,
        telefon TEXT,
        sezonska_blagajna TEXT,
        Foreign KEY (korisnik_id) REFERENCES korisnici(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vrste_ugovora(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naziv TEXT NOT NULL,
        opis TEXT 
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ugovori(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        klijent_id INTEGER,
        vrsta_ugovora_id INTEGER,
        datum_potpisa TEXT NOT NULL,
        FOREIGN KEY (klijent_id) REFERENCES korisnici(id),
        FOREIGN KEY (vrsta_ugovora_id) REFERENCES vrste_ugovora(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pitanja(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tekst TEXT NOT NULL,
        tip_polja TEXT NOT NULL,
        obavezno INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ugovori_pitanja(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vrsta_ugovora_id INTEGER,
        pitanje_id INTEGER,
        redoslijed INTEGER,
        FOREIGN KEY (vrsta_ugovora_id) REFERENCES vrste_ugovora(id),
        FOREIGN KEY (pitanje_id) REFERENCES pitanja(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS odgovori(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        korisnik_id INTEGER,
        ugovor_id INTEGER,
        pitanje_id INTEGER,
        odgovor TEXT,
        FOREIGN KEY (korisnik_id) REFERENCES korisnici(id),
        FOREIGN KEY (ugovor_id) REFERENCES ugovori(id),
        FOREIGN KEY (pitanje_id) REFERENCES pitanja(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predlosci(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ugovor_id INTEGER,
        naziv TEXT NOT NULL,
        putanja_datoteke TEXT,
        FOREIGN KEY (ugovor_id) REFERENCES ugovori(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logovi(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        korisnik_id INTEGER,
        aktivnost TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (korisnik_id) REFERENCES korisnici(id)
    )
    """)
    # Provjera postojećih stupaca u tablici dodatni_vlasnici
    cursor.execute("PRAGMA table_info(dodatni_vlasnici)")
    stupci_dodatni = [red[1] for red in cursor.fetchall()]

    novi_stupci_dodatni = {
        "drugo_drzavljanstvo": "TEXT",
        "drzava_prebivalista": "TEXT",
        "vrsta_vlasnistva": "TEXT"
    }

    for naziv, tip in novi_stupci_dodatni.items():
        if naziv not in stupci_dodatni:
            cursor.execute(f"ALTER TABLE dodatni_vlasnici ADD COLUMN {naziv} {tip}")
            print(f"Dodan stupac u dodatni_vlasnici: {naziv}")

    # Provjera postojećih stupaca u tablici korisnici

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS administratori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            korisnicko_ime TEXT NOT NULL UNIQUE,
            lozinka_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        SELECT id
        FROM administratori
        WHERE korisnicko_ime = ?
    """, ("admin",))

    postojeci_admin = cursor.fetchone()

    if not postojeci_admin:
        lozinka_hash = generate_password_hash("Admin123!")

        cursor.execute("""
            INSERT INTO administratori (
                korisnicko_ime,
                lozinka_hash
            )
            VALUES (?, ?)
        """, (
            "admin",
            lozinka_hash
        ))

    conn.commit()
    conn.close()

def unesi_pocetne_podatke():
    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    #vrste ugovora
    cursor.execute("""
    
    INSERT OR IGNORE INTO vrste_ugovora (id, naziv, opis) 
    VALUES (1, "SPU2", "Upitnik za prihvaćanje platnih transakcija")
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO vrste_ugovora (id, naziv, opis)
    VALUES (2, "Posebne odredbe", "Posebne odredbe okvirnog ugovora")
    """)

    #pitanja iz forme
    pitanja = [
        ("naziv","Naziv tvrtke/obrta", "text", 1),
        ("oib","OIB tvrtke", "text", 1),
        ("nkdklasifikacija","NKD klasifikacija", "text", 1),
        ("iban","IBAN", "text", 1),
        ("maticni_broj","Matični broj", "text", 1),
        ("adresa_sjedista","Adresa sjedišta", "text", 1),
        ("virtualne_kartice","Prihvaćate li virtualne kartice?", "radio", 0),
        ("izvor_sredstava","Odaberite izvor sredstava", "checkbox", 0),
        ("izvor_ostalo","Izvor sredstava - ostalo", "text", 0),
        ("promet","Očekivani godišnji promet", "radio", 0),
        ("svrha","Svrha poslovnog odnosa", "checkbox", 0),
        ("svrha_ostalo","Svrha poslovnog odnosa - ostalo", "text", 0),
        ("kontakt_ime","Ime i prezime ovlaštene osobe", "text", 1),
        ("kontakt_email","Email ovlaštene osobe", "email", 1),
        ("kontakt_telefon","Telefon ovlaštene osobe", "text", 1),
        ("kontakt_oib","OIB ovlaštene osobe", "text", 1),
        ("kontakt_adresa","Adresa prebivališta ovlaštene osobe", "text", 1),
        ("kontakt_drzavljanstvo","Državljanstvo ovlaštene osobe", "text", 1),
        ("kontakt_drugo_drzavljanstvo", "Drugo državljanstvo ovlaštene osobe", "text", 0),
        ("kontakt_datum_rodenja","Datum rođenja ovlaštene osobe", "date", 1),
        ("kontakt_funkcija","Funkcija ovlaštene osobe", "text", 1),
        ("kontakt_broj_osobne_iskaznice","Broj osobne iskaznice ovlaštene osobe", "text", 1),
        ("kontakt_datum_isteka_osobne_iskaznice","Datum isteka osobne iskaznice ovlaštene osobe", "date", 1),
        ("kontakt_mjesto_izdavanja_osobne_iskaznice","Mjesto izdavanja osobne iskaznice ovlaštene osobe", "text", 1),
        ("vlasnik_ime","Ime i prezime vlasnika", "text", 1),
        ("vlasnik_drzavljanstvo","Državljanstvo vlasnika", "text", 1),
        ("vlasnik_drugo_drzavljanstvo", "Drugo državljanstvo vlasnika", "text", 0),
        ("vlasnik_drzava_prebivalista", "Država prebivališta vlasnika", "text", 1),
        ("vlasnik_OIB","OIB vlasnika", "text", 1),
        ("vlasnik_telefon","Telefon vlasnika", "text", 1),
        ("vlasnik_broj_osobne_iskaznice","Broj osobne iskaznice vlasnika", "text", 1),
        ("vlasnik_datum_isteka_osobne_iskaznice","Datum isteka osobne iskaznice vlasnika", "date", 1),
        ("vlasnik_mjesto_izdavanja_osobne_iskaznice","Mjesto izdavanja osobne iskaznice vlasnika", "text", 1),
        ("vlasnik_datum_rodenja","Datum rođenja vlasnika", "date", 1),
        ("vlasnik_funkcija","Funkcija vlasnika", "text", 1),
        ("vlasnik_udio_vlasnistva","Udio vlasništva", "number", 1),
        ("vlasnik_vrsta_vlasnistva","Vrsta vlasništva", "radio", 1),
        ("vlasnik_politicki_izlozena","Je li vlasnik politički izložena osoba?", "radio", 0),
        ("poslovni_prostor_naziv","Naziv poslovnog prostora", "text", 1),
        ("poslovni_adresa","Adresa poslovnog prostora", "text", 1),
        ("poslovni_prostor_vrsta_robe_usluga","Vrsta robe/usluga", "text", 1),
        ("poslovni_prostor_sezonska_blagajna","Sezonska blagajna:", "radio", 0),
        ("poslovni_prostor_pos_terminal","POS terminal druge institucije", "radio", 0),
        ("poslovni_prostor_banka_institucija","Naziv banke/institucije (ako je prethodno pitanje Da)", "text", 0)
    ]

    #Ako pitanje već postoji, koristi ga; ako ne postoji, doda ga automatski
    for i, (sifra, tekst, tip, obavezno) in enumerate(pitanja, start=1):

        cursor.execute("SELECT id FROM pitanja WHERE tekst = ?", (tekst,))
        postojece_pitanje = cursor.fetchone()

        if postojece_pitanje:
            pitanje_id = postojece_pitanje[0]
        else:
            cursor.execute("""
                INSERT INTO pitanja (tekst, tip_polja, obavezno)
                VALUES (?,?,?)
            """, (tekst, tip, obavezno))

            pitanje_id = cursor.lastrowid

        cursor.execute("""
            INSERT OR IGNORE INTO ugovori_pitanja (vrsta_ugovora_id, pitanje_id, redoslijed)
            VALUES (1,?,?)
        """, (pitanje_id, i))

    conn.commit()
    conn.close()

@app.route("/")
def forma():
    return render_template(
        "forma.html",
        form_action="/spremi",
        podaci={},
        dodatni_vlasnici=[],
        prodajna_mjesta=[],
        edit_mode=False,
        danas=date.today().isoformat()
    )

@app.route("/spremi", methods=["POST"])
def spremi():
    podaci = request.form

    def provjeri_datum_isteka(naziv_polja):
        datum = podaci.get(naziv_polja)

        if datum:
            datum_isteka = datetime.strptime(datum, "%Y-%m-%d").date()

            if datum_isteka <= date.today():
                return False

        return True

    if not provjeri_datum_isteka("kontakt_datum_isteka_osobne_iskaznice"):
        return "Greška: Datum isteka osobne iskaznice ovlaštene osobe mora biti nakon današnjeg datuma."

    if not provjeri_datum_isteka("vlasnik_datum_isteka_osobne_iskaznice"):
        return "Greška: Datum isteka osobne iskaznice vlasnika mora biti nakon današnjeg datuma."

    #OIB validacija
    oib = podaci.get("oib")
    if not oib or not oib.isdigit() or len(oib) != 11:
        return "Neispravan OIB. OIB mora imati 11 znamenki i sadržavati samo brojeve."

    oib_vlasnika = podaci.get("vlasnik_OIB")
    if not oib_vlasnika or not oib_vlasnika.isdigit() or len(oib_vlasnika) != 11:
        return "Neispravan OIB. OIB mora imati 11 znamenki i sadržavati samo brojeve."
    
    kontakt_oib = podaci.get("kontakt_oib")
    if not kontakt_oib or not kontakt_oib.isdigit() or len(kontakt_oib) != 11:
        return "Neispravan OIB. OIB mora imati 11 znamenki i sadržavati samo brojeve."

    # Provjera IBAN-a
    iban = podaci.get("iban", "").replace(" ", "").upper()
    if not provjeri_iban(iban):
        return "Neispravan IBAN. IBAN mora biti u formatu HR + 19 znamenki."


    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    # 1. Spremamo županiju sjedišta
    zupanija_sjedista = podaci.get("zupanija_sjedista")
    cursor.execute("INSERT OR IGNORE INTO zupanije (naziv) VALUES (?)", (zupanija_sjedista,))
    cursor.execute("SELECT id FROM zupanije WHERE naziv = ?", (zupanija_sjedista,))
    zupanija_id = cursor.fetchone()[0]

    # 2. Spremamo mjesto sjedišta
    mjesto_sjedista = podaci.get("mjesto_sjedista")
    cursor.execute("INSERT OR IGNORE INTO mjesta (naziv, postanski_broj, zupanija_id) VALUES (?, ?, ?)", (mjesto_sjedista, podaci.get("postanski_broj"), zupanija_id))
    cursor.execute("SELECT id FROM mjesta WHERE naziv = ? AND postanski_broj = ? AND zupanija_id = ?", (mjesto_sjedista, podaci.get("postanski_broj"), zupanija_id))
    mjesto_id = cursor.fetchone()[0]

    # 3. Spremamo korisnika
    cursor.execute("""
        INSERT INTO korisnici (
            ime,
            prezime,
            naziv_tvrtke,
            oib,
            datum_rodjenja,
            email,
            telefon,

            kontakt_oib,
            kontakt_adresa,
            kontakt_drzavljanstvo,
            kontakt_drugo_drzavljanstvo,
            kontakt_datum_rodenja,
            kontakt_funkcija,
            kontakt_broj_osobne_iskaznice,
            kontakt_datum_isteka_osobne_iskaznice,
            kontakt_mjesto_izdavanja_osobne_iskaznice,

            adresa,
            zupanija_id,
            mjesto_id
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        podaci.get("kontakt_ime"),
    "",
        podaci.get("naziv"),
        oib,

        podaci.get("vlasnik_datum_rodenja"),

        podaci.get("kontakt_email"),
        podaci.get("kontakt_telefon"),

        podaci.get("kontakt_oib"),
        podaci.get("kontakt_adresa"),
        podaci.get("kontakt_drzavljanstvo"),
        podaci.get("kontakt_drugo_drzavljanstvo")
            if podaci.get("kontakt_drugo_drzavljanstvo_odabir") == "Da"
            else "",
        podaci.get("kontakt_datum_rodenja"),
        podaci.get("kontakt_funkcija"),
        podaci.get("kontakt_broj_osobne_iskaznice"),
        podaci.get("kontakt_datum_isteka_osobne_iskaznice"),
        podaci.get("kontakt_mjesto_izdavanja_osobne_iskaznice"),

        podaci.get("adresa_sjedista"),
        zupanija_id,
        mjesto_id
    ))

    korisnik_id = cursor.lastrowid  # Dohvaćamo ID novog korisnika

    for i in range(1, 4):
        ime_prezime = podaci.get(f"dodatni_vlasnik_ime_{i}")
        
        if not provjeri_datum_isteka(f"dodatni_vlasnik_datum_isteka_osobne_iskaznice_{i}"):
            return f"Greška: Datum isteka osobne iskaznice dodatnog vlasnika {i} mora biti nakon današnjeg datuma."
        if ime_prezime:
            cursor.execute("""
                INSERT INTO dodatni_vlasnici (  
                    korisnik_id, ime_prezime, oib, drzavljanstvo,drugo_drzavljanstvo, drzava_prebivalista,
                    datum_rodenja, udio_vlasnistva, vrsta_vlasnistva, politicki_izlozena
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                korisnik_id,
                ime_prezime,
                podaci.get(f"dodatni_vlasnik_OIB_{i}"),
                podaci.get(f"dodatni_vlasnik_drzavljanstvo_{i}"),
                podaci.get(f"dodatni_vlasnik_drugo_drzavljanstvo_{i}") if podaci.get(f"dodatni_vlasnik_drugo_drzavljanstvo_odabir_{i}") == "Da" else "",
                podaci.get(f"dodatni_vlasnik_drzava_prebivalista_{i}"),
                podaci.get(f"dodatni_vlasnik_datum_rodenja_{i}"),
                podaci.get(f"dodatni_vlasnik_udio_{i}"),
                podaci.get(f"dodatni_vlasnik_vrsta_vlasnistva_{i}"),
                1 if podaci.get(f"dodatni_vlasnik_politicki_izlozena_{i}") == "Da" else 0
                ))
    #4. Spremamo prodajna mjesta
    for i in range(1, 5):
        naziv = podaci.get(f"prodajno_mjesto_naziv_{i}")
        if naziv:
            cursor.execute("""
                INSERT INTO prodajna_mjesta (
                    korisnik_id, naziv, adresa, kontakt_osoba, vrsta_robe_usluga, email, telefon, sezonska_blagajna
                ) VALUES (?,?,?,?,?,?,?,?)
            """, (
                korisnik_id,
                naziv,
                podaci.get(f"prodajno_mjesto_adresa_{i}"),
                podaci.get(f"prodajno_mjesto_kontakt_osoba_{i}"),
                podaci.get(f"prodajno_mjesto_vrsta_robe_usluga_{i}"),
                podaci.get(f"prodajno_mjesto_kontakt_email_{i}"),
                podaci.get(f"prodajno_mjesto_kontakt_telefon_{i}"),
                podaci.get(f"prodajno_mjesto_sezonska_{i}")
            ))

    # 5.Spremamo ugovor
    cursor.execute("""
        INSERT INTO ugovori (klijent_id, vrsta_ugovora_id, datum_potpisa)
        VALUES (?,?,DATE('now'))
    """, (korisnik_id, 1))  # Pretpostavljamo da je vrsta_ugovora_id 1 za SPU2

    ugovor_id = cursor.lastrowid  # Dohvaćamo ID novog ugovora

    # 6. Spremamo odogovre iz forme
    cursor.execute("SELECT id, tekst FROM pitanja")
    pitanja = cursor.fetchall()

    mapa={
        # TVRTKA
        "Naziv tvrtke/obrta":"naziv",
        "OIB tvrtke":"oib",
        "NKD klasifikacija":"nkdklasifikacija",
        "IBAN":"iban",
        "Matični broj":"maticni_broj",
        "Adresa sjedišta":"adresa_sjedista",
        "Prihvaćate li virtualne kartice?":"virtualne_kartice",
        "Odaberite izvor sredstava":"izvor_sredstava",
        "Izvor sredstava - ostalo":"izvor_ostalo",
        "Očekivani godišnji promet":"promet",
        "Svrha poslovnog odnosa":"svrha",
        "Svrha poslovnog odnosa - ostalo":"svrha_ostalo",

        # OVLAŠTENA OSOBA (kontakt)
        "Ime i prezime ovlaštene osobe":"kontakt_ime",
        "Email ovlaštene osobe":"kontakt_email",
        "Telefon ovlaštene osobe":"kontakt_telefon",
        "OIB ovlaštene osobe":"kontakt_oib",
        "Adresa prebivališta ovlaštene osobe":"kontakt_adresa",
        "Državljanstvo ovlaštene osobe":"kontakt_drzavljanstvo",
        "Drugo državljanstvo ovlaštene osobe": "kontakt_drugo_drzavljanstvo",
        "Datum rođenja ovlaštene osobe":"kontakt_datum_rodenja",
        "Funkcija ovlaštene osobe":"kontakt_funkcija",
        "Broj osobne iskaznice ovlaštene osobe":"kontakt_broj_osobne_iskaznice",
        "Datum isteka osobne iskaznice ovlaštene osobe":"kontakt_datum_isteka_osobne_iskaznice",
        "Mjesto izdavanja osobne iskaznice ovlaštene osobe":"kontakt_mjesto_izdavanja_osobne_iskaznice",

        # STVARNI VLASNIK
        "Ime i prezime vlasnika":"vlasnik_ime",
        "OIB vlasnika":"vlasnik_OIB",
        "Državljanstvo vlasnika":"vlasnik_drzavljanstvo",
        "Drugo državljanstvo vlasnika": "vlasnik_drugo_drzavljanstvo",
        "Država prebivališta vlasnika":"vlasnik_drzava_prebivalista",
        "Datum rođenja vlasnika":"vlasnik_datum_rodenja",
        "Udio vlasništva":"vlasnik_udio_vlasnistva",
        "Vrsta vlasništva":"vlasnik_vrsta_vlasnistva",
        "Je li vlasnik politički izložena osoba?":"vlasnik_politicki_izlozena",

        # PRODAJNO MJESTO
        "Naziv poslovnog prostora":"poslovni_prostor_naziv",
        "Adresa poslovnog prostora":"poslovni_adresa",
        "Vrsta robe/usluga":"poslovni_prostor_vrsta_robe_usluga",
        "Sezonska blagajna:":"poslovni_prostor_sezonska_blagajna",
        "POS terminal druge institucije":"poslovni_prostor_pos_terminal",
        "Naziv banke/institucije (ako je prethodno pitanje Da)":"poslovni_prostor_banka_institucija"
    }

    for pitanje_id, tekst_pitanja in pitanja:
        if tekst_pitanja == "Odaberite izvor sredstava":
            odgovor = ", ".join(podaci.getlist("izvor_sredstava"))
        elif tekst_pitanja == "Svrha poslovnog odnosa":
            odgovor = ", ".join(podaci.getlist("svrha"))
        else:
            naziv_polja = mapa.get(tekst_pitanja)

            if naziv_polja == "iban":
                odgovor = iban
            else:
                odgovor = podaci.get(naziv_polja, "") if naziv_polja else ""

        cursor.execute("""
            INSERT INTO odgovori (korisnik_id, ugovor_id, pitanje_id, odgovor)            VALUES (?,?,?,?)
        """, (korisnik_id, ugovor_id, pitanje_id, odgovor))

        
    # 7. Log
    cursor.execute("""
        INSERT INTO logovi (korisnik_id, aktivnost)
        VALUES (?,?)
    """, (korisnik_id, "Korisnik je ispunio formu i kreiran je novi ugovor"))

    conn.commit()
    conn.close()

    return """
    <h2>"Podaci su uspješno spremljeni!" <h2>
    <p>Korisnik, ugovor i odgovori su spremljeni u bazu podataka. Također je zabilježen log aktivnosti.</p>
    <a href="/">Povratak na formu</a><br>
    <a href="/admin">Pogledaj sve unose</a>
    """

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    greska = None

    if request.method == "POST":
        korisnicko_ime = request.form.get(
            "korisnicko_ime",
            ""
        ).strip()

        lozinka = request.form.get("lozinka", "")

        conn = sqlite3.connect("ugovori.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, korisnicko_ime, lozinka_hash
            FROM administratori
            WHERE korisnicko_ime = ?
        """, (korisnicko_ime,))

        administrator = cursor.fetchone()
        conn.close()

        if (
            administrator
            and check_password_hash(
                administrator[2],
                lozinka
            )
        ):
            session.clear()
            session["admin_prijavljen"] = True
            session["admin_id"] = administrator[0]
            session["admin_korisnicko_ime"] = administrator[1]

            return redirect(url_for("admin"))

        greska = "Neispravno korisničko ime ili lozinka."

    return render_template(
        "admin_login.html",
        greska=greska
    )

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_prijava_obavezna
def admin():
    oib_pretraga = request.args.get("oib", "").strip()

    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    if oib_pretraga:
        cursor.execute("""
        SELECT 
            korisnici.id,
            korisnici.naziv_tvrtke,
            korisnici.oib, 
            korisnici.email,
            korisnici.telefon, 
            zupanije.naziv AS zupanija,
            mjesta.naziv AS mjesto
        FROM korisnici
        LEFT JOIN zupanije ON korisnici.zupanija_id = zupanije.id
        LEFT JOIN mjesta ON korisnici.mjesto_id = mjesta.id
        WHERE korisnici.oib LIKE ?
        """, (f"%{oib_pretraga}%",))
    else:
        cursor.execute("""
        SELECT 
            korisnici.id,
            korisnici.naziv_tvrtke, 
            korisnici.oib,
            korisnici.email,
            korisnici.telefon,
            zupanije.naziv AS zupanija,
            mjesta.naziv AS mjesto
        FROM korisnici
        LEFT JOIN zupanije ON korisnici.zupanija_id = zupanije.id
        LEFT JOIN mjesta ON korisnici.mjesto_id = mjesta.id
        """)
    podaci = cursor.fetchall()
    conn.close()

    return render_template("admin.html", podaci=podaci, oib_pretraga=oib_pretraga)

    
@app.route("/admin/korisnik/<int:korisnik_id>")
@admin_prijava_obavezna
def admin_korisnik(korisnik_id):
    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    
    cursor.execute("""
    SELECT 
        id,
        naziv_tvrtke,
        oib,
        email,  
        telefon,
        adresa,
        kontakt_oib,
        kontakt_adresa,
        kontakt_drzavljanstvo,
        kontakt_datum_rodenja,
        kontakt_funkcija,
        kontakt_broj_osobne_iskaznice,
        kontakt_datum_isteka_osobne_iskaznice,
        kontakt_mjesto_izdavanja_osobne_iskaznice
        FROM korisnici
        WHERE id = ?
    """, (korisnik_id,))

    korisnik = cursor.fetchone()    

    cursor.execute("""
    SELECT
        pitanja.tekst,
        odgovori.odgovor
    FROM odgovori
    JOIN pitanja ON odgovori.pitanje_id = pitanja.id
    WHERE odgovori.korisnik_id = ?
    """, (korisnik_id,))

    odgovori = cursor.fetchall()

    cursor.execute("""
    SELECT
        ime_prezime,
        oib,
        datum_rodenja,
        drzavljanstvo,
        drugo_drzavljanstvo,
        drzava_prebivalista,
        vrsta_vlasnistva,
        udio_vlasnistva,
        politicki_izlozena
    FROM dodatni_vlasnici
    WHERE korisnik_id = ?
    """, (korisnik_id,))
   
    dodatni_vlasnici = cursor.fetchall()

    cursor.execute("""
    SELECT
        naziv,
        adresa,
        kontakt_osoba,
        vrsta_robe_usluga,
        email,
        telefon,
        sezonska_blagajna
    FROM prodajna_mjesta
    WHERE korisnik_id = ?
    """, (korisnik_id,))

    prodajna_mjesta = cursor.fetchall()

    conn.close()


    return render_template(
        "admin_korisnik.html",
        korisnik=korisnik,
        odgovori=odgovori,
        dodatni_vlasnici=dodatni_vlasnici,
        prodajna_mjesta=prodajna_mjesta
    )

@app.route("/admin/korisnik/<int:korisnik_id>/uredi")
@admin_prijava_obavezna
def uredi_korisnika(korisnik_id):
    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pitanja.tekst, odgovori.odgovor
        FROM odgovori
        JOIN pitanja ON odgovori.pitanje_id = pitanja.id
        WHERE odgovori.korisnik_id = ?
    """, (korisnik_id,))
    odgovori = cursor.fetchall()

    podaci = {}
    mapa_obrnuto = {
        "Naziv tvrtke/obrta": "naziv",
        "OIB tvrtke": "oib",
        "NKD klasifikacija": "nkdklasifikacija",
        "IBAN": "iban",
        "Matični broj": "maticni_broj",
        "Adresa sjedišta": "adresa_sjedista",
        "Prihvaćate li virtualne kartice?": "virtualne_kartice",
        "Odaberite izvor sredstava": "izvor_sredstava",
        "Izvor sredstava - ostalo": "izvor_ostalo",
        "Očekivani godišnji promet": "promet",
        "Svrha poslovnog odnosa": "svrha",
        "Svrha poslovnog odnosa - ostalo": "svrha_ostalo",

        "Ime i prezime ovlaštene osobe": "kontakt_ime",
        "Email ovlaštene osobe": "kontakt_email",
        "Telefon ovlaštene osobe": "kontakt_telefon",
        "OIB ovlaštene osobe": "kontakt_oib",
        "Adresa prebivališta ovlaštene osobe": "kontakt_adresa",
        "Državljanstvo ovlaštene osobe": "kontakt_drzavljanstvo",
        "Drugo državljanstvo ovlaštene osobe": "kontakt_drugo_drzavljanstvo",
        "Datum rođenja ovlaštene osobe": "kontakt_datum_rodenja",
        "Funkcija ovlaštene osobe": "kontakt_funkcija",
        "Broj osobne iskaznice ovlaštene osobe": "kontakt_broj_osobne_iskaznice",
        "Datum isteka osobne iskaznice ovlaštene osobe": "kontakt_datum_isteka_osobne_iskaznice",
        "Mjesto izdavanja osobne iskaznice ovlaštene osobe": "kontakt_mjesto_izdavanja_osobne_iskaznice",

        "Ime i prezime vlasnika": "vlasnik_ime",
        "OIB vlasnika": "vlasnik_OIB",
        "Državljanstvo vlasnika": "vlasnik_drzavljanstvo",
        "Drugo državljanstvo vlasnika": "vlasnik_drugo_drzavljanstvo",
        "Država prebivališta vlasnika": "vlasnik_drzava_prebivalista",
        "Datum rođenja vlasnika": "vlasnik_datum_rodenja",
        "Udio vlasništva": "vlasnik_udio_vlasnistva",
        "Vrsta vlasništva": "vlasnik_vrsta_vlasnistva",
        "Je li vlasnik politički izložena osoba?": "vlasnik_politicki_izlozena",
    }

    for tekst, odgovor in odgovori:
        if tekst in mapa_obrnuto:
            podaci[mapa_obrnuto[tekst]] = odgovor

    cursor.execute("""
        SELECT
            zupanije.naziv,
            mjesta.naziv,
            mjesta.postanski_broj
        FROM korisnici
        LEFT JOIN zupanije ON korisnici.zupanija_id = zupanije.id
        LEFT JOIN mjesta ON korisnici.mjesto_id = mjesta.id
        WHERE korisnici.id = ?
    """, (korisnik_id,))

    lokacija = cursor.fetchone()

    if lokacija:
        podaci["zupanija_sjedista"] = lokacija[0] or ""
        podaci["mjesto_sjedista"] = lokacija[1] or ""
        podaci["postanski_broj"] = lokacija[2] or ""

    cursor.execute("""
        SELECT ime_prezime, oib, datum_rodenja, drzavljanstvo,
               drugo_drzavljanstvo, drzava_prebivalista,
               vrsta_vlasnistva, udio_vlasnistva, politicki_izlozena
        FROM dodatni_vlasnici
        WHERE korisnik_id = ?
        ORDER BY id
    """, (korisnik_id,))
    dodatni_vlasnici = cursor.fetchall()

    cursor.execute("""
        SELECT naziv, adresa, kontakt_osoba, telefon, email,
               vrsta_robe_usluga, sezonska_blagajna
        FROM prodajna_mjesta
        WHERE korisnik_id = ?
        ORDER BY id
    """, (korisnik_id,))
    prodajna_mjesta = cursor.fetchall()

    conn.close()

    return render_template(
        "forma.html",
        form_action=f"/admin/korisnik/{korisnik_id}/uredi/spremi",
        podaci=podaci,
        dodatni_vlasnici=dodatni_vlasnici,
        prodajna_mjesta=prodajna_mjesta,
        edit_mode=True,
        korisnik_id=korisnik_id
    )

@app.route("/admin/korisnik/<int:korisnik_id>/uredi/spremi", methods=["POST"])
@admin_prijava_obavezna
def spremi_uredenog_korisnika(korisnik_id):
    podaci = request.form

    # OIB validacija
    oib = podaci.get("oib", "").strip()
    kontakt_oib = podaci.get("kontakt_oib", "").strip()
    vlasnik_oib = podaci.get("vlasnik_OIB", "").strip()

    if not oib.isdigit() or len(oib) != 11:
        return "Neispravan OIB tvrtke."

    if not kontakt_oib.isdigit() or len(kontakt_oib) != 11:
        return "Neispravan OIB kontakt osobe."

    if not vlasnik_oib.isdigit() or len(vlasnik_oib) != 11:
        return "Neispravan OIB vlasnika."

    # IBAN validacija
    iban = podaci.get("iban", "").replace(" ", "").upper()

    if not provjeri_iban(iban):
        return "Neispravan IBAN. IBAN mora biti u formatu HR + 19 znamenki."

    # Datum isteka osobne iskaznice kontakt osobe
    datum_isteka = podaci.get("kontakt_datum_isteka_osobne_iskaznice", "")

    if datum_isteka:
        try:
            datum_isteka_obj = datetime.strptime(
                datum_isteka,
                "%Y-%m-%d"
            ).date()

            if datum_isteka_obj <= date.today():
                return (
                    "Datum isteka osobne iskaznice kontakt osobe "
                    "mora biti nakon današnjeg datuma."
                )

        except ValueError:
            return "Datum isteka osobne iskaznice nije ispravan."

    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    try:
        # Županija
        zupanija_sjedista = podaci.get("zupanija_sjedista", "").strip()

        cursor.execute(
            "INSERT OR IGNORE INTO zupanije (naziv) VALUES (?)",
            (zupanija_sjedista,)
        )

        cursor.execute(
            "SELECT id FROM zupanije WHERE naziv = ?",
            (zupanija_sjedista,)
        )

        zupanija = cursor.fetchone()

        if not zupanija:
            return "Županija nije pronađena."

        zupanija_id = zupanija[0]

        # Mjesto
        mjesto_sjedista = podaci.get("mjesto_sjedista", "").strip()
        postanski_broj = podaci.get("postanski_broj", "").strip()

        cursor.execute("""
            INSERT OR IGNORE INTO mjesta (
                naziv,
                postanski_broj,
                zupanija_id
            )
            VALUES (?, ?, ?)
        """, (
            mjesto_sjedista,
            postanski_broj,
            zupanija_id
        ))

        cursor.execute("""
            SELECT id
            FROM mjesta
            WHERE naziv = ?
              AND postanski_broj = ?
              AND zupanija_id = ?
        """, (
            mjesto_sjedista,
            postanski_broj,
            zupanija_id
        ))

        mjesto = cursor.fetchone()

        if not mjesto:
            return "Mjesto nije pronađeno."

        mjesto_id = mjesto[0]

        kontakt_drugo_drzavljanstvo = ""

        if podaci.get("kontakt_drugo_drzavljanstvo_odabir") == "Da":
            kontakt_drugo_drzavljanstvo = podaci.get(
                "kontakt_drugo_drzavljanstvo", ""
            )

        # Ažuriranje tablice korisnici
        cursor.execute("""
            UPDATE korisnici
            SET
                ime = ?,
                naziv_tvrtke = ?,
                oib = ?,
                datum_rodjenja = ?,
                email = ?,
                telefon = ?,
                kontakt_oib = ?,
                kontakt_adresa = ?,
                kontakt_drzavljanstvo = ?,
                kontakt_drugo_drzavljanstvo = ?,
                kontakt_datum_rodenja = ?,
                kontakt_funkcija = ?,
                kontakt_broj_osobne_iskaznice = ?,
                kontakt_datum_isteka_osobne_iskaznice = ?,
                kontakt_mjesto_izdavanja_osobne_iskaznice = ?,
                adresa = ?,
                zupanija_id = ?,
                mjesto_id = ?
            WHERE id = ?
        """, (
            podaci.get("kontakt_ime", ""),
            podaci.get("naziv", ""),
            oib,
            podaci.get("vlasnik_datum_rodenja", ""),
            podaci.get("kontakt_email", ""),
            podaci.get("kontakt_telefon", ""),
            kontakt_oib,
            podaci.get("kontakt_adresa", ""),
            podaci.get("kontakt_drzavljanstvo", ""),
            kontakt_drugo_drzavljanstvo,
            podaci.get("kontakt_datum_rodenja", ""),
            podaci.get("kontakt_funkcija", ""),
            podaci.get("kontakt_broj_osobne_iskaznice", ""),
            podaci.get(
                "kontakt_datum_isteka_osobne_iskaznice", ""
            ),
            podaci.get(
                "kontakt_mjesto_izdavanja_osobne_iskaznice", ""
            ),
            podaci.get("adresa_sjedista", ""),
            zupanija_id,
            mjesto_id,
            korisnik_id
        ))

        # Dohvati ugovor korisnika
        cursor.execute("""
            SELECT id
            FROM ugovori
            WHERE klijent_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (korisnik_id,))

        ugovor = cursor.fetchone()
        ugovor_id = ugovor[0] if ugovor else None

        # Mapa pitanja i polja forme
        mapa = {
            "Naziv tvrtke/obrta": "naziv",
            "OIB tvrtke": "oib",
            "NKD klasifikacija": "nkdklasifikacija",
            "IBAN": "iban",
            "Matični broj": "maticni_broj",
            "Adresa sjedišta": "adresa_sjedista",
            "Prihvaćate li virtualne kartice?": "virtualne_kartice",
            "Odaberite izvor sredstava": "izvor_sredstava",
            "Izvor sredstava - ostalo": "izvor_ostalo",
            "Očekivani godišnji promet": "promet",
            "Svrha poslovnog odnosa": "svrha",
            "Svrha poslovnog odnosa - ostalo": "svrha_ostalo",

            "Ime i prezime ovlaštene osobe": "kontakt_ime",
            "Email ovlaštene osobe": "kontakt_email",
            "Telefon ovlaštene osobe": "kontakt_telefon",
            "OIB ovlaštene osobe": "kontakt_oib",
            "Adresa prebivališta ovlaštene osobe": "kontakt_adresa",
            "Državljanstvo ovlaštene osobe":
                "kontakt_drzavljanstvo",
            "Drugo državljanstvo ovlaštene osobe":
                "kontakt_drugo_drzavljanstvo",
            "Datum rođenja ovlaštene osobe":
                "kontakt_datum_rodenja",
            "Funkcija ovlaštene osobe": "kontakt_funkcija",
            "Broj osobne iskaznice ovlaštene osobe":
                "kontakt_broj_osobne_iskaznice",
            "Datum isteka osobne iskaznice ovlaštene osobe":
                "kontakt_datum_isteka_osobne_iskaznice",
            "Mjesto izdavanja osobne iskaznice ovlaštene osobe":
                "kontakt_mjesto_izdavanja_osobne_iskaznice",

            "Ime i prezime vlasnika": "vlasnik_ime",
            "OIB vlasnika": "vlasnik_OIB",
            "Državljanstvo vlasnika": "vlasnik_drzavljanstvo",
            "Drugo državljanstvo vlasnika":
                "vlasnik_drugo_drzavljanstvo",
            "Država prebivališta vlasnika":
                "vlasnik_drzava_prebivalista",
            "Datum rođenja vlasnika": "vlasnik_datum_rodenja",
            "Udio vlasništva": "vlasnik_udio_vlasnistva",
            "Vrsta vlasništva": "vlasnik_vrsta_vlasnistva",
            "Je li vlasnik politički izložena osoba?":
                "vlasnik_politicki_izlozena"
        }

        cursor.execute("SELECT id, tekst FROM pitanja")
        pitanja = cursor.fetchall()

        for pitanje_id, tekst_pitanja in pitanja:
            if tekst_pitanja == "Odaberite izvor sredstava":
                odgovor = ", ".join(
                    podaci.getlist("izvor_sredstava")
                )
            elif tekst_pitanja == "Svrha poslovnog odnosa":
                odgovor = ", ".join(podaci.getlist("svrha"))
            elif tekst_pitanja == "IBAN":
                odgovor = iban
            elif tekst_pitanja == (
                "Drugo državljanstvo ovlaštene osobe"
            ):
                odgovor = kontakt_drugo_drzavljanstvo
            else:
                naziv_polja = mapa.get(tekst_pitanja)
                odgovor = (
                    podaci.get(naziv_polja, "")
                    if naziv_polja
                    else ""
                )

            cursor.execute("""
                SELECT id
                FROM odgovori
                WHERE korisnik_id = ?
                  AND pitanje_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (
                korisnik_id,
                pitanje_id
            ))

            postojeci_odgovor = cursor.fetchone()

            if postojeci_odgovor:
                cursor.execute("""
                    UPDATE odgovori
                    SET odgovor = ?
                    WHERE id = ?
                """, (
                    odgovor,
                    postojeci_odgovor[0]
                ))
            elif ugovor_id:
                cursor.execute("""
                    INSERT INTO odgovori (
                        korisnik_id,
                        ugovor_id,
                        pitanje_id,
                        odgovor
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    korisnik_id,
                    ugovor_id,
                    pitanje_id,
                    odgovor
                ))

        # Najjednostavnije ažuriranje dodatnih vlasnika:
        # obriši stare i ponovno spremi podatke iz forme
        cursor.execute(
            "DELETE FROM dodatni_vlasnici WHERE korisnik_id = ?",
            (korisnik_id,)
        )

        for i in range(1, 4):
            ime_prezime = podaci.get(
                f"dodatni_vlasnik_ime_{i}", ""
            ).strip()

            if ime_prezime:
                drugo_drzavljanstvo = ""

                if podaci.get(
                    f"dodatni_vlasnik_drugo_drzavljanstvo_odabir_{i}"
                ) == "Da":
                    drugo_drzavljanstvo = podaci.get(
                        f"dodatni_vlasnik_drugo_drzavljanstvo_{i}",
                        ""
                    )

                cursor.execute("""
                    INSERT INTO dodatni_vlasnici (
                        korisnik_id,
                        ime_prezime,
                        oib,
                        drzavljanstvo,
                        drugo_drzavljanstvo,
                        drzava_prebivalista,
                        datum_rodenja,
                        udio_vlasnistva,
                        vrsta_vlasnistva,
                        politicki_izlozena
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    korisnik_id,
                    ime_prezime,
                    podaci.get(f"dodatni_vlasnik_OIB_{i}", ""),
                    podaci.get(
                        f"dodatni_vlasnik_drzavljanstvo_{i}", ""
                    ),
                    drugo_drzavljanstvo,
                    podaci.get(
                        f"dodatni_vlasnik_drzava_prebivalista_{i}",
                        ""
                    ),
                    podaci.get(
                        f"dodatni_vlasnik_datum_rodenja_{i}",
                        ""
                    ),
                    podaci.get(f"dodatni_vlasnik_udio_{i}", ""),
                    podaci.get(
                        f"dodatni_vlasnik_vrsta_vlasnistva_{i}",
                        ""
                    ),
                    1 if podaci.get(
                        f"dodatni_vlasnik_politicki_izlozena_{i}"
                    ) == "Da" else 0
                ))

        # Prodajna mjesta: obriši stare i ponovno spremi
        cursor.execute(
            "DELETE FROM prodajna_mjesta WHERE korisnik_id = ?",
            (korisnik_id,)
        )

        for i in range(1, 5):
            naziv = podaci.get(
                f"prodajno_mjesto_naziv_{i}", ""
            ).strip()

            if naziv:
                cursor.execute("""
                    INSERT INTO prodajna_mjesta (
                        korisnik_id,
                        naziv,
                        adresa,
                        kontakt_osoba,
                        vrsta_robe_usluga,
                        email,
                        telefon,
                        sezonska_blagajna
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    korisnik_id,
                    naziv,
                    podaci.get(
                        f"prodajno_mjesto_adresa_{i}", ""
                    ),
                    podaci.get(
                        f"prodajno_mjesto_kontakt_osoba_{i}", ""
                    ),
                    podaci.get(
                        f"prodajno_mjesto_vrsta_robe_usluga_{i}",
                        ""
                    ),
                    podaci.get(
                        f"prodajno_mjesto_kontakt_email_{i}", ""
                    ),
                    podaci.get(
                        f"prodajno_mjesto_kontakt_telefon_{i}", ""
                    ),
                    podaci.get(
                        f"prodajno_mjesto_sezonska_{i}", ""
                    )
                ))

        cursor.execute("""
            INSERT INTO logovi (korisnik_id, aktivnost)
            VALUES (?, ?)
        """, (
            korisnik_id,
            "Administrator je uredio podatke korisnika"
        ))

        conn.commit()

    except sqlite3.Error as greska:
        conn.rollback()
        return f"Greška pri ažuriranju baze: {greska}"

    finally:
        conn.close()

    return render_template("uspjeh.html", korisnik_id=korisnik_id)
@app.route("/admin/korisnik/<int:korisnik_id>/obrisi", methods=["POST"])
@admin_prijava_obavezna
def obrisi_korisnika(korisnik_id):
    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    try:
        # Dohvati ugovore korisnika
        cursor.execute("""
            SELECT id
            FROM ugovori
            WHERE klijent_id = ?
        """, (korisnik_id,))
        ugovor_ids = [red[0] for red in cursor.fetchall()]

        # Obriši odgovore
        cursor.execute("""
            DELETE FROM odgovori
            WHERE korisnik_id = ?
        """, (korisnik_id,))

        # Obriši predloške vezane uz ugovore
        for ugovor_id in ugovor_ids:
            cursor.execute("""
                DELETE FROM predlosci
                WHERE ugovor_id = ?
            """, (ugovor_id,))

        # Obriši ugovore
        cursor.execute("""
            DELETE FROM ugovori
            WHERE klijent_id = ?
        """, (korisnik_id,))

        # Obriši dodatne vlasnike
        cursor.execute("""
            DELETE FROM dodatni_vlasnici
            WHERE korisnik_id = ?
        """, (korisnik_id,))

        # Obriši prodajna mjesta
        cursor.execute("""
            DELETE FROM prodajna_mjesta
            WHERE korisnik_id = ?
        """, (korisnik_id,))

        # Obriši logove
        cursor.execute("""
            DELETE FROM logovi
            WHERE korisnik_id = ?
        """, (korisnik_id,))

        # Na kraju obriši korisnika
        cursor.execute("""
            DELETE FROM korisnici
            WHERE id = ?
        """, (korisnik_id,))

        conn.commit()

    except sqlite3.Error as greska:
        conn.rollback()
        return f"Greška pri brisanju korisnika: {greska}"

    finally:
        conn.close()

    return """
        <h2>Korisnik je uspješno obrisan.</h2>
        <a href="/admin">Nazad na pregled korisnika</a>
    """

@app.route("/generiraj_spu2/<int:korisnik_id>/")
@admin_prijava_obavezna
def generiraj_spu2_za_korisnika(korisnik_id):
    from pdf_generator import generiraj_spu2

    conn = sqlite3.connect("ugovori.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
            korisnici.naziv_tvrtke,
            korisnici.oib,
            korisnici.email,
            korisnici.telefon,
            korisnici.adresa,
            mjesta.naziv,
            mjesta.postanski_broj,
            korisnici.ime,
            korisnici.kontakt_oib,
            korisnici.kontakt_adresa,
            korisnici.kontakt_drzavljanstvo,
            korisnici.kontakt_drugo_drzavljanstvo,
            korisnici.kontakt_datum_rodenja,
            korisnici.kontakt_funkcija,
            korisnici.kontakt_broj_osobne_iskaznice,
            korisnici.kontakt_datum_isteka_osobne_iskaznice,
            korisnici.kontakt_mjesto_izdavanja_osobne_iskaznice
        FROM korisnici
        Left JOIN mjesta ON korisnici.mjesto_id = mjesta.id
        WHERE korisnici.id = ?
    """, (korisnik_id,))

    korisnik = cursor.fetchone()

    cursor.execute("""
    SELECT pitanja.tekst, odgovori.odgovor
        FROM odgovori
        JOIN pitanja ON odgovori.pitanje_id = pitanja.id
        WHERE odgovori.korisnik_id = ?
    """, (korisnik_id,))

    odgovori = cursor.fetchall()

    cursor.execute("""
    SELECT
        ime_prezime,
        oib,
        datum_rodenja,
        drzavljanstvo,
        drugo_drzavljanstvo,
        drzava_prebivalista,
        vrsta_vlasnistva,   
        politicki_izlozena,
        udio_vlasnistva
    FROM dodatni_vlasnici
    WHERE korisnik_id=?
    """, (korisnik_id,)
    )
    dodatni_vlasnici = cursor.fetchall()
    
    cursor.execute("""
    SELECT
        naziv,
        adresa, 
        kontakt_osoba,
        telefon,
        email,
        vrsta_robe_usluga,
        sezonska_blagajna
    FROM prodajna_mjesta
    WHERE korisnik_id=?
    ORDER BY id
    """, (korisnik_id,)
    )
    prodajna_mjesta = cursor.fetchall()

    conn.close()

    podaci = {
        "naziv": korisnik[0],
        "oib": korisnik[1],
        "kontakt_email": korisnik[2],
        "kontakt_telefon": korisnik[3],
        "adresa_sjedista": korisnik[4],
        "mjesto_sjedista": korisnik[5],
        "postanski_broj": korisnik[6],
        "kontakt_ime": korisnik[7],
        "kontakt_oib": korisnik[8],
        "kontakt_adresa": korisnik[9],
        "kontakt_drzavljanstvo": korisnik[10],
        "kontakt_drugo_drzavljanstvo": korisnik[11],
        "kontakt_datum_rodenja": korisnik[12],
        "kontakt_funkcija": korisnik[13],
        "kontakt_broj_osobne_iskaznice": korisnik[14],
        "kontakt_datum_isteka_osobne_iskaznice": korisnik[15],
        "kontakt_mjesto_izdavanja_osobne_iskaznice": korisnik[16],
        "dodatni_vlasnici": dodatni_vlasnici,
        "prodajna_mjesta": prodajna_mjesta
    }

    mapa = {
        
        # TVRTKA
        "Naziv tvrtke/obrta": "naziv",
        "OIB tvrtke": "oib",
        "NKD klasifikacija": "nkdklasifikacija",
        "IBAN": "iban",
        "Matični broj": "maticni_broj",
        "Adresa sjedišta": "adresa_sjedista",
        "Prihvaćate li virtualne kartice?": "virtualne_kartice",
        "Odaberite izvor sredstava": "izvor_sredstava",
        "Izvor sredstava - ostalo": "izvor_ostalo",
        "Očekivani godišnji promet": "promet",
        "Svrha poslovnog odnosa": "svrha",
        "Svrha poslovnog odnosa - ostalo": "svrha_ostalo",

        # ZAKONSKI ZASTUPNIK (kontakt osoba)
        "Ime i prezime ovlaštene osobe": "kontakt_ime",
        "OIB ovlaštene osobe": "kontakt_oib",
        "Adresa prebivališta ovlaštene osobe": "kontakt_adresa",
        "Državljanstvo ovlaštene osobe": "kontakt_drzavljanstvo",
        "Drugo državljanstvo ovlaštene osobe": "kontakt_drugo_drzavljanstvo",
        "Telefon ovlaštene osobe": "kontakt_telefon",
        "Email ovlaštene osobe": "kontakt_email",
        "Datum rođenja ovlaštene osobe": "kontakt_datum_rodenja",
        "Funkcija ovlaštene osobe": "kontakt_funkcija",
        "Broj osobne iskaznice ovlaštene osobe": "kontakt_broj_osobne_iskaznice",
        "Datum isteka osobne iskaznice ovlaštene osobe": "kontakt_datum_isteka_osobne_iskaznice",
        "Mjesto izdavanja osobne iskaznice ovlaštene osobe": "kontakt_mjesto_izdavanja_osobne_iskaznice",

        # STVARNI VLASNIK
        "Ime i prezime vlasnika": "vlasnik_ime",
        "OIB vlasnika": "vlasnik_OIB",
        "Državljanstvo vlasnika": "vlasnik_drzavljanstvo",
        "Drugo državljanstvo vlasnika": "vlasnik_drugo_drzavljanstvo",
        "Država prebivališta vlasnika": "vlasnik_drzava_prebivalista",
        "Datum rođenja vlasnika": "vlasnik_datum_rodenja",
        "Udio vlasništva": "vlasnik_udio_vlasnistva",
        "Vrsta vlasništva": "vlasnik_vrsta_vlasnistva",
        "Jeste li politički izložena osoba?": "vlasnik_politicki_izlozena",

        # PRODAJNO MJESTO
        "Naziv poslovnog prostora": "poslovni_prostor_naziv",
        "Adresa poslovnog prostora": "poslovni_adresa",
        "Vrsta robe/usluga": "poslovni_prostor_vrsta_robe_usluga",
        "Sezonska blagajna:": "poslovni_prostor_sezonska_blagajna",
        "POS terminal druge institucije": "poslovni_prostor_pos_terminal",
        "Naziv banke/institucije (ako je prethodno pitanje Da)": "poslovni_prostor_banka_institucija"
    }

    for tekst_pitanja, odgovor in odgovori:
        if tekst_pitanja in mapa:
            podaci[mapa[tekst_pitanja]] = odgovor
    

    putanja = generiraj_spu2(podaci, podaci["oib"])

    return send_file(putanja, as_attachment=True)

if __name__ == "__main__":
    kreiraj_bazu()



    unesi_pocetne_podatke()

    app.run(debug=True)