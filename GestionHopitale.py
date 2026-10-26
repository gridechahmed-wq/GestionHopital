import sqlite3
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime
from tkinter import ttk


# =====================================================================
# MODÈLES MÉTIER (héritage, composition, agrégation)
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

    def __init__(self, id_service, nom):
        self.id_service = id_service
        self.nom = nom
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
                 service=None, rue="", ville=""):
        self.id_patient = id_patient
        self.nom = nom
        self.prenom = prenom
        self.date_naissance = date_naissance  # objet datetime.date
        self.telephone = telephone
        self.prise_en_charge = prise_en_charge  # composition
        self.adresse = Adresse(rue, ville)  # composition : créée par le patient lui-même
        self.service = service  # agrégation
        self.medecins = []  # agrégation : liste d'objets Medecin

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
                  service=None, rue="", ville=""):
    prise = PriseEnCharge(type_prise, tarif, jours)
    return TYPES_PATIENTS[type_prise](
        id_patient, nom, prenom, date_naissance, telephone, prise, service, rue, ville)


# =====================================================================
# VALIDATION
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


def telephone_valide(telephone):
    """Facultatif ; sinon chiffres, espaces, + - . ( ) et 8 à 15 chiffres."""
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
    if not 0 <= tarif <= 1000000 or round(tarif, 2) != tarif:
        raise ValueError("Tarif invalide (0 à 1 000 000 €, 2 décimales max).")

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
# BASE DE DONNÉES (schéma inchangé : 4 tables)
# =====================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS services
(
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
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
    service_id            INTEGER,
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
        self.conn = sqlite3.connect(fichier)
        self.conn.execute("PRAGMA foreign_keys = ON")  # sinon SQLite ignore les clés étrangères
        self.conn.executescript(SCHEMA)

    def _ecrire(self, sql, params=(), message_doublon="Valeur déjà existante."):
        try:
            with self.conn:  # commit automatique (ou rollback en cas d'erreur)
                self.conn.execute(sql, params)
        except sqlite3.IntegrityError:
            raise ValueError(message_doublon)

    # ----- services et médecins -----
    def lister_services(self):
        lignes = self.conn.execute("SELECT id, nom FROM services ORDER BY nom")
        return [Service(i, n) for i, n in lignes]

    def ajouter_service(self, nom):
        self._ecrire("INSERT INTO services (nom) VALUES (?)", (nom,),
                     "Ce service existe déjà.")

    def supprimer_service(self, id_service):
        # Les patients restent : service_id passe à NULL (agrégation).
        self._ecrire("DELETE FROM services WHERE id = ?", (id_service,))

    def lister_medecins(self):
        lignes = self.conn.execute("SELECT id, nom, specialite FROM medecins ORDER BY nom")
        return [Medecin(i, n, s) for i, n, s in lignes]

    def ajouter_medecin(self, nom, specialite=""):
        self._ecrire("INSERT INTO medecins (nom, specialite) VALUES (?, ?)",
                     (nom, specialite), "Ce médecin existe déjà.")

    def supprimer_medecin(self, id_medecin):
        # Seuls les suivis disparaissent (CASCADE) : les patients restent.
        self._ecrire("DELETE FROM medecins WHERE id = ?", (id_medecin,))

    # ----- patients -----
    def enregistrer_patient(self, patient, id_service):
        """Ajoute le patient (id_patient = None) ou le modifie."""
        p = patient.prise_en_charge
        valeurs = (patient.nom, patient.prenom, patient.date_naissance.isoformat(),
                   patient.telephone, patient.adresse.rue, patient.adresse.ville,
                   p.type_prise, p.tarif, p.jours_hospitalisation, id_service)
        try:
            with self.conn:  # tout réussit ensemble ou rien n'est écrit
                if patient.id_patient is None:
                    patient.id_patient = self.conn.execute(
                        "INSERT INTO patients (nom, prenom, date_naissance, telephone, rue, "
                        "ville, type_prise_en_charge, tarif, jours_hospitalisation, "
                        "service_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        valeurs).lastrowid
                else:
                    curseur = self.conn.execute(
                        "UPDATE patients SET nom = ?, prenom = ?, date_naissance = ?, "
                        "telephone = ?, rue = ?, ville = ?, type_prise_en_charge = ?, "
                        "tarif = ?, jours_hospitalisation = ?, service_id = ? "
                        "WHERE id = ?",
                        valeurs + (patient.id_patient,))
                    if curseur.rowcount == 0:
                        raise ValueError("Ce patient n'existe plus.")
                    self.conn.execute("DELETE FROM suivis WHERE patient_id = ?",
                                      (patient.id_patient,))
                self.conn.executemany(
                    "INSERT INTO suivis (patient_id, medecin_id) VALUES (?, ?)",
                    [(patient.id_patient, m.id_medecin) for m in patient.medecins])
        except sqlite3.IntegrityError:
            raise ValueError("Ce patient existe déjà (même nom, prénom et date de naissance).")

    def supprimer_patient(self, id_patient):
        self._ecrire("DELETE FROM patients WHERE id = ?", (id_patient,))

    def lister_patients(self, recherche=""):
        motif = f"%{recherche}%"
        lignes = self.conn.execute(
            "SELECT p.id, p.nom, p.prenom, p.date_naissance, p.telephone, "
            "p.type_prise_en_charge, p.tarif, p.jours_hospitalisation, s.id, s.nom, "
            "p.rue, p.ville "
            "FROM patients p LEFT JOIN services s ON s.id = p.service_id "
            "WHERE p.nom LIKE ? OR p.prenom LIKE ? OR p.telephone LIKE ? "
            "ORDER BY p.nom COLLATE NOCASE, p.prenom COLLATE NOCASE, p.id",
            (motif, motif, motif)).fetchall()
        suivis = self.conn.execute(
            "SELECT sv.patient_id, m.id, m.nom, m.specialite FROM suivis sv "
            "JOIN medecins m ON m.id = sv.medecin_id ORDER BY m.nom").fetchall()

        medecins = {}
        medecins_par_patient = {}
        for id_p, id_m, nom_m, specialite in suivis:
            medecins.setdefault(id_m, Medecin(id_m, nom_m, specialite))
            medecins_par_patient.setdefault(id_p, []).append(medecins[id_m])

        services = {}
        resultat = []
        for (id_p, nom, prenom, naissance, tel, type_prise, tarif, jours, id_s, nom_s,
             rue, ville) in lignes:
            patient = creer_patient(
                type_prise, id_p, nom, prenom, date.fromisoformat(naissance), tel, tarif, jours,
                rue=rue or "", ville=ville or "")
            if id_s is not None:
                services.setdefault(id_s, Service(id_s, nom_s))
                services[id_s].ajouter_patient(patient)
            for medecin in medecins_par_patient.get(id_p, []):
                medecin.ajouter_patient(patient)
            resultat.append(patient)
        return resultat


# =====================================================================
# INTERFACE TKINTER
# =====================================================================
AUCUN = "(aucun)"

# Palette
FOND = "#F3F4F6"
TEXTE = "#1F2937"
GRIS = "#6B7280"
BORDURE = "#D1D5DB"
VERT, VERT_FONCE = "#2E7D32", "#256628"
BLEU, BLEU_FONCE = "#1976D2", "#1565C0"
ROUGE, ROUGE_FONCE = "#B71C1C", "#8E1515"

# (clé, libellé) des champs texte du formulaire : rangés 2 par ligne
CHAMPS = (("nom", "Nom *"), ("prenom", "Prénom *"), ("naissance", "Naissance *"),
          ("telephone", "Téléphone"), ("tarif", "Tarif (€) *"),
          ("jours", "Jours d'hospitalisation"), ("rue", "Rue"), ("ville", "Ville"))

# (clé, titre affiché, largeur en pixels, alignement)
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
)


class Application(tk.Tk):
    def __init__(self, depot):
        super().__init__()
        self.title("Gestion de l'hôpital")
        self.minsize(1300, 760)
        self.configure(background=FOND)
        self._plein_ecran()
        self.depot = depot
        self.patients = []
        self.services = []
        self.medecins = []
        self.en_edition = None
        self.fenetre_confirmation = None

        self.var_statut = tk.StringVar(value="Consultation")
        self.var_service = tk.StringVar(value=AUCUN)
        self.var_recherche = tk.StringVar()

        self._appliquer_style()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._construire_haut()
        self._construire_liste()
        self.lbl_message = ttk.Label(self, anchor="w", padding=(14, 8))
        self.lbl_message.grid(row=2, column=0, sticky="ew")
        self.message("Prêt.", info=True)
        self._raccourcis()

        self.var_recherche.trace_add("write", lambda *a: self.rafraichir_liste())
        self._mode_ajout()
        self.rafraichir_services()
        self.rafraichir_medecins()
        self.rafraichir_liste()

    def _plein_ecran(self):
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
        self.ent_service, _, self.var_supp_service, self.menu_supp_service = \
            self._bloc_gestion(droite, 0, "Services", self.action_creer_service,
                               self.action_supprimer_service)
        self.ent_medecin, self.ent_specialite, self.var_supp_medecin, \
            self.menu_supp_medecin = self._bloc_gestion(
                droite, 1, "Médecins", self.action_creer_medecin,
                self.action_supprimer_medecin, libelle_extra="Spécialité")

    def _bloc_gestion(self, parent, ligne, titre, creer, supprimer, libelle_extra=None):
        """Bloc « Créer / Supprimer » : retourne (champ, champ extra, variable, liste)."""
        bloc = ttk.LabelFrame(parent, text=f" {titre} ", padding=10)
        bloc.grid(row=ligne, column=0, sticky="nsew", pady=(0, 6) if ligne == 0 else 0)
        bloc.columnconfigure(1, weight=1)

        ttk.Label(bloc, text="Nouveau").grid(row=0, column=0, sticky="w", padx=(0, 10))
        entree = ttk.Entry(bloc)
        entree.grid(row=0, column=1, sticky="ew", pady=4)
        entree.bind("<Return>", lambda e: creer())
        ttk.Button(bloc, text="Créer", command=creer).grid(
            row=0, column=2, sticky="ew", padx=(8, 0))

        extra, suite = None, 1
        if libelle_extra:
            ttk.Label(bloc, text=libelle_extra).grid(row=1, column=0, sticky="w", padx=(0, 10))
            extra = ttk.Entry(bloc)
            extra.grid(row=1, column=1, sticky="ew", pady=4)
            extra.bind("<Return>", lambda e: creer())
            suite = 2

        ttk.Label(bloc, text="Existant").grid(row=suite, column=0, sticky="w", padx=(0, 10))
        var = tk.StringVar()
        choix = self._combo(bloc, var, ())
        choix.grid(row=suite, column=1, sticky="ew", pady=4)
        ttk.Button(bloc, text="Supprimer", style="Danger.TButton", command=supprimer).grid(
            row=suite, column=2, sticky="ew", padx=(8, 0))
        return entree, extra, var, choix

    def _construire_formulaire(self, parent):
        self.cadre_form = ttk.LabelFrame(parent, padding=12)
        cadre = self.cadre_form
        cadre.grid(row=0, column=0, sticky="nsew")
        # colonnes de champs de même largeur ; colonnes des libellés à largeur fixe
        cadre.columnconfigure(0, minsize=110)
        cadre.columnconfigure(1, weight=1, uniform="champ")
        cadre.columnconfigure(2, minsize=170)
        cadre.columnconfigure(3, weight=1, uniform="champ")

        self.champs = {}
        for i, (cle, texte) in enumerate(CHAMPS):
            ligne, colonne = divmod(i, 2)
            self._etiquette(cadre, texte, ligne, colonne * 2)
            self.champs[cle] = ttk.Entry(cadre)
            self.champs[cle].grid(row=ligne, column=colonne * 2 + 1, sticky="ew", pady=4)

        self._etiquette(cadre, "Prise en charge", 4, 0)
        self._combo(cadre, self.var_statut, list(TYPES_PATIENTS)).grid(
            row=4, column=1, sticky="ew", pady=4)
        self._etiquette(cadre, "Service", 4, 2)
        self.menu_service = self._combo(cadre, self.var_service, ())
        self.menu_service.grid(row=4, column=3, sticky="ew", pady=4)

        self._etiquette(cadre, "Médecins", 5, 0, sticky="nw", pady=8)
        cadre_med = ttk.Frame(cadre)
        cadre_med.grid(row=5, column=1, sticky="ew", pady=4)
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

        boutons = ttk.Frame(cadre)
        boutons.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.btn_valider = ttk.Button(boutons, command=self.action_valider)
        self.btn_valider.pack(side="left")
        self.btn_annuler = ttk.Button(boutons, text="Annuler", command=self._mode_ajout)
        ttk.Label(boutons, text="* champ obligatoire   •   date : JJ/MM/AAAA",
                  foreground=GRIS).pack(side="right")

    @staticmethod
    def _etiquette(parent, texte, ligne, colonne, sticky="w", pady=4):
        etiquette = ttk.Label(parent, text=texte)
        etiquette.grid(row=ligne, column=colonne, sticky=sticky, pady=pady,
                       padx=(16 if colonne else 0, 8))
        return etiquette

    @staticmethod
    def _combo(parent, variable, valeurs):
        return ttk.Combobox(parent, textvariable=variable, values=list(valeurs),
                            state="readonly")

    def _construire_liste(self):
        self.cadre_liste = ttk.LabelFrame(self, padding=10)
        cadre = self.cadre_liste
        cadre.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        cadre.columnconfigure(0, weight=1)
        cadre.rowconfigure(1, weight=1)

        barre = ttk.Frame(cadre)
        barre.grid(row=0, column=0, sticky="ew")
        ttk.Label(barre, text="Recherche").pack(side="left")
        ttk.Entry(barre, textvariable=self.var_recherche, width=22).pack(
            side="left", padx=(6, 18))
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
        for cle, titre, largeur, ancre in COLONNES:
            self.liste.heading(cle, text=titre, anchor=ancre)
            # largeur fixe : seule la colonne « Médecins » s'étire si on agrandit la fenêtre
            self.liste.column(cle, width=largeur, minwidth=largeur, anchor=ancre,
                              stretch=(cle == "medecins"))
        self.liste.grid(row=0, column=0, sticky="nsew")
        ascenseur.config(command=self.liste.yview)
        self.liste.bind("<Double-Button-1>", self.action_charger)

        # Lignes en alternance
        self.liste.tag_configure("pair", background="white")
        self.liste.tag_configure("impair", background="#F3F6FA")

        # Message affiché quand la liste est vide
        self.lbl_vide = ttk.Label(self.liste, background="white", foreground=GRIS,
                                  font=(self.police, 11))

        ttk.Label(cadre, foreground=GRIS,
                  text="Double-clic : modifier   •   Suppr : supprimer la ligne").grid(
            row=2, column=0, sticky="w", pady=(8, 0))

    def _raccourcis(self):
        for champ in self.champs.values():  # Entrée : valider le formulaire
            champ.bind("<Return>", lambda e: self.action_valider())
        self.liste.bind("<Delete>", lambda e: self.action_supprimer())
        # Échap : quitter le mode modification
        self.bind("<Escape>", lambda e: self._mode_ajout() if self.en_edition else None)

    # ----- affichage -----
    def message(self, texte, erreur=False, info=False):
        if erreur:
            fond, couleur = "#FDE8E8", ROUGE
        elif info:
            fond, couleur = "#E8F0FE", "#1A4E9C"
        else:
            fond, couleur = "#E6F4EA", "#1E6B34"
        self.lbl_message.config(text=texte, background=fond, foreground=couleur)

    def rafraichir_services(self):
        self.services = self.depot.lister_services()
        noms = [s.nom for s in self.services]
        self.menu_service.config(values=[AUCUN] + noms)
        if self.var_service.get() not in noms:
            self.var_service.set(AUCUN)
        self.menu_supp_service.config(values=noms)
        if self.var_supp_service.get() not in noms:
            self.var_supp_service.set(noms[0] if noms else "")

    def rafraichir_medecins(self):
        choisis = {m.nom for m in self._medecins_choisis()}  # garder la sélection
        self.medecins = self.depot.lister_medecins()
        self.liste_medecins.delete(0, tk.END)
        for i, medecin in enumerate(self.medecins):
            self.liste_medecins.insert(tk.END, medecin.libelle)
            if medecin.nom in choisis:
                self.liste_medecins.selection_set(i)
        libelles = [m.libelle for m in self.medecins]
        self.menu_supp_medecin.config(values=libelles)
        if self.var_supp_medecin.get() not in libelles:
            self.var_supp_medecin.set(libelles[0] if libelles else "")

    def rafraichir_liste(self):
        recherche = self.var_recherche.get().strip()
        self.patients = self.depot.lister_patients(recherche)
        self.liste.delete(*self.liste.get_children())
        for i, pat in enumerate(self.patients):
            self.liste.insert("", tk.END, iid=str(i), tags=("impair" if i % 2 else "pair",),
                              values=(
                pat.id_patient, pat.nom, pat.prenom, pat.naissance_affichee, pat.telephone,
                pat.prise_en_charge.type_prise, pat.service.nom if pat.service else AUCUN,
                pat.adresse.ville,
                ", ".join(m.nom for m in pat.medecins), pat.facture_affichee))
        self.cadre_liste.config(text=f" Patients ({len(self.patients)}) ")

        if self.patients:
            self.lbl_vide.place_forget()
        else:
            self.lbl_vide.config(text="Aucun résultat pour cette recherche." if recherche
                                 else "Aucun patient pour l'instant.")
            self.lbl_vide.place(relx=0.5, rely=0.3, anchor="center")

    def _medecins_choisis(self):
        return [self.medecins[i] for i in self.liste_medecins.curselection()]

    def _id_service_par_nom(self, nom):
        return next((s.id_service for s in self.services if s.nom == nom), None)

    # ----- mode ajout / mode modification -----
    def _remplir(self, cle, valeur):
        self.champs[cle].delete(0, tk.END)
        self.champs[cle].insert(0, valeur)

    def _mode_ajout(self):
        self.en_edition = None
        self.cadre_form.config(text=" Nouveau patient ")
        self.btn_valider.config(text="Ajouter le patient", style="Accent.TButton")
        self.btn_annuler.pack_forget()
        for cle in self.champs:
            self._remplir(cle, "1" if cle == "jours" else "")
        self.liste_medecins.selection_clear(0, tk.END)

    def action_charger(self, event):
        """Double-clic : charge le patient dans le formulaire."""
        ligne = self.liste.identify_row(event.y)
        if not ligne:  # clic sur l'en-tête ou dans le vide
            return
        pat = self.patients[int(ligne)]
        self.en_edition = pat
        self.cadre_form.config(text=f" Modifier : {pat.prenom} {pat.nom} ")
        self.btn_valider.config(text="Enregistrer les modifications", style="Edit.TButton")
        self.btn_annuler.pack(side="left", padx=(8, 0))
        prise = pat.prise_en_charge
        for cle, valeur in (("nom", pat.nom), ("prenom", pat.prenom),
                            ("naissance", pat.naissance_affichee),
                            ("telephone", pat.telephone), ("tarif", f"{prise.tarif:.2f}"),
                            ("rue", pat.adresse.rue), ("ville", pat.adresse.ville),
                            ("jours", prise.jours_hospitalisation or "1")):
            self._remplir(cle, valeur)
        self.var_statut.set(prise.type_prise)
        self.var_service.set(pat.service.nom if pat.service else AUCUN)
        ids = {m.id_medecin for m in pat.medecins}
        self.liste_medecins.selection_clear(0, tk.END)
        for k, medecin in enumerate(self.medecins):
            if medecin.id_medecin in ids:
                self.liste_medecins.selection_set(k)
        self.message("Modifiez les champs puis enregistrez (Entrée) ou annulez (Échap).",
                     info=True)

    # ----- actions -----
    def _essayer(self, action, succes):
        """Exécute action(); affiche l'erreur ou le message de succès. Retourne True/False."""
        try:
            action()
        except (ValueError, sqlite3.Error) as e:
            self.message(str(e), erreur=True)
            return False
        self.message(succes)
        return True

    def action_valider(self):
        saisie = {cle: champ.get().strip() for cle, champ in self.champs.items()}
        statut = self.var_statut.get()
        id_patient = self.en_edition.id_patient if self.en_edition else None

        def enregistrer():
            naissance, tarif, jours = valider_saisie(
                saisie["nom"], saisie["prenom"], saisie["naissance"], saisie["telephone"],
                statut, saisie["tarif"], saisie["jours"])
            patient = creer_patient(
                statut, id_patient, saisie["nom"], saisie["prenom"], naissance,
                saisie["telephone"], tarif, jours, rue=saisie["rue"], ville=saisie["ville"])
            patient.medecins = self._medecins_choisis()
            self.depot.enregistrer_patient(patient,
                                           self._id_service_par_nom(self.var_service.get()))

        verbe = "modifié" if id_patient else "ajouté"
        if self._essayer(enregistrer, f"{saisie['prenom']} {saisie['nom']} {verbe}."):
            self._mode_ajout()
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

    def _confirmer_suppression(self, texte, supprimer, succes, apres):
        """Demande confirmation, supprime, puis appelle apres() si tout a réussi."""
        def action():
            if self._essayer(supprimer, succes):
                apres()
        self.confirmer("Confirmer la suppression", texte, action)

    def action_supprimer(self):
        selection = self.liste.selection()
        if not selection:
            self.message("Sélectionnez d'abord un patient.", erreur=True)
            return
        pat = self.patients[int(selection[0])]

        def apres():
            if self.en_edition and self.en_edition.id_patient == pat.id_patient:
                self._mode_ajout()
            self.rafraichir_liste()

        self._confirmer_suppression(
            f"Supprimer le dossier de {pat.prenom} {pat.nom} ?\n\nCette action est définitive.",
            lambda: self.depot.supprimer_patient(pat.id_patient),
            f"Dossier de {pat.prenom} {pat.nom} supprimé.", apres)

    def action_creer_service(self):
        nom = self.ent_service.get().strip()
        if nom and self._essayer(lambda: self.depot.ajouter_service(nom),
                                 f"Service « {nom} » créé."):
            self.ent_service.delete(0, tk.END)
            self.rafraichir_services()

    def action_supprimer_service(self):
        nom = self.var_supp_service.get()
        id_service = self._id_service_par_nom(nom)
        if id_service is None:
            self.message("Choisissez d'abord le service à supprimer.", erreur=True)
            return

        def apres():
            self.rafraichir_services()
            self.rafraichir_liste()

        self._confirmer_suppression(
            f"Supprimer le service « {nom} » ?\n\nSes patients seront conservés (sans service).",
            lambda: self.depot.supprimer_service(id_service),
            f"Service « {nom} » supprimé ; ses patients sont conservés.", apres)

    def action_creer_medecin(self):
        nom = self.ent_medecin.get().strip()
        specialite = self.ent_specialite.get().strip()
        if nom and self._essayer(lambda: self.depot.ajouter_medecin(nom, specialite),
                                 f"Médecin « {nom} » créé."):
            self.ent_medecin.delete(0, tk.END)
            self.ent_specialite.delete(0, tk.END)
            self.rafraichir_medecins()

    def action_supprimer_medecin(self):
        libelle = self.var_supp_medecin.get()
        medecin = next((m for m in self.medecins if m.libelle == libelle), None)
        if medecin is None:
            self.message("Choisissez d'abord le médecin à supprimer.", erreur=True)
            return

        def apres():
            self.rafraichir_medecins()
            self.rafraichir_liste()

        self._confirmer_suppression(
            f"Supprimer le médecin « {medecin.nom} » ?\n\nLes patients qu'il suit seront conservés.",
            lambda: self.depot.supprimer_medecin(medecin.id_medecin),
            f"Médecin « {medecin.nom} » supprimé ; ses patients sont conservés.", apres)


if __name__ == "__main__":
    Application(Depot()).mainloop()
