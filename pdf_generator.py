from pypdf import PdfReader, PdfWriter
from datetime import datetime

def formatiraj_datum(datum):
    if not datum:
        return ""

    try:
        parsed_date = datetime.strptime(datum, "%Y-%m-%d")
        return parsed_date.strftime("%d.%m.%Y.")
    except ValueError:
        return datum
    return ""

def generiraj_spu2(podaci, oib):
    
    predlozak = "pdf_predlosci/SPU2.pdf"
    izlaz = f"generated/SPU2_{oib}.pdf"

    # Učitavanje PDF predloška
    reader = PdfReader(predlozak)
    writer = PdfWriter()

    writer.clone_document_from_reader(reader)

    adresa_i_mjesto = podaci.get("adresa_sjedista","")
    if podaci.get("mjesto_sjedista"):
        adresa_i_mjesto += ", " + podaci.get("mjesto_sjedista")

    polja = {
        "A 1": podaci.get("naziv", ""),
        "A 5": adresa_i_mjesto,
        "A 6": podaci.get("postanski_broj", ""),
        "A 7": podaci.get("oib", ""),
        "A 8": podaci.get("maticni_broj", ""),
        "A 10": podaci.get("nkdklasifikacija", ""),
        "A 12": podaci.get("kontakt_telefon", ""),
        "A 14": podaci.get("kontakt_email", ""),
        "A 15": podaci.get("iban", ""),

        "A 39": podaci.get("kontakt_ime", ""),
        "A 40": podaci.get("kontakt_oib", ""),
        "A 41": podaci.get("kontakt_funkcija", ""),
        "A 42": formatiraj_datum(podaci.get("kontakt_datum_rodenja", "")),
        "A 43": podaci.get("kontakt_email", ""),
        "A 44": podaci.get("kontakt_telefon", ""),
        "A 45": podaci.get("kontakt_adresa", ""),
        "A 46": podaci.get("kontakt_drzavljanstvo", ""),
        "A 47": podaci.get("kontakt_drugo_drzavljanstvo", ""),
        "A 48": podaci.get("kontakt_broj_osobne_iskaznice", ""),
        "A 49": podaci.get("kontakt_mjesto_izdavanja_osobne_iskaznice", ""),
        "A 50": formatiraj_datum(podaci.get("kontakt_datum_isteka_osobne_iskaznice", ""))
    }

    #Virtualne valute/kartice
    if podaci.get("virtualne_kartice") == "Da":
        polja["A 17"] = "/Yes"
    elif podaci.get("virtualne_kartice") == "Ne":
        polja["A 18"] = "/Yes"
    
    #Izvor sredstava
    izvor = podaci.get("izvor_sredstava","")
    if "Redovito poslovanje" in izvor:
        polja["A 19"] = "/Yes"
    if "Sredstva vlasnika/osnivača" in izvor:
        polja["A 20"] = "/Yes"
    if "Kredit/sredstva iz EU fondova" in izvor:
        polja["A 21"] = "/Yes"
    if "Ostalo" in izvor:
        polja["A 22"] = "/Yes"
        polja["A 23"] = podaci.get("izvor_ostalo","")
    
    #Očekivani godišnji promet
    promet = podaci.get("promet","")
    if promet == "0-5000":
        polja["A 24"] = "/Yes"
    elif promet == "5001-20000":
        polja["A 25"] = "/Yes"
    elif promet == "20001-50000":
        polja["A 26"] = "/Yes"
    elif promet == "50001-100000":
        polja["A 27"] = "/Yes"
    elif promet == "100001-200000":
        polja["A 28"] = "/Yes"
    elif promet == "Vise od 200000":
        polja["A 29"] = "/Yes"

    #Svrha poslovnog odnosa
    svrha = podaci.get("svrha","")
    if "Naplata roba i usluga" in svrha:
        polja["A 30"] = "/Yes"
    if "Donacije" in svrha:
        polja["A 31"] = "/Yes"
    if "Ostalo" in svrha:
        polja["A 32"] = "/Yes"
        polja["A 33"] = podaci.get("svrha_ostalo","")
    
    #Stvarni vlasnik - glavni vlasnik, 1. blok na stranici 2
    polja.update({
        "B3":podaci.get("vlasnik_ime",""),
        "B4":podaci.get("vlasnik_OIB",""),
        "B5": formatiraj_datum(podaci.get("vlasnik_datum_rodenja","")),
        "B6":podaci.get("vlasnik_drzavljanstvo",""),
        "B7": podaci.get("vlasnik_drugo_drzavljanstvo", ""),
        "B8": podaci.get("vlasnik_drzava_prebivalista",""),
        "B11": "/Yes" if podaci.get("vlasnik_vrsta_vlasnistva") == "Izravni" else "",
        "B12": "/Yes" if podaci.get("vlasnik_vrsta_vlasnistva") == "Neizravni" else "",
        "B13": "/Yes" if podaci.get("vlasnik_vrsta_vlasnistva") == "Kontrolni položaj" else "",
        "B14": "A",
        "B15":podaci.get("vlasnik_udio_vlasnistva",""),
        })

    prodajna_mjesta = podaci.get("prodajna_mjesta",[])
    blokovi_prodajna_mjesta = [
        {
            "naziv": "C25",
            "adresa": "C26",
            "kontakt": "C27",
            "telefon": "C28",
            "vrsta": "C29",
            "email": "C30",
            "pos_druga_institucija": "C31",
            "premium": "C37",
            "internet_da": "C41",
            "sezonska": "C42",
            "napojnica_da": "C44"
        },
        {
            "naziv": "C48",
            "adresa": "C49",
            "kontakt": "C50",
            "telefon": "C51",
            "vrsta": "C52",
            "email": "C53",
            "pos_druga_institucija": "C54",
            "premium": "C60",
            "sezonska": "C65",
            "internet_da": "C64",
            "napojnica_da": "C67"
        }
    ]
    for i, mjesto in enumerate(prodajna_mjesta[:2]):
        naziv, adresa, kontakt_osoba, telefon, email, vrsta_robe_usluga, sezonska = mjesto
        blok = blokovi_prodajna_mjesta[i]

        polja[blok["naziv"]] = naziv or ""
        polja[blok["adresa"]] = adresa or ""
        polja[blok["kontakt"]] = kontakt_osoba or ""
        polja[blok["telefon"]] = telefon or ""
        polja[blok["email"]] = email or ""
        polja[blok["vrsta"]] = vrsta_robe_usluga or ""
        polja[blok["pos_druga_institucija"]] = podaci.get("poslovni_prostor_banka_institucija", "Ne")
        polja[blok["premium"]] = "/Yes"
        polja[blok["sezonska"]] = "Da" if sezonska == "Da" else "Ne"
        polja[blok["internet_da"]] = "Da" 
        polja[blok["napojnica_da"]] = "/Yes"

    if podaci.get("vlasnik_politicki_izlozena") == "Da":
        polja["B9"] = "/Yes"
    else:
        polja["B10"] = "/Yes"
    
    #Dodatni vlasnici 
    dodatni_vlasnici = podaci.get("dodatni_vlasnici",[])

    blokovi = [
        {
            "ime": "B16",
            "oib": "B17",
            "datum_rodenja": "B18",
            "drzavljanstvo": "B19",
            "drugo_drzavljanstvo": "B20",
            "mjesto": "B21",
            "politicki_da": "B22",
            "politicki_ne": "B23",
            "vlasnistvo_izravni": "B24",
            "vlasnistvo_neizravni": "B25",
            "vlasnistvo_kontrolni": "B26",
            "tip_vlasnistva": "B27",
            "udio": "B28"
        },
        {
            "ime": "B29",
            "oib": "B30",
            "datum_rodenja": "B31",
            "drzavljanstvo": "B32",
            "drugo_drzavljanstvo": "B33",
            "mjesto": "B34",
            "politicki_da": "B35",
            "politicki_ne": "B36",
            "vlasnistvo_izravni": "B37",
            "vlasnistvo_neizravni": "B38",
            "vlasnistvo_kontrolni": "B39",
            "tip_vlasnistva": "B40",
            "udio": "B41"
        },
        {
            "ime": "B42",
            "oib": "B43",
            "datum_rodenja": "B44",
            "drzavljanstvo": "B45",
            "drugo_drzavljanstvo": "B46",
            "mjesto": "B47",
            "politicki_da": "B48",
            "politicki_ne": "B49",
            "vlasnistvo_izravni": "B50",
            "vlasnistvo_neizravni": "B51",
            "vlasnistvo_kontrolni": "B52",
            "tip_vlasnistva": "B53",
            "udio": "B54"
        },
        {
            "ime": "B55",
            "oib": "B56",
            "datum_rodenja": "B57",
            "drzavljanstvo": "B58",
            "drugo_drzavljanstvo": "B59",
            "mjesto": "B60",
            "politicki_da": "B61",
            "politicki_ne": "B62",
            "udio": "B67"
        }
    ]

    for i, vlasnik in enumerate(dodatni_vlasnici[:4]):
        ime, oib, datum_rodenja, drzavljanstvo, drugo_drzavljanstvo, drzava_prebivalista, vrsta_vlasnistva, politicki, udio = vlasnik
        blok = blokovi[i]

        polja[blok["ime"]] = ime or ""
        polja[blok["oib"]] = oib or ""
        polja[blok["datum_rodenja"]] = formatiraj_datum(datum_rodenja)
        polja[blok["drzavljanstvo"]] = drzavljanstvo or ""
        polja[blok["drugo_drzavljanstvo"]] = drugo_drzavljanstvo or ""
        polja[blok["mjesto"]] = drzava_prebivalista or ""

        polja[blok["udio"]] = str(udio or "")

        if politicki == 1:
            polja[blok["politicki_da"]] = "/Yes"
        else:
            polja[blok["politicki_ne"]] = "/Yes"

        if vrsta_vlasnistva == "Izravni":
            polja[blok["vlasnistvo_izravni"]] = "/Yes"  
        elif vrsta_vlasnistva == "Neizravni":
            polja[blok["vlasnistvo_neizravni"]] = "/Yes"    
        elif vrsta_vlasnistva == "Kontrolni položaj":
            polja[blok["vlasnistvo_kontrolni"]] = "/Yes"

        polja[blok["tip_vlasnistva"]] = "A"

    for page in writer.pages:
        writer.update_page_form_field_values(
            page,
            polja,
            auto_regenerate=True
        )

    with open(izlaz,"wb") as output_file:
        writer.write(output_file)

    return izlaz





