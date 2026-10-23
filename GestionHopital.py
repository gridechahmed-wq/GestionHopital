import sqlite3
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime
from tkinter import ttk


# =====================================================================
# ÉTAPE 1 : MODÈLES MÉTIER (héritage, composition, agrégation)
# =====================================================================
class PriseEnCharge:
    """COMPOSITION : la prise en charge n'existe que pour un patient
    (en base, ses champs sont simplement des colonnes de « patients »)."""

    def __init__(self, type_prise, tarif, jours_hospitalisation=0):
        self.type_prise = type_prise
        self.tarif = tarif
        self.jours_hospitalisation = jours_hospitalisation


class Adresse:
    """COMPOSITION : l'adresse est créée par le patient et disparaît avec lui
    (en base, ses deux champs sont simplement des colonnes de « patients »)."""

    def __init__(self, rue="", ville=""):
        self.rue = rue
        self.ville = ville


class Service:
    """AGRÉGATION : un service hospitalier regroupe des patients qui existent sans lui."""

    def __init__(self, id_service, nom, nombre_lits=0):
        self.id_service = id_service
        self.nom = nom
        self.nombre_lits = int(nombre_lits or 0)
        self.patients = []

    def ajouter_patient(self, patient):
        self.patients.append(patient)
        patient.service = self


class Medecin:
    """AGRÉGATION : un médecin existe sans ses patients (et inversement)."""

    def __init__(self, id_medecin, nom, specialite=""):
        self.id_medecin = id_medecin
        self.nom = nom
        self.specialite = specialite
        self.patients = []

    @property
    def libelle(self):
        """Texte affiché dans les listes : « Dr Benali (Cardiologie) »."""
        return f"{self.nom} ({self.specialite})" if self.specialite else self.nom

    def ajouter_patient(self, patient):
        self.patients.append(patient)
        patient.medecins.append(self)


class Patient:
    """Classe de base : les sous-classes définissent calculer_facture()."""

    def __init__(self, id_patient, nom, prenom, date_naissance, telephone, prise_en_charge,
                 service=None, rue="", ville="", gravite=3, date_entree=None,
                 date_hospitalisation=None, present=True):
        self.id_patient = id_patient
        self.nom = nom
        self.prenom = prenom
        self.date_naissance = date_naissance  # objet datetime.date
        self.telephone = telephone
        self.prise_en_charge = prise_en_charge  # composition
        self.adresse = Adresse(rue, ville)  # composition : créée par le patient lui-même
        self.service = service  # agrégation
        self.medecins = []  # agrégation : liste d'objets Medecin
        self.gravite = int(gravite or 3)
        self.date_entree = date_entree
        self.date_hospitalisation = date_hospitalisation
        self.present = bool(present)

    @property
    def age(self):
        aujourd_hui = date.today()
        return aujourd_hui.year - self.date_naissance.year - (
            (aujourd_hui.month, aujourd_hui.day) <
            (self.date_naissance.month, self.date_naissance.day))

    def calculer_facture(self):
        raise NotImplementedError("À implémenter dans la sous-classe.")

    @property
    def total_facture(self):
        """Montant à facturer : s'utilise comme un attribut (patient.total_facture)."""
        return self.calculer_facture()

    @property
    def facture_affichee(self):
        """Texte affiché dans la liste (les sous-classes peuvent le changer)."""
        return f"{self.total_facture:,.2f} €"

    @property
    def naissance_affichee(self):
        return self.date_naissance.strftime("%d/%m/%Y")


class PatientConsultation(Patient):
    """HÉRITAGE : facture = tarif de la consultation."""

    def calculer_facture(self):
        return self.prise_en_charge.tarif


class PatientHospitalise(Patient):
    """HÉRITAGE : facture = tarif journalier x jours d'hospitalisation."""

    def calculer_facture(self):
        return round(self.prise_en_charge.tarif * self.prise_en_charge.jours_hospitalisation, 2)


class PatientUrgence(Patient):
    """HÉRITAGE : facture = forfait des urgences (0 = aucun frais)."""

    def calculer_facture(self):
        return self.prise_en_charge.tarif

    @property
    def facture_affichee(self):
        if self.total_facture == 0:
            return "Aucun frais"
        return super().facture_affichee


TYPES_PATIENTS = {"Consultation": PatientConsultation, "Hospitalisation": PatientHospitalise,
                  "Urgence": PatientUrgence}


def creer_patient(type_prise, id_patient, nom, prenom, date_naissance, telephone, tarif, jours,
                  service=None, rue="", ville="", gravite=3, date_entree=None,
                  date_hospitalisation=None, present=True):
    prise = PriseEnCharge(type_prise, tarif, jours)
    return TYPES_PATIENTS[type_prise](
        id_patient, nom, prenom, date_naissance, telephone, prise, service, rue, ville,
        gravite, date_entree, date_hospitalisation, present)


# =====================================================================
# ÉTAPE 2 : VALIDATION
# =====================================================================
def convertir_date(texte):
    """Convertit « JJ/MM/AAAA » en objet date ; lève ValueError si la date est incorrecte."""
    texte = texte.replace("-", "/").replace(".", "/")
    try:
        naissance = datetime.strptime(texte, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("La date de naissance doit être au format JJ/MM/AAAA.")
    aujourdhui = date.today()
    if naissance > aujourdhui:
        raise ValueError("La date de naissance ne peut pas être dans le futur.")
    if naissance.year < aujourdhui.year - 130:
        raise ValueError("La date de naissance n'est pas plausible.")
    return naissance


def convertir_date_optionnelle(texte, libelle="La date"):
    """Convertit une date facultative JJ/MM/AAAA en ISO (ou None si vide)."""
    texte = texte.strip()
    if not texte:
        return None
    return convertir_date(texte).isoformat()


def age_depuis_iso(texte):
    """Calcule l'âge exact à partir d'une date ISO ou retourne None."""
    if not texte:
        return None
    try:
        naissance = date.fromisoformat(texte)
    except (TypeError, ValueError):
        return None
    aujourd_hui = date.today()
    return aujourd_hui.year - naissance.year - (
        (aujourd_hui.month, aujourd_hui.day) < (naissance.month, naissance.day))


def telephone_valide(telephone):
    """Le téléphone est facultatif ; s'il est saisi : chiffres, espaces, + - . ( ) et 8 à 15 chiffres."""
    if not telephone:
        return True
    if any(c not in "0123456789 +-.()" for c in telephone):
        return False
    return 8 <= sum(c.isdigit() for c in telephone) <= 15


def valider_saisie(nom, prenom, naissance_txt, telephone, type_prise, tarif_txt, jours_txt):
    """Retourne (date de naissance, tarif, jours) ou lève ValueError."""
    if not nom or not prenom or not naissance_txt or not tarif_txt:
        raise ValueError("Tous les champs obligatoires doivent être remplis.")
    naissance = convertir_date(naissance_txt)
    if not telephone_valide(telephone):
        raise ValueError("Le numéro de téléphone n'est pas valide.")
    try:
        tarif = float(tarif_txt.replace(",", "."))
    except ValueError:
        raise ValueError("Le tarif doit être un nombre.")
    if not 0 <= tarif <= 1000000:
        raise ValueError("Le tarif doit être compris entre 0 et 1 000 000 €.")
    if round(tarif, 2) != tarif:
        raise ValueError("Le tarif ne peut pas avoir plus de 2 décimales.")

    jours = 0
    if type_prise == "Hospitalisation":
        try:
            jours = int(jours_txt)
        except ValueError:
            raise ValueError("Les jours d'hospitalisation doivent être un entier.")
        if not 1 <= jours <= 365:
            raise ValueError("Les jours d'hospitalisation doivent être entre 1 et 365.")
    return naissance, tarif, jours


# =====================================================================
# ÉTAPE 3 : BASE DE DONNÉES (4 tables)
# =====================================================================
# Tri SQL : clé de colonne -> expressions ORDER BY (liste blanche)
TRIS_SQL = {
    "id": ("p.id",),
    "nom": ("p.nom COLLATE NOCASE", "p.prenom COLLATE NOCASE"),
    "prenom": ("p.prenom COLLATE NOCASE", "p.nom COLLATE NOCASE"),
    "naissance": ("p.date_naissance",),
    "telephone": ("p.telephone",),
    "statut": ("p.type_prise_en_charge",),
    "service": ("s.nom COLLATE NOCASE",),
    "ville": ("p.ville COLLATE NOCASE",),
    "medecins": ("(SELECT COUNT(*) FROM suivis x WHERE x.patient_id = p.id)",),
    "facture": ("p.total_facture",),
    "gravite": ("p.gravite", "p.date_entree", "p.id"),
    "present": ("p.present", "p.nom COLLATE NOCASE"),
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS services
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,
    nombre_lits INTEGER NOT NULL DEFAULT 0 CHECK (nombre_lits >= 0)
);
CREATE TABLE IF NOT EXISTS medecins
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT NOT NULL UNIQUE,
    specialite TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS patients
(
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                   TEXT NOT NULL,
    prenom                TEXT NOT NULL,
    date_naissance        TEXT NOT NULL,
    telephone             TEXT NOT NULL DEFAULT '',
    rue                   TEXT NOT NULL DEFAULT '',
    ville                 TEXT NOT NULL DEFAULT '',
    type_prise_en_charge  TEXT NOT NULL DEFAULT 'Consultation',
    tarif                 REAL NOT NULL DEFAULT 0 CHECK (tarif >= 0),
    jours_hospitalisation INTEGER NOT NULL DEFAULT 0,
    total_facture         REAL NOT NULL DEFAULT 0,
    service_id            INTEGER,
    gravite               INTEGER NOT NULL DEFAULT 3 CHECK (gravite BETWEEN 1 AND 5),
    date_entree           TEXT,
    date_hospitalisation  TEXT,
    present               INTEGER NOT NULL DEFAULT 1 CHECK (present IN (0, 1)),
    UNIQUE (nom, prenom, date_naissance),
    FOREIGN KEY (service_id) REFERENCES services (id)
        ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS suivis
(
    patient_id INTEGER NOT NULL,
    medecin_id INTEGER NOT NULL,
    PRIMARY KEY (patient_id, medecin_id),
    FOREIGN KEY (patient_id) REFERENCES patients (id)
        ON DELETE CASCADE,
    FOREIGN KEY (medecin_id) REFERENCES medecins (id)
        ON DELETE CASCADE
);
"""


class Depot:
    def __init__(self, fichier="hopital.db"):
        self.fichier = fichier
        self._creer_tables()

    def _connexion(self):
        conn = sqlite3.connect(self.fichier)
        conn.execute("PRAGMA foreign_keys = ON")  # sinon SQLite ignore les clés étrangères
        return conn

    def _creer_tables(self):
        conn = None
        try:
            conn = self._connexion()
            conn.executescript(SCHEMA)
            # Migration douce : rend aussi le programme compatible avec hopital.db existant.
            colonnes_services = {r[1] for r in conn.execute("PRAGMA table_info(services)")}
            if "nombre_lits" not in colonnes_services:
                conn.execute("ALTER TABLE services ADD COLUMN nombre_lits INTEGER NOT NULL DEFAULT 0")
            colonnes_patients = {r[1] for r in conn.execute("PRAGMA table_info(patients)")}
            migrations = (
                ("gravite", "INTEGER NOT NULL DEFAULT 3"),
                ("date_entree", "TEXT"),
                ("date_hospitalisation", "TEXT"),
                ("present", "INTEGER NOT NULL DEFAULT 1"),
            )
            for nom_colonne, definition in migrations:
                if nom_colonne not in colonnes_patients:
                    conn.execute(f"ALTER TABLE patients ADD COLUMN {nom_colonne} {definition}")
            conn.commit()
        finally:
            if conn:
                conn.close()

    def _ecrire(self, sql, params=(), message_doublon="Valeur déjà existante."):
        conn = None
        try:
            conn = self._connexion()
            conn.execute(sql, params)
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(message_doublon)
        finally:
            if conn:
                conn.close()

    # ----- services -----
    def lister_services(self):
        conn = None
        try:
            conn = self._connexion()
            lignes = conn.execute(
                "SELECT id, nom, nombre_lits FROM services ORDER BY nom").fetchall()
            return [Service(i, n, lits) for i, n, lits in lignes]
        finally:
            if conn:
                conn.close()

    def ajouter_service(self, nom, nombre_lits=0):
        self._ecrire("INSERT INTO services (nom, nombre_lits) VALUES (?, ?)",
                     (nom, nombre_lits), "Ce service existe déjà.")

    def modifier_capacite_service(self, id_service, nombre_lits):
        self._ecrire("UPDATE services SET nombre_lits = ? WHERE id = ?",
                     (nombre_lits, id_service), "Impossible de modifier la capacité du service.")

    def supprimer_service(self, id_service):
        # Les patients restent : service_id passe à NULL (agrégation).
        self._ecrire("DELETE FROM services WHERE id = ?", (id_service,))

    # ----- médecins -----
    def lister_medecins(self):
        conn = None
        try:
            conn = self._connexion()
            lignes = conn.execute(
                "SELECT id, nom, specialite FROM medecins ORDER BY nom").fetchall()
            return [Medecin(i, n, s) for i, n, s in lignes]
        finally:
            if conn:
                conn.close()

    def ajouter_medecin(self, nom, specialite=""):
        self._ecrire("INSERT INTO medecins (nom, specialite) VALUES (?, ?)",
                     (nom, specialite), "Ce médecin existe déjà.")

    def supprimer_medecin(self, id_medecin):
        # Seuls les suivis disparaissent (CASCADE) : les patients restent.
        self._ecrire("DELETE FROM medecins WHERE id = ?", (id_medecin,))

    # ----- patients -----
    @staticmethod
    def _erreur_integrite(e):
        if "patients.nom" in str(e):
            return ValueError("Ce patient existe déjà (même nom, prénom et date de naissance).")
        return ValueError(f"Donnée refusée par la base : {e}")

    def ajouter_patient(self, patient, id_service):
        prise = patient.prise_en_charge
        conn = None
        try:
            conn = self._connexion()
            curseur = conn.execute(
                "INSERT INTO patients (nom, prenom, date_naissance, telephone, rue, ville, "
                "type_prise_en_charge, tarif, jours_hospitalisation, total_facture, service_id, "
                "gravite, date_entree, date_hospitalisation, present) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (patient.nom, patient.prenom, patient.date_naissance.isoformat(),
                 patient.telephone, patient.adresse.rue, patient.adresse.ville,
                 prise.type_prise, prise.tarif, prise.jours_hospitalisation,
                 patient.total_facture, id_service, patient.gravite,
                 patient.date_entree or date.today().isoformat(), patient.date_hospitalisation,
                 int(patient.present)))
            id_patient = curseur.lastrowid
            conn.executemany(
                "INSERT INTO suivis (patient_id, medecin_id) VALUES (?, ?)",
                [(id_patient, m.id_medecin) for m in patient.medecins])
            conn.commit()  # tout réussit ensemble ou rien n'est écrit
        except sqlite3.IntegrityError as e:
            raise self._erreur_integrite(e)
        finally:
            if conn:
                conn.close()

    def modifier_patient(self, patient, id_service):
        prise = patient.prise_en_charge
        conn = None
        try:
            conn = self._connexion()
            curseur = conn.execute(
                "UPDATE patients SET nom = ?, prenom = ?, date_naissance = ?, telephone = ?, "
                "rue = ?, ville = ?, type_prise_en_charge = ?, tarif = ?, "
                "jours_hospitalisation = ?, total_facture = ?, service_id = ?, gravite = ?, "
                "date_entree = ?, date_hospitalisation = ?, present = ? WHERE id = ?",
                (patient.nom, patient.prenom, patient.date_naissance.isoformat(),
                 patient.telephone, patient.adresse.rue, patient.adresse.ville,
                 prise.type_prise, prise.tarif, prise.jours_hospitalisation,
                 patient.total_facture, id_service, patient.gravite,
                 patient.date_entree or date.today().isoformat(), patient.date_hospitalisation,
                 int(patient.present), patient.id_patient))
            if curseur.rowcount == 0:
                raise ValueError("Ce patient n'existe plus.")
            conn.execute("DELETE FROM suivis WHERE patient_id = ?", (patient.id_patient,))
            conn.executemany(
                "INSERT INTO suivis (patient_id, medecin_id) VALUES (?, ?)",
                [(patient.id_patient, m.id_medecin) for m in patient.medecins])
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise self._erreur_integrite(e)
        finally:
            if conn:
                conn.close()

    def supprimer_patient(self, id_patient):
        # Les suivis disparaissent en CASCADE ;
        # les médecins, eux, restent (agrégation).
        self._ecrire("DELETE FROM patients WHERE id = ?", (id_patient,))

    def lister_patients(self, recherche="", service_filtre=None, statut=None,
                        medecin_filtre=None, tri="nom", decroissant=False):
        if tri not in TRIS_SQL:
            raise ValueError("Colonne de tri inconnue.")
        sens = "DESC" if decroissant else "ASC"
        ordre = ", ".join(f"{colonne} {sens}" for colonne in TRIS_SQL[tri]) + ", p.id"

        motif = f"%{recherche}%"
        conditions = ["(p.nom LIKE ? OR p.prenom LIKE ? OR p.telephone LIKE ?)"]
        params = [motif, motif, motif]
        if service_filtre is not None:
            if service_filtre == 0:
                conditions.append("p.service_id IS NULL")
            else:
                conditions.append("p.service_id = ?")
                params.append(service_filtre)
        if statut is not None:
            conditions.append("p.type_prise_en_charge = ?")
            params.append(statut)
        if medecin_filtre is not None:
            if medecin_filtre == 0:
                conditions.append("NOT EXISTS (SELECT 1 FROM suivis x "
                                  "WHERE x.patient_id = p.id)")
            else:
                conditions.append("EXISTS (SELECT 1 FROM suivis x "
                                  "WHERE x.patient_id = p.id AND x.medecin_id = ?)")
                params.append(medecin_filtre)

        sql = f"""
            SELECT p.id, p.nom, p.prenom, p.date_naissance, p.telephone,
                   p.type_prise_en_charge, p.tarif, p.jours_hospitalisation,
                   s.id, s.nom, p.rue, p.ville, p.gravite, p.date_entree,
                   p.date_hospitalisation, p.present
            FROM patients p
            LEFT JOIN services s ON s.id = p.service_id
            WHERE {" AND ".join(conditions)}
            ORDER BY {ordre}
        """
        conn = None
        try:
            conn = self._connexion()
            lignes = conn.execute(sql, params).fetchall()
            suivis = conn.execute(
                "SELECT sv.patient_id, m.id, m.nom, m.specialite FROM suivis sv "
                "JOIN medecins m ON m.id = sv.medecin_id ORDER BY m.nom").fetchall()
        finally:
            if conn:
                conn.close()

        medecins = {}
        medecins_par_patient = {}
        for id_p, id_m, nom_m, specialite in suivis:
            if id_m not in medecins:
                medecins[id_m] = Medecin(id_m, nom_m, specialite)
            medecins_par_patient.setdefault(id_p, []).append(medecins[id_m])

        services = {}
        resultat = []
        for (id_p, nom, prenom, naissance, tel, type_prise, tarif, jours,
             id_s, nom_s, rue, ville, gravite, date_entree, date_hospitalisation, present) in lignes:
            patient = creer_patient(
                type_prise, id_p, nom, prenom, date.fromisoformat(naissance), tel, tarif, jours,
                rue=rue or "", ville=ville or "", gravite=gravite or 3,
                date_entree=date_entree, date_hospitalisation=date_hospitalisation,
                present=bool(present))
            if id_s is not None:
                if id_s not in services:
                    services[id_s] = Service(id_s, nom_s)
                services[id_s].ajouter_patient(patient)
            for medecin in medecins_par_patient.get(id_p, []):
                medecin.ajouter_patient(patient)
            resultat.append(patient)
        return resultat

    def statistiques_tableau_bord(self):
        """Indicateurs calculés directement depuis la base."""
        aujourd_hui = date.today().isoformat()
        conn = None
        try:
            conn = self._connexion()
            ligne = conn.execute("""
                SELECT
                    SUM(CASE WHEN present = 1 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN present = 1 AND type_prise_en_charge = 'Hospitalisation'
                             THEN 1 ELSE 0 END),
                    SUM(CASE WHEN type_prise_en_charge = 'Urgence' AND date_entree = ?
                             THEN 1 ELSE 0 END),
                    COALESCE(SUM(total_facture), 0)
                FROM patients
            """, (aujourd_hui,)).fetchone()
            return {
                "presents": int(ligne[0] or 0),
                "hospitalises": int(ligne[1] or 0),
                "urgences_jour": int(ligne[2] or 0),
                "facturation": float(ligne[3] or 0),
            }
        finally:
            if conn:
                conn.close()

    def occupation_services(self):
        conn = None
        try:
            conn = self._connexion()
            return conn.execute("""
                SELECT s.id, s.nom, s.nombre_lits,
                       SUM(CASE WHEN p.present = 1
                                     AND p.type_prise_en_charge = 'Hospitalisation'
                                THEN 1 ELSE 0 END) AS occupes
                FROM services s
                LEFT JOIN patients p ON p.service_id = s.id
                GROUP BY s.id, s.nom, s.nombre_lits
                ORDER BY s.nom COLLATE NOCASE
            """).fetchall()
        finally:
            if conn:
                conn.close()

    def donnees_alertes(self, seuil_jours=7):
        """Renvoie les listes d'alertes : séjours longs, mineurs et patients de 75 ans+."""
        patients = self.lister_patients(tri="nom")
        longs_sejours, mineurs, seniors = [], [], []
        aujourdhui = date.today()
        for p in patients:
            if p.age is not None and p.age < 18:
                mineurs.append(p)
            if p.age is not None and p.age > 75:
                seniors.append(p)
            if (p.present and p.prise_en_charge.type_prise == "Hospitalisation"
                    and p.date_hospitalisation):
                try:
                    entree = date.fromisoformat(p.date_hospitalisation)
                    jours = (aujourdhui - entree).days
                    if jours > seuil_jours:
                        longs_sejours.append((p, jours))
                except ValueError:
                    pass
        return longs_sejours, mineurs, seniors


# =====================================================================
# ÉTAPE 4 : INTERFACE TKINTER
# =====================================================================
TOUS = "Tous"
AUCUN = "(aucun)"

# Palette
FOND = "#F3F4F6"
TEXTE = "#1F2937"
GRIS = "#6B7280"
BORDURE = "#D1D5DB"
VERT, VERT_FONCE = "#2E7D32", "#256628"
BLEU, BLEU_FONCE = "#1976D2", "#1565C0"
ROUGE, ROUGE_FONCE = "#B71C1C", "#8E1515"

# (clé de tri, titre affiché, largeur en pixels, alignement)
COLONNES = (
    ("id", "ID", 45, "center"),
    ("nom", "Nom", 120, "w"),
    ("prenom", "Prénom", 110, "w"),
    ("naissance", "Naissance", 90, "center"),
    ("telephone", "Téléphone", 110, "w"),
    ("statut", "Prise en charge", 120, "w"),
    ("service", "Service", 130, "w"),
    ("ville", "Ville", 100, "w"),
    ("medecins", "Médecins", 220, "w"),
    ("facture", "Facture", 140, "e"),
    ("gravite", "Gravité", 65, "center"),
    ("present", "Présent", 75, "center"),
)

# Couleur du texte de la ligne selon la prise en charge (Consultation = couleur normale)
TAGS_STATUT = {"Hospitalisation": "hospitalisation", "Urgence": "urgence"}


class Application(tk.Tk):
    def __init__(self, depot):
        super().__init__()
        self.title("Gestion de l'hôpital")
        self.minsize(1300, 760)
        self.configure(background=FOND)
        self._plein_ecran()
        self.depot = depot
        self.patients_affiches = []
        self.services = []
        self.medecins = []
        self.patient_en_edition = None
        self.fenetre_confirmation = None
        self.tri_col = 1
        self.tri_desc = False

        self.var_statut = tk.StringVar(value="Consultation")
        self.var_gravite = tk.StringVar(value="3")
        self.var_present = tk.BooleanVar(value=True)
        self.var_service = tk.StringVar()
        self.var_supp_service = tk.StringVar()
        self.var_supp_medecin = tk.StringVar()
        self.var_recherche = tk.StringVar()
        self.var_filtre_service = tk.StringVar(value=TOUS)
        self.var_filtre_statut = tk.StringVar(value=TOUS)
        self.var_filtre_medecin = tk.StringVar(value=TOUS)

        self._appliquer_style()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._construire_haut()
        self._construire_liste()
        self._construire_barre_etat()
        self._raccourcis()

        self.var_statut.trace_add("write", lambda *a: self._maj_formulaire())
        for var in (self.var_recherche, self.var_filtre_service, self.var_filtre_statut,
                    self.var_filtre_medecin):
            var.trace_add("write", lambda *a: self.rafraichir_liste())

        self._maj_formulaire()
        self.rafraichir_services()
        self.rafraichir_medecins()
        self.rafraichir_liste()

    def ouvrir_tableau_bord(self):
        """Ouvre le tableau de bord ; une seule fenêtre est maintenue à la fois."""
        if getattr(self, "fenetre_tableau_bord", None) is not None:
            try:
                if self.fenetre_tableau_bord.winfo_exists():
                    self.fenetre_tableau_bord.deiconify()
                    self.fenetre_tableau_bord.lift()
                    self._actualiser_tableau_bord()
                    return
            except tk.TclError:
                pass
        fen = tk.Toplevel(self)
        self.fenetre_tableau_bord = fen
        fen.title("Tableau de bord — Gestion de l'hôpital")
        fen.configure(background=FOND)
        fen.geometry("980x680")
        fen.minsize(820, 560)
        fen.transient(self)
        fen.protocol("WM_DELETE_WINDOW", fen.destroy)

        racine = ttk.Frame(fen, padding=16)
        racine.pack(fill="both", expand=True)
        entete = ttk.Frame(racine)
        entete.pack(fill="x", pady=(0, 12))
        ttk.Label(entete, text="Tableau de bord", font=(self.police, 19, "bold")).pack(side="left")
        ttk.Button(entete, text="Actualiser", command=self._actualiser_tableau_bord).pack(side="right")
        ttk.Button(entete, text="Gestion des patients", command=lambda: (fen.destroy(), self.lift())).pack(
            side="right", padx=(0, 8))

        kpis = ttk.Frame(racine)
        kpis.pack(fill="x", pady=(0, 12))
        self.kpi_labels = {}
        indicateurs = [
            ("presents", "Patients présents", BLEU),
            ("hospitalises", "Hospitalisés", ROUGE),
            ("urgences_jour", "Urgences aujourd'hui", "#C2410C"),
            ("facturation", "Total facturé", VERT),
        ]
        for i, (cle, titre, couleur) in enumerate(indicateurs):
            kpis.columnconfigure(i, weight=1)
            card = ttk.LabelFrame(kpis, text=f" {titre} ", padding=12)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            valeur = ttk.Label(card, text="—", font=(self.police, 20, "bold"), foreground=couleur)
            valeur.pack(anchor="w")
            self.kpi_labels[cle] = valeur

        milieu = ttk.Frame(racine)
        milieu.pack(fill="both", expand=True)
        milieu.columnconfigure(0, weight=3)
        milieu.columnconfigure(1, weight=2)
        milieu.rowconfigure(0, weight=1)

        cadre_occupation = ttk.LabelFrame(milieu, text=" Occupation des lits par service ", padding=12)
        cadre_occupation.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        cadre_occupation.columnconfigure(0, weight=1)
        self.zone_occupation = ttk.Frame(cadre_occupation)
        self.zone_occupation.pack(fill="both", expand=True)

        cadre_alertes = ttk.LabelFrame(milieu, text=" Alertes ", padding=12)
        cadre_alertes.grid(row=0, column=1, sticky="nsew")
        ttk.Label(cadre_alertes, text="Alerter si hospitalisation supérieure à (jours) :").pack(anchor="w")
        self.var_seuil_sejour = tk.StringVar(value="7")
        seuil_frame = ttk.Frame(cadre_alertes)
        seuil_frame.pack(fill="x", pady=(4, 8))
        ttk.Spinbox(seuil_frame, from_=0, to=365, width=6, textvariable=self.var_seuil_sejour).pack(side="left")
        ttk.Button(seuil_frame, text="Appliquer", command=self._actualiser_tableau_bord).pack(side="left", padx=6)
        self.zone_alertes = ttk.Frame(cadre_alertes)
        self.zone_alertes.pack(fill="both", expand=True)
        self._actualiser_tableau_bord()

    def _actualiser_tableau_bord(self):
        """Met à jour les KPI, barres d'occupation et alertes si le tableau existe."""
        fen = getattr(self, "fenetre_tableau_bord", None)
        if fen is None:
            return
        try:
            if not fen.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            stats = self.depot.statistiques_tableau_bord()
            for cle in ("presents", "hospitalises", "urgences_jour", "facturation"):
                if cle in self.kpi_labels:
                    valeur = stats[cle]
                    texte = f"{valeur:,.2f} €" if cle == "facturation" else str(valeur)
                    self.kpi_labels[cle].config(text=texte.replace(",", " "))

            for widget in self.zone_occupation.winfo_children():
                widget.destroy()
            occupations = self.depot.occupation_services()
            if not occupations:
                ttk.Label(self.zone_occupation, text="Aucun service enregistré.",
                          foreground=GRIS).pack(anchor="w", pady=8)
            else:
                for idx, (id_s, nom, lits, occupes) in enumerate(occupations):
                    occupes = int(occupes or 0)
                    lits = int(lits or 0)
                    ligne = ttk.Frame(self.zone_occupation, padding=(0, 5))
                    ligne.pack(fill="x", anchor="n")
                    ttk.Label(ligne, text=nom, font=(self.police, 10, "bold")).pack(anchor="w")
                    if lits <= 0:
                        ttk.Label(ligne, text=f"{occupes} patient(s) hospitalisé(s) • capacité non définie",
                                  foreground=GRIS).pack(anchor="w")
                        continue
                    taux = (occupes / lits) * 100
                    couleur = ROUGE if taux >= 90 else ("#D97706" if taux >= 75 else VERT)
                    style_nom = f"Occupation{idx}.Horizontal.TProgressbar"
                    ttk.Style(self).configure(style_nom, troughcolor="#E5E7EB", background=couleur)
                    barres = ttk.Frame(ligne)
                    barres.pack(fill="x", pady=(3, 0))
                    barre = ttk.Progressbar(barres, maximum=100, value=min(taux, 100),
                                            style=style_nom, mode="determinate")
                    barre.pack(side="left", fill="x", expand=True)
                    ttk.Label(barres, text=f" {occupes}/{lits} ({taux:.0f}%)",
                              foreground=(ROUGE if taux >= 90 else TEXTE)).pack(side="left", padx=(8, 0))
                    if taux >= 90:
                        ttk.Label(ligne, text="⚠ Capacité presque atteinte ou dépassée",
                                  foreground=ROUGE).pack(anchor="w")

            for widget in self.zone_alertes.winfo_children():
                widget.destroy()
            try:
                seuil = int(self.var_seuil_sejour.get())
                if seuil < 0:
                    raise ValueError
            except (ValueError, tk.TclError):
                ttk.Label(self.zone_alertes, text="Le seuil doit être un entier positif.",
                          foreground=ROUGE).pack(anchor="w")
                return
            longs, mineurs, seniors = self.depot.donnees_alertes(seuil)
            self._bloc_alerte(self.zone_alertes, f"Séjours > {seuil} jour(s)",
                              [f"{p.prenom} {p.nom} — {j} jour(s)" for p, j in longs], ROUGE)
            self._bloc_alerte(self.zone_alertes, "Patients mineurs (< 18 ans)",
                              [f"{p.prenom} {p.nom} — {p.age} ans" for p in mineurs], "#B45309")
            self._bloc_alerte(self.zone_alertes, "Patients âgés (> 75 ans)",
                              [f"{p.prenom} {p.nom} — {p.age} ans" for p in seniors], BLEU)
        except (sqlite3.Error, ValueError, tk.TclError) as e:
            if hasattr(self, "zone_alertes"):
                ttk.Label(self.zone_alertes, text=f"Impossible d'actualiser : {e}",
                          foreground=ROUGE).pack(anchor="w")

    @staticmethod
    def _bloc_alerte(parent, titre, elements, couleur):
        bloc = ttk.Frame(parent, padding=(0, 5))
        bloc.pack(fill="x", anchor="n")
        ttk.Label(bloc, text=f"{titre} ({len(elements)})", foreground=couleur,
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        if elements:
            for element in elements[:8]:
                ttk.Label(bloc, text=f"• {element}", wraplength=300,
                          justify="left").pack(anchor="w", padx=(5, 0))
            if len(elements) > 8:
                ttk.Label(bloc, text=f"… et {len(elements) - 8} autre(s)",
                          foreground=GRIS).pack(anchor="w", padx=(5, 0))
        else:
            ttk.Label(bloc, text="Aucune alerte", foreground=GRIS).pack(anchor="w", padx=(5, 0))

    def _plein_ecran(self):
        """Ouvre la fenêtre maximisée (Windows, Linux, macOS)."""
        try:
            self.state("zoomed")  # Windows (et certains macOS)
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)  # Linux
            except tk.TclError:
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

    # ----- style -----
    def _appliquer_style(self):
        familles = set(tkfont.families(self))
        police = next((f for f in ("Segoe UI", "Helvetica Neue", "Ubuntu", "DejaVu Sans")
                       if f in familles), None)
        if police:
            for nom in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                tkfont.nametofont(nom).configure(family=police, size=10)
        else:
            police = tkfont.nametofont("TkDefaultFont").actual("family")
        self.police = police

        s = ttk.Style(self)
        s.theme_use("clam")  # thème qui accepte les couleurs personnalisées
        s.configure(".", background=FOND, foreground=TEXTE, font=(police, 10))

        # Champs de saisie
        s.configure("TEntry", fieldbackground="white", padding=4, bordercolor=BORDURE)
        s.map("TEntry", fieldbackground=[("disabled", "#E5E7EB")],
              foreground=[("disabled", GRIS)])
        s.configure("TCombobox", fieldbackground="white", padding=4, bordercolor=BORDURE,
                    arrowsize=14)
        s.map("TCombobox", fieldbackground=[("readonly", "white")],
              selectbackground=[("readonly", "white")],
              selectforeground=[("readonly", TEXTE)])

        # Cadres
        s.configure("TLabelframe", background=FOND, bordercolor=BORDURE)
        s.configure("TLabelframe.Label", background=FOND, foreground=TEXTE,
                    font=(police, 10, "bold"))

        # Boutons
        s.configure("TButton", padding=(12, 5), background="#E5E7EB", bordercolor=BORDURE)
        s.map("TButton", background=[("active", BORDURE)])

        def bouton(nom, fond, actif):
            s.configure(nom, background=fond, foreground="white", bordercolor=fond,
                        padding=(16, 6))
            s.map(nom, background=[("active", actif), ("pressed", actif)],
                  foreground=[("active", "white")])

        bouton("Accent.TButton", VERT, VERT_FONCE)      # action principale
        bouton("Edit.TButton", BLEU, BLEU_FONCE)        # mode modification
        bouton("DangerSolid.TButton", ROUGE, ROUGE_FONCE)
        s.configure("Danger.TButton", background="white", foreground=ROUGE,
                    bordercolor=ROUGE)
        s.map("Danger.TButton", background=[("active", "#FDE8E8")],
              foreground=[("active", ROUGE)])

        # Tableau
        s.configure("Treeview", rowheight=28, background="white", fieldbackground="white",
                    borderwidth=0, font=(police, 10))
        s.map("Treeview", background=[("selected", BLEU)], foreground=[("selected", "white")])
        s.configure("Treeview.Heading", background="#E5E7EB", foreground=TEXTE,
                    font=(police, 10, "bold"), padding=(6, 6), relief="flat")
        s.map("Treeview.Heading", background=[("active", BORDURE)])

    # ----- construction -----
    def _construire_haut(self):
        haut = ttk.Frame(self)
        haut.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        haut.columnconfigure(0, weight=3)
        haut.columnconfigure(1, weight=2, minsize=400)
        self._construire_formulaire(haut)

        # Colonne de droite : gestion des services et des médecins
        droite = ttk.Frame(haut)
        droite.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        droite.columnconfigure(0, weight=1)
        droite.rowconfigure(0, weight=1)
        droite.rowconfigure(1, weight=1)
        self.ent_nouveau_service, _, self.menu_supp_service = self._bloc_gestion(
            droite, 0, "Services", self.var_supp_service,
            self.action_creer_service, self.action_supprimer_service, capacite=True)
        self.menu_supp_service.bind("<<ComboboxSelected>>", self._charger_capacite_service)
        self.ent_nouveau_medecin, self.ent_specialite, self.menu_supp_medecin = \
            self._bloc_gestion(droite, 1, "Médecins", self.var_supp_medecin,
                               self.action_creer_medecin, self.action_supprimer_medecin,
                               libelle_extra="Spécialité")

    def _bloc_gestion(self, parent, ligne, titre, var_choix, creer, supprimer,
                      libelle_extra=None, capacite=False):
        """Bloc « Créer / Supprimer » : retourne (champ nom, champ extra ou None, liste)."""
        bloc = ttk.LabelFrame(parent, text=f" {titre} ", padding=10)
        bloc.grid(row=ligne, column=0, sticky="nsew", pady=(0, 6) if ligne == 0 else 0)
        bloc.columnconfigure(1, weight=1)

        ttk.Label(bloc, text="Nouveau").grid(row=0, column=0, sticky="w", padx=(0, 10))
        entree = ttk.Entry(bloc)
        entree.grid(row=0, column=1, sticky="ew", pady=4)
        entree.bind("<Return>", lambda e: creer())
        ttk.Button(bloc, text="Créer", command=creer).grid(
            row=0, column=2, sticky="ew", padx=(8, 0))

        extra = None
        suite = 1
        if capacite:
            ttk.Label(bloc, text="Nombre de lits").grid(
                row=1, column=0, sticky="w", padx=(0, 10))
            self.ent_nombre_lits_service = ttk.Entry(bloc, width=8)
            self.ent_nombre_lits_service.insert(0, "0")
            self.ent_nombre_lits_service.grid(row=1, column=1, sticky="ew", pady=4)
            self.ent_nombre_lits_service.bind("<Return>", lambda e: self.action_creer_service())
            suite = 2
        if libelle_extra:
            ttk.Label(bloc, text=libelle_extra).grid(row=1, column=0, sticky="w", padx=(0, 10))
            extra = ttk.Entry(bloc)
            extra.grid(row=1, column=1, sticky="ew", pady=4)
            extra.bind("<Return>", lambda e: creer())
            suite = 2

        ttk.Label(bloc, text="Existant").grid(row=suite, column=0, sticky="w", padx=(0, 10))
        choix = self._combo(bloc, var_choix, ())
        choix.grid(row=suite, column=1, sticky="ew", pady=4)
        ttk.Button(bloc, text="Supprimer", style="Danger.TButton", command=supprimer).grid(
            row=suite, column=2, sticky="ew", padx=(8, 0))
        if capacite:
            ttk.Button(bloc, text="Enregistrer la capacité", command=self.action_modifier_capacite_service).grid(
                row=suite + 1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        return entree, extra, choix

    def _construire_formulaire(self, parent):
        self.cadre_form = ttk.LabelFrame(parent, padding=12)
        cadre = self.cadre_form
        cadre.grid(row=0, column=0, sticky="nsew")
        # colonnes de champs de même largeur ; colonnes des libellés à largeur fixe
        cadre.columnconfigure(0, minsize=110)
        cadre.columnconfigure(1, weight=1, uniform="champ")
        cadre.columnconfigure(2, minsize=240)
        cadre.columnconfigure(3, weight=1, uniform="champ")

        self.ent_nom = self._champ(cadre, "Nom *", 0, 0)
        self.ent_prenom = self._champ(cadre, "Prénom *", 0, 2)
        self.ent_naissance = self._champ(cadre, "Naissance *", 1, 0)
        self.ent_telephone = self._champ(cadre, "Téléphone", 1, 2)

        self._etiquette(cadre, "Prise en charge", 2, 0)
        self._combo(cadre, self.var_statut, list(TYPES_PATIENTS)).grid(
            row=2, column=1, sticky="ew", pady=4)

        self.lbl_tarif = self._etiquette(cadre, "Tarif de la consultation (€) *", 2, 2)
        self.ent_tarif = ttk.Entry(cadre)
        self.ent_tarif.grid(row=2, column=3, sticky="ew", pady=4)

        self.ent_rue = self._champ(cadre, "Rue", 3, 0)
        self.lbl_jours = self._etiquette(cadre, "Jours d'hospitalisation", 3, 2)
        self.ent_jours = ttk.Entry(cadre)
        self.ent_jours.grid(row=3, column=3, sticky="ew", pady=4)

        self.ent_ville = self._champ(cadre, "Ville", 4, 0)
        self._etiquette(cadre, "Service", 5, 0)
        self.menu_service = self._combo(cadre, self.var_service, ())
        self.menu_service.grid(row=5, column=1, sticky="ew", pady=4)

        self._etiquette(cadre, "Médecins", 4, 2, sticky="nw", pady=8)
        cadre_med = ttk.Frame(cadre)
        cadre_med.grid(row=4, column=3, rowspan=2, sticky="ew", pady=4)
        cadre_med.columnconfigure(0, weight=1)
        self.liste_medecins = tk.Listbox(
            cadre_med, selectmode=tk.MULTIPLE, height=4, exportselection=False,
            activestyle="none", bg="white", fg=TEXTE, relief="flat",
            highlightthickness=1, highlightbackground="#B8BEC7", highlightcolor=BLEU,
            selectbackground=BLEU, selectforeground="white", font=(self.police, 10))
        ascenseur = ttk.Scrollbar(cadre_med, orient="vertical",
                                  command=self.liste_medecins.yview)
        self.liste_medecins.config(yscrollcommand=ascenseur.set)
        self.liste_medecins.grid(row=0, column=0, sticky="ew")
        ascenseur.grid(row=0, column=1, sticky="ns")

        self.ent_date_hospitalisation = self._champ(
            cadre, "Date d'hospitalisation", 6, 0)
        self._etiquette(cadre, "Gravité (1 = critique)", 6, 2)
        self._combo(cadre, self.var_gravite, ["1", "2", "3", "4", "5"]).grid(
            row=6, column=3, sticky="ew", pady=4)
        ttk.Checkbutton(cadre, text="Patient actuellement présent",
                        variable=self.var_present).grid(row=7, column=0, columnspan=2,
                                                          sticky="w", pady=(3, 0))
        ttk.Label(cadre, text="Date d'entrée : enregistrée automatiquement",
                  foreground=GRIS).grid(row=7, column=2, columnspan=2, sticky="w", pady=(3, 0))

        boutons = ttk.Frame(cadre)
        boutons.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.btn_valider = ttk.Button(boutons, command=self.action_valider)
        self.btn_valider.pack(side="left")
        self.btn_annuler = ttk.Button(boutons, text="Annuler", command=self._mode_ajout)
        ttk.Label(boutons, text="* champ obligatoire   •   date : JJ/MM/AAAA",
                  foreground=GRIS).pack(side="right")

        self._mode_ajout()

    @staticmethod
    def _etiquette(parent, texte, ligne, colonne, sticky="w", pady=4):
        etiquette = ttk.Label(parent, text=texte)
        etiquette.grid(row=ligne, column=colonne, sticky=sticky, pady=pady,
                       padx=(16 if colonne else 0, 8))
        return etiquette

    def _champ(self, parent, texte, ligne, colonne):
        self._etiquette(parent, texte, ligne, colonne)
        entree = ttk.Entry(parent)
        entree.grid(row=ligne, column=colonne + 1, sticky="ew", pady=4)
        return entree

    @staticmethod
    def _combo(parent, variable, valeurs, width=None):
        options = {"textvariable": variable, "values": list(valeurs), "state": "readonly"}
        if width:
            options["width"] = width
        return ttk.Combobox(parent, **options)

    def _construire_liste(self):
        self.cadre_liste = ttk.LabelFrame(self, padding=10)
        cadre = self.cadre_liste
        cadre.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        cadre.columnconfigure(0, weight=1)
        cadre.rowconfigure(1, weight=1)

        # Ligne de recherche et de filtres
        barre = ttk.Frame(cadre)
        barre.grid(row=0, column=0, sticky="ew")
        ttk.Label(barre, text="Recherche").pack(side="left")
        ttk.Entry(barre, textvariable=self.var_recherche, width=22).pack(
            side="left", padx=(6, 18))
        ttk.Label(barre, text="Service").pack(side="left")
        self.menu_filtre_service = self._combo(barre, self.var_filtre_service, [TOUS], width=14)
        self.menu_filtre_service.pack(side="left", padx=(6, 18))
        ttk.Label(barre, text="Prise en charge").pack(side="left")
        self._combo(barre, self.var_filtre_statut, [TOUS, *TYPES_PATIENTS], width=14).pack(
            side="left", padx=(6, 18))
        ttk.Label(barre, text="Médecin").pack(side="left")
        self.menu_filtre_medecin = self._combo(barre, self.var_filtre_medecin, [TOUS], width=14)
        self.menu_filtre_medecin.pack(side="left", padx=(6, 0))
        ttk.Button(barre, text="Tableau de bord", command=self.ouvrir_tableau_bord).pack(
            side="right", padx=(6, 0))
        ttk.Button(barre, text="Trier par priorité", command=self.action_trier_priorite).pack(
            side="right", padx=(6, 0))
        ttk.Button(barre, text="Modifier la sélection", style="Edit.TButton",
                   command=self.action_modifier_selection).pack(side="right", padx=(6, 0))
        ttk.Button(barre, text="Supprimer la sélection", style="Danger.TButton",
                   command=self.action_supprimer).pack(side="right")

        corps = ttk.Frame(cadre)
        corps.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        corps.columnconfigure(0, weight=1)
        corps.rowconfigure(0, weight=1)
        ascenseur = ttk.Scrollbar(corps, orient="vertical")
        ascenseur.grid(row=0, column=1, sticky="ns")

        self.liste = ttk.Treeview(corps, columns=[c[0] for c in COLONNES],
                                  show="headings", selectmode="browse", height=8,
                                  yscrollcommand=ascenseur.set)
        for i, (cle, titre, largeur, ancre) in enumerate(COLONNES):
            self.liste.heading(cle, text=titre, anchor=ancre,
                               command=lambda i=i: self.action_trier(i))
            # largeur fixe : seule la colonne « Médecins » s'étire si on agrandit la fenêtre
            self.liste.column(cle, width=largeur, minwidth=largeur, anchor=ancre,
                              stretch=(cle == "medecins"))
        self.liste.grid(row=0, column=0, sticky="nsew")
        ascenseur.config(command=self.liste.yview)
        self.liste.bind("<Double-Button-1>", self.action_fiche_detaillee)

        # Lignes en alternance + couleur du texte selon la prise en charge
        self.liste.tag_configure("pair", background="white")
        self.liste.tag_configure("impair", background="#F3F6FA")
        self.liste.tag_configure("hospitalisation", foreground="#B45309")
        self.liste.tag_configure("urgence", foreground=ROUGE)
        self.liste.tag_configure("gravite1", background="#FECACA", foreground="#7F1D1D")
        self.liste.tag_configure("gravite2", background="#FED7AA", foreground="#7C2D12")
        self.liste.tag_configure("gravite3", background="#FEF3C7", foreground="#78350F")
        self.liste.tag_configure("gravite4", background="#D1FAE5", foreground="#064E3B")
        self.liste.tag_configure("gravite5", background="#DBEAFE", foreground="#1E3A8A")

        # Message affiché quand la liste est vide
        self.lbl_vide = ttk.Label(self.liste, background="white", foreground=GRIS,
                                  font=(self.police, 11))
        self._maj_entetes()

        ttk.Label(cadre, foreground=GRIS,
                  text="Double-clic : fiche détaillée   •   Modifier : éditer   •   "
                       "Suppr : supprimer   •   Clic sur un titre : trier").grid(row=2, column=0, sticky="w",
                                                         pady=(8, 0))

    def _construire_barre_etat(self):
        self.lbl_message = ttk.Label(self, anchor="w", padding=(14, 8))
        self.lbl_message.grid(row=2, column=0, sticky="ew")
        self.message("Prêt.", info=True)

    def _raccourcis(self):
        # Entrée : valider le formulaire
        for champ in (self.ent_nom, self.ent_prenom, self.ent_naissance, self.ent_telephone,
                      self.ent_tarif, self.ent_rue, self.ent_ville, self.ent_jours,
                      self.ent_date_hospitalisation):
            champ.bind("<Return>", lambda e: self.action_valider())
        # Suppr : supprimer la ligne sélectionnée
        self.liste.bind("<Delete>", lambda e: self.action_supprimer())
        # Échap : quitter le mode modification
        self.bind("<Escape>", lambda e: self._mode_ajout() if self.patient_en_edition else None)

    # ----- affichage -----
    def message(self, texte, erreur=False, info=False):
        if erreur:
            fond, couleur = "#FDE8E8", ROUGE
        elif info:
            fond, couleur = "#E8F0FE", "#1A4E9C"
        else:
            fond, couleur = "#E6F4EA", "#1E6B34"
        self.lbl_message.config(text=texte, background=fond, foreground=couleur)

    def _maj_formulaire(self):
        """Adapte le formulaire au type de prise en charge choisi."""
        statut = self.var_statut.get()
        if statut == "Hospitalisation":
            self.lbl_tarif.config(text="Tarif journalier (€) *")
            self.lbl_jours.config(text="Jours d'hospitalisation *")
            self.ent_jours.config(state="normal")
            if not self.ent_jours.get():
                self.ent_jours.insert(0, "1")
            if (hasattr(self, "ent_date_hospitalisation")
                    and self.patient_en_edition is None
                    and not self.ent_date_hospitalisation.get()):
                self.ent_date_hospitalisation.insert(0, date.today().strftime("%d/%m/%Y"))
        else:
            if statut == "Urgence":
                self.lbl_tarif.config(text="Forfait des urgences (€) *")
            else:
                self.lbl_tarif.config(text="Tarif de la consultation (€) *")
            self.lbl_jours.config(text="Jours d'hospitalisation")
            self.ent_jours.config(state="normal")
            self.ent_jours.delete(0, tk.END)
            self.ent_jours.config(state="disabled")

    def _maj_entetes(self):
        for i, (cle, titre, _, _) in enumerate(COLONNES):
            fleche = ""
            if i == self.tri_col:
                fleche = " ▼" if self.tri_desc else " ▲"
            self.liste.heading(cle, text=titre + fleche)

    def rafraichir_services(self):
        try:
            self.services = self.depot.lister_services()
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
            return
        noms = [s.nom for s in self.services]

        self.menu_service.config(values=[AUCUN] + noms)
        if self.var_service.get() not in noms + [AUCUN]:
            self.var_service.set(noms[0] if noms else AUCUN)

        self.menu_supp_service.config(values=noms)
        if self.var_supp_service.get() not in noms:
            self.var_supp_service.set(noms[0] if noms else "")

        self.menu_filtre_service.config(values=[TOUS, AUCUN] + noms)
        if self.var_filtre_service.get() not in noms + [TOUS, AUCUN]:
            self.var_filtre_service.set(TOUS)
        self._charger_capacite_service()
        self._actualiser_tableau_bord()

    def _medecins_choisis(self):
        """Objets Medecin sélectionnés dans la liste du formulaire."""
        return [self.medecins[i] for i in self.liste_medecins.curselection()]

    def rafraichir_medecins(self):
        noms_choisis = {m.nom for m in self._medecins_choisis()}  # garder la sélection
        try:
            self.medecins = self.depot.lister_medecins()
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
            return
        self.liste_medecins.delete(0, tk.END)
        for i, medecin in enumerate(self.medecins):
            self.liste_medecins.insert(tk.END, medecin.libelle)
            if medecin.nom in noms_choisis:
                self.liste_medecins.selection_set(i)

        libelles = [m.libelle for m in self.medecins]
        self.menu_supp_medecin.config(values=libelles)
        if self.var_supp_medecin.get() not in libelles:
            self.var_supp_medecin.set(libelles[0] if libelles else "")

        noms = [m.nom for m in self.medecins]
        self.menu_filtre_medecin.config(values=[TOUS, AUCUN] + noms)
        if self.var_filtre_medecin.get() not in noms + [TOUS, AUCUN]:
            self.var_filtre_medecin.set(TOUS)

    def _id_service_par_nom(self, nom):
        return next((s.id_service for s in self.services if s.nom == nom), None)

    def _service_filtre(self):
        valeur = self.var_filtre_service.get()
        if valeur == TOUS:
            return None
        if valeur == AUCUN:
            return 0
        return self._id_service_par_nom(valeur)

    def _medecin_filtre(self):
        valeur = self.var_filtre_medecin.get()
        if valeur == TOUS:
            return None
        if valeur == AUCUN:
            return 0
        return next((m.id_medecin for m in self.medecins if m.nom == valeur), None)

    def rafraichir_liste(self):
        statut = self.var_filtre_statut.get()
        recherche = self.var_recherche.get().strip()
        try:
            patients = self.depot.lister_patients(
                recherche,
                self._service_filtre(),
                None if statut == TOUS else statut,
                self._medecin_filtre(),
                COLONNES[self.tri_col][0],
                self.tri_desc)
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
            return
        self.patients_affiches = patients

        self.liste.delete(*self.liste.get_children())
        for i, pat in enumerate(patients):
            service = pat.service.nom if pat.service else AUCUN
            medecins = ", ".join(m.nom for m in pat.medecins)
            tags = ["impair" if i % 2 else "pair"]
            tags.append(f"gravite{max(1, min(5, pat.gravite))}")
            self.liste.insert("", tk.END, iid=str(i), tags=tags, values=(
                pat.id_patient, pat.nom, pat.prenom, pat.naissance_affichee, pat.telephone,
                pat.prise_en_charge.type_prise, service, pat.adresse.ville, medecins,
                pat.facture_affichee, pat.gravite, "Oui" if pat.present else "Non"))
        self.cadre_liste.config(text=f" Patients ({len(patients)}) ")

        if patients:
            self.lbl_vide.place_forget()
        else:
            filtre_actif = (recherche or statut != TOUS
                            or self.var_filtre_service.get() != TOUS
                            or self.var_filtre_medecin.get() != TOUS)
            self.lbl_vide.config(text="Aucun résultat pour ces critères." if filtre_actif
                                 else "Aucun patient pour l'instant.")
            self.lbl_vide.place(relx=0.5, rely=0.3, anchor="center")
        self._actualiser_tableau_bord()

    # ----- mode ajout / mode modification -----
    def _vider_formulaire(self):
        for champ in (self.ent_nom, self.ent_prenom, self.ent_naissance, self.ent_telephone,
                      self.ent_tarif, self.ent_rue, self.ent_ville):
            champ.delete(0, tk.END)
        self.liste_medecins.selection_clear(0, tk.END)
        self.ent_date_hospitalisation.delete(0, tk.END)
        self.var_gravite.set("3")
        self.var_present.set(True)
        if self.var_statut.get() == "Hospitalisation":
            self.ent_jours.delete(0, tk.END)
            self.ent_jours.insert(0, "1")

    def _mode_ajout(self):
        self.patient_en_edition = None
        self.cadre_form.config(text=" Nouveau patient ")
        self.btn_valider.config(text="Ajouter le patient", style="Accent.TButton")
        self.btn_annuler.pack_forget()
        self._vider_formulaire()

    def action_modifier_selection(self):
        selection = self.liste.selection()
        if not selection:
            self.message("Sélectionnez d'abord un patient à modifier.", erreur=True)
            return
        self._charger_patient(self.patients_affiches[int(selection[0])])

    def action_charger(self, event=None):
        """Compatibilité : charge le patient sélectionné dans le formulaire."""
        self.action_modifier_selection()

    def _charger_patient(self, pat):
        self.patient_en_edition = pat
        self.cadre_form.config(text=f" Modifier : {pat.prenom} {pat.nom} ")
        self.btn_valider.config(text="Enregistrer les modifications", style="Edit.TButton")
        self.btn_annuler.pack(side="left", padx=(8, 0))

        for champ, valeur in ((self.ent_nom, pat.nom), (self.ent_prenom, pat.prenom),
                              (self.ent_naissance, pat.naissance_affichee),
                              (self.ent_telephone, pat.telephone),
                              (self.ent_tarif, f"{pat.prise_en_charge.tarif:.2f}"),
                              (self.ent_rue, pat.adresse.rue),
                              (self.ent_ville, pat.adresse.ville)):
            champ.delete(0, tk.END)
            champ.insert(0, valeur)
        self.ent_date_hospitalisation.delete(0, tk.END)
        self.var_statut.set(pat.prise_en_charge.type_prise)
        self.ent_jours.config(state="normal")
        self.ent_jours.delete(0, tk.END)
        if pat.prise_en_charge.type_prise == "Hospitalisation":
            self.ent_jours.insert(0, str(pat.prise_en_charge.jours_hospitalisation))
            if pat.date_hospitalisation:
                try:
                    self.ent_date_hospitalisation.insert(
                        0, date.fromisoformat(pat.date_hospitalisation).strftime("%d/%m/%Y"))
                except ValueError:
                    pass
        self.var_gravite.set(str(pat.gravite))
        self.var_present.set(pat.present)
        self.var_service.set(pat.service.nom if pat.service else AUCUN)

        ids_medecins = {m.id_medecin for m in pat.medecins}
        self.liste_medecins.selection_clear(0, tk.END)
        for k, medecin in enumerate(self.medecins):
            if medecin.id_medecin in ids_medecins:
                self.liste_medecins.selection_set(k)
        self.message("Modifiez les champs puis enregistrez (Entrée) ou annulez (Échap).",
                     info=True)

    def action_fiche_detaillee(self, event=None):
        """Ouvre une fiche complète ; le double-clic ne passe plus en mode édition."""
        if event is not None:
            ligne = self.liste.identify_row(event.y)
            if not ligne:
                return
            self.liste.selection_set(ligne)
            pat = self.patients_affiches[int(ligne)]
        else:
            selection = self.liste.selection()
            if not selection:
                self.message("Sélectionnez un patient pour afficher sa fiche.", erreur=True)
                return
            pat = self.patients_affiches[int(selection[0])]

        fen = tk.Toplevel(self)
        fen.title(f"Dossier patient — {pat.prenom} {pat.nom}")
        fen.configure(background=FOND)
        fen.transient(self)
        fen.geometry("760x620")
        fen.minsize(650, 500)
        cadre = ttk.Frame(fen, padding=18)
        cadre.pack(fill="both", expand=True)
        ttk.Label(cadre, text=f"{pat.prenom} {pat.nom}",
                  font=(self.police, 18, "bold")).pack(anchor="w")
        ttk.Label(cadre, text=f"Dossier n° {pat.id_patient}  •  Âge : {pat.age} ans  •  "
                              f"Gravité : {pat.gravite}/5",
                  foreground=GRIS).pack(anchor="w", pady=(2, 14))

        infos = ttk.LabelFrame(cadre, text=" Informations générales ", padding=12)
        infos.pack(fill="x", pady=(0, 10))
        def ligne_info(parent, libelle, valeur):
            r = ttk.Frame(parent)
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=libelle, width=22, foreground=GRIS).pack(side="left", anchor="nw")
            ttk.Label(r, text=str(valeur if valeur not in (None, "") else "—"),
                      wraplength=470, justify="left").pack(side="left", anchor="nw")
        ligne_info(infos, "Date de naissance", pat.naissance_affichee)
        ligne_info(infos, "Téléphone", pat.telephone)
        ligne_info(infos, "Adresse", ", ".join(v for v in [pat.adresse.rue, pat.adresse.ville] if v) or "—")
        ligne_info(infos, "Prise en charge", pat.prise_en_charge.type_prise)
        ligne_info(infos, "Service", pat.service.nom if pat.service else AUCUN)
        ligne_info(infos, "Médecins", ", ".join(m.libelle for m in pat.medecins) or "Aucun médecin associé")
        ligne_info(infos, "Présence actuelle", "Oui" if pat.present else "Non")
        ligne_info(infos, "Date d'entrée", self._date_fr(pat.date_entree))
        ligne_info(infos, "Date d'hospitalisation", self._date_fr(pat.date_hospitalisation))

        facture = ttk.LabelFrame(cadre, text=" Détail de facturation ", padding=12)
        facture.pack(fill="x", pady=(0, 10))
        ligne_info(facture, "Tarif unitaire / forfait", f"{pat.prise_en_charge.tarif:,.2f} €")
        if pat.prise_en_charge.type_prise == "Hospitalisation":
            ligne_info(facture, "Jours facturés", pat.prise_en_charge.jours_hospitalisation)
            formule = (f"{pat.prise_en_charge.tarif:,.2f} € × "
                       f"{pat.prise_en_charge.jours_hospitalisation} jour(s)")
        elif pat.prise_en_charge.type_prise == "Consultation":
            formule = "Forfait de consultation"
        else:
            formule = "Forfait des urgences"
        ligne_info(facture, "Calcul", formule)
        ligne_info(facture, "Total facturé", f"{pat.total_facture:,.2f} €")

        boutons = ttk.Frame(cadre)
        boutons.pack(fill="x", pady=(4, 0))
        ttk.Button(boutons, text="Modifier ce patient", style="Edit.TButton",
                   command=lambda: (fen.destroy(), self._charger_patient(pat))).pack(side="left")
        ttk.Button(boutons, text="Fermer", command=fen.destroy).pack(side="right")

    @staticmethod
    def _date_fr(valeur):
        if not valeur:
            return "—"
        try:
            return date.fromisoformat(valeur).strftime("%d/%m/%Y")
        except ValueError:
            return valeur

    # ----- actions -----
    def action_valider(self):
        try:
            nom = self.ent_nom.get().strip()
            prenom = self.ent_prenom.get().strip()
            telephone = self.ent_telephone.get().strip()
            statut = self.var_statut.get()
            naissance, tarif, jours = valider_saisie(
                nom, prenom, self.ent_naissance.get().strip(), telephone, statut,
                self.ent_tarif.get().strip(), self.ent_jours.get().strip())
            rue = self.ent_rue.get().strip()
            ville = self.ent_ville.get().strip()
            id_service = self._id_service_par_nom(self.var_service.get())  # None si "(aucun)"
            id_pat = None if self.patient_en_edition is None else self.patient_en_edition.id_patient
            date_hosp = None
            if statut == "Hospitalisation":
                date_hosp = convertir_date_optionnelle(
                    self.ent_date_hospitalisation.get().strip(), "Date d'hospitalisation")
                if not date_hosp:
                    date_hosp = date.today().isoformat()
            date_entree = (self.patient_en_edition.date_entree
                           if self.patient_en_edition else date.today().isoformat())
            try:
                gravite = int(self.var_gravite.get())
            except (TypeError, ValueError):
                raise ValueError("La gravité doit être comprise entre 1 et 5.")
            if gravite not in range(1, 6):
                raise ValueError("La gravité doit être comprise entre 1 et 5.")
            patient = creer_patient(
                statut, id_pat, nom, prenom, naissance, telephone, tarif, jours,
                rue=rue, ville=ville, gravite=gravite, date_entree=date_entree,
                date_hospitalisation=date_hosp, present=self.var_present.get())
            patient.medecins = self._medecins_choisis()
            if id_pat is None:
                self.depot.ajouter_patient(patient, id_service)
                texte = f"{prenom} {nom} ajouté."
            else:
                self.depot.modifier_patient(patient, id_service)
                texte = f"{prenom} {nom} modifié."
        except ValueError as e:
            self.message(str(e), erreur=True)
        except sqlite3.Error as e:
            self.message(f"Erreur base de données : {e}", erreur=True)
        else:
            self._mode_ajout()
            self.rafraichir_liste()
            self.message(texte)

    def action_trier_priorite(self):
        """Trie les patients de la gravité 1 (critique) à 5 (faible)."""
        self.tri_col = next(i for i, col in enumerate(COLONNES) if col[0] == "gravite")
        self.tri_desc = False
        self._maj_entetes()
        self.rafraichir_liste()

    def action_trier(self, colonne):
        if colonne == self.tri_col:
            self.tri_desc = not self.tri_desc
        else:
            self.tri_col, self.tri_desc = colonne, False
        self._maj_entetes()
        self.rafraichir_liste()

    def confirmer(self, titre, texte, action):
        """Petite fenêtre Oui / Non. 'action' n'est appelée que si l'on clique sur Oui."""
        if self.fenetre_confirmation is not None:
            self.fenetre_confirmation.lift()
            return
        fen = tk.Toplevel(self)
        self.fenetre_confirmation = fen
        fen.configure(background=FOND)
        fen.title(titre)
        fen.resizable(False, False)
        fen.transient(self)  # reste au-dessus de la fenêtre principale

        def fermer():
            fen.grab_release()
            fen.destroy()
            self.fenetre_confirmation = None

        def oui():
            fermer()
            action()

        ttk.Label(fen, text=texte, justify="left", padding=(24, 18)).pack()
        boutons = ttk.Frame(fen)
        boutons.pack(pady=(0, 16))
        ttk.Button(boutons, text="Oui, supprimer", style="DangerSolid.TButton",
                   command=oui).pack(side="left", padx=6)
        bouton_non = ttk.Button(boutons, text="Non", width=10, command=fermer)
        bouton_non.pack(side="left", padx=6)
        bouton_non.focus_set()  # par sécurité, « Non » est le choix par défaut
        fen.bind("<Escape>", lambda e: fermer())
        fen.protocol("WM_DELETE_WINDOW", fermer)

        fen.update_idletasks()  # centrer sur la fenêtre principale
        x = self.winfo_rootx() + (self.winfo_width() - fen.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - fen.winfo_reqheight()) // 2
        fen.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        fen.wait_visibility()
        fen.grab_set()  # modale : bloque la fenêtre principale

    def action_supprimer(self):
        selection = self.liste.selection()
        if not selection:
            self.message("Sélectionnez d'abord un patient.", erreur=True)
            return
        pat = self.patients_affiches[int(selection[0])]
        self.confirmer(
            "Confirmer la suppression",
            f"Supprimer le dossier de {pat.prenom} {pat.nom} ?\n\n"
            "Cette action est définitive.",
            lambda: self._supprimer_patient(pat))

    def _supprimer_patient(self, pat):
        try:
            self.depot.supprimer_patient(pat.id_patient)
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
        else:
            if self.patient_en_edition and self.patient_en_edition.id_patient == pat.id_patient:
                self._mode_ajout()
            self.rafraichir_liste()
            self.message(f"Dossier de {pat.prenom} {pat.nom} supprimé.")

    def action_creer_service(self):
        nom = self.ent_nouveau_service.get().strip()
        if not nom or nom in (TOUS, AUCUN):
            self.message("Saisissez un nom de service valide.", erreur=True)
            return
        try:
            lits = int(self.ent_nombre_lits_service.get().strip() or "0")
            if lits < 0:
                raise ValueError("Le nombre de lits ne peut pas être négatif.")
            self.depot.ajouter_service(nom, lits)
        except ValueError as e:
            self.message(str(e) if str(e) else "Le nombre de lits doit être un entier positif.", erreur=True)
            return
        except sqlite3.Error as e:
            self.message(f"Erreur base de données : {e}", erreur=True)
            return
        self.ent_nouveau_service.delete(0, tk.END)
        self.ent_nombre_lits_service.delete(0, tk.END)
        self.ent_nombre_lits_service.insert(0, "0")
        self.rafraichir_services()
        self.message(f"Service « {nom} » créé avec {lits} lit(s).")

    def _charger_capacite_service(self, event=None):
        nom = self.var_supp_service.get()
        service = next((s for s in self.services if s.nom == nom), None)
        if service and hasattr(self, "ent_nombre_lits_service"):
            self.ent_nombre_lits_service.delete(0, tk.END)
            self.ent_nombre_lits_service.insert(0, str(service.nombre_lits))

    def action_modifier_capacite_service(self):
        nom = self.var_supp_service.get()
        service = next((s for s in self.services if s.nom == nom), None)
        if service is None:
            self.message("Choisissez un service pour modifier sa capacité.", erreur=True)
            return
        try:
            lits = int(self.ent_nombre_lits_service.get().strip())
            if lits < 0:
                raise ValueError
            self.depot.modifier_capacite_service(service.id_service, lits)
        except ValueError:
            self.message("Le nombre de lits doit être un entier positif ou nul.", erreur=True)
            return
        except sqlite3.Error as e:
            self.message(f"Erreur base de données : {e}", erreur=True)
            return
        self.rafraichir_services()
        self.message(f"Capacité du service « {nom} » fixée à {lits} lit(s).")

    def action_supprimer_service(self):
        nom = self.var_supp_service.get()
        id_service = self._id_service_par_nom(nom)
        if id_service is None:
            self.message("Choisissez d'abord le service à supprimer.", erreur=True)
            return
        self.confirmer(
            "Confirmer la suppression",
            f"Supprimer le service « {nom} » ?\n\n"
            "Ses patients seront conservés (sans service).",
            lambda: self._supprimer_service(id_service, nom))

    def _supprimer_service(self, id_service, nom):
        try:
            self.depot.supprimer_service(id_service)
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
        else:
            self.rafraichir_services()
            self.rafraichir_liste()
            self.message(f"Service « {nom} » supprimé ; ses patients sont conservés.")

    def action_creer_medecin(self):
        nom = self.ent_nouveau_medecin.get().strip()
        specialite = self.ent_specialite.get().strip()
        if not nom or nom in (TOUS, AUCUN):
            self.message("Saisissez un nom de médecin valide.", erreur=True)
            return
        try:
            self.depot.ajouter_medecin(nom, specialite)
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
        else:
            self.ent_nouveau_medecin.delete(0, tk.END)
            self.ent_specialite.delete(0, tk.END)
            self.rafraichir_medecins()
            self.message(f"Médecin « {nom} » créé.")

    def action_supprimer_medecin(self):
        libelle = self.var_supp_medecin.get()
        medecin = next((m for m in self.medecins if m.libelle == libelle), None)
        if medecin is None:
            self.message("Choisissez d'abord le médecin à supprimer.", erreur=True)
            return
        self.confirmer(
            "Confirmer la suppression",
            f"Supprimer le médecin « {medecin.nom} » ?\n\n"
            "Les patients qu'il suit seront conservés.",
            lambda: self._supprimer_medecin(medecin))

    def _supprimer_medecin(self, medecin):
        try:
            self.depot.supprimer_medecin(medecin.id_medecin)
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
        else:
            self.rafraichir_medecins()
            self.rafraichir_liste()
            self.message(f"Médecin « {medecin.nom} » supprimé ; ses patients sont conservés.")


if __name__ == "__main__":
    Application(Depot()).mainloop()
