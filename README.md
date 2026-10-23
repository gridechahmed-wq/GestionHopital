# 🏥 Gestion de l’hôpital

Application de bureau de gestion hospitalière développée en **Python**, avec **Tkinter/ttk** pour l’interface graphique et **SQLite** pour le stockage des données. Ce projet met en pratique la programmation orientée objet, la validation des saisies et la gestion d’une base de données relationnelle.

## ✨ Fonctionnalités

### 👨‍⚕️ Gestion des patients
- Ajouter, modifier et supprimer des dossiers patients.
- Enregistrer les informations personnelles, les coordonnées et les dates pertinentes.
- Gérer trois types de prise en charge : Consultation, Hospitalisation et Urgence.
- Définir le niveau de gravité du patient sur une échelle de 1 à 5.
- Suivre la présence des patients dans l’établissement.
- Associer les patients à des services et à des médecins.
- Rechercher, filtrer et trier les patients.
- Afficher les montants des factures et demander confirmation avant les suppressions.

### 🏥 Gestion des services
- Créer et supprimer des services hospitaliers.
- Définir et modifier le nombre de lits disponibles par service.
- Visualiser l’occupation des lits depuis le tableau de bord.
- Conserver les dossiers des patients lorsqu’un service est supprimé.

### 🩺 Gestion des médecins
- Ajouter des médecins et renseigner leur spécialité.
- Associer plusieurs médecins à un patient.
- Supprimer un médecin sans supprimer les dossiers des patients concernés.

### 📊 Tableau de bord
- Nombre de patients présents.
- Nombre de patients hospitalisés.
- Nombre d’urgences du jour.
- Total facturé.
- Barres de progression indiquant le taux d’occupation des lits par service.
- Alertes lorsque la capacité d’un service approche de la saturation.
- Alertes concernant les séjours prolongés, les patients mineurs et les patients de plus de 75 ans.

### 💶 Calcul automatique des factures
- **Consultation :** facture égale au tarif de la consultation.
- **Hospitalisation :** tarif journalier multiplié par le nombre de jours d’hospitalisation.
- **Urgence :** facture égale au forfait d’urgence, avec affichage « Aucun frais » lorsque le tarif est nul.

## 🧰 Technologies utilisées

| Technologie | Utilisation |
|---|---|
| Python 3 | Logique de l’application et programmation orientée objet |
| Tkinter / ttk | Création de l’interface graphique |
| SQLite | Stockage des données dans une base locale |
| `sqlite3` | Connexion et exécution des requêtes SQL |
| `datetime` | Gestion des dates et calcul de l’âge |

Aucun paquet externe n’est normalement nécessaire. Tkinter doit être disponible dans l’installation de Python.

## 🗂️ Base de données

La base de données `hopital.db` est créée automatiquement au premier lancement.

Elle contient quatre tables principales :

| Table | Description |
|---|---|
| `patients` | Informations des patients, facturation, gravité et présence |
| `services` | Services hospitaliers et capacité en lits |
| `medecins` | Médecins et spécialités |
| `suivis` | Relations entre les patients et leurs médecins |

Les clés étrangères et les contraintes SQL contribuent à assurer la cohérence des données.

## 🧱 Programmation orientée objet

Le projet applique plusieurs concepts fondamentaux de la programmation orientée objet :

- **Héritage :** les classes `PatientConsultation`, `PatientHospitalise` et `PatientUrgence` héritent de `Patient`.
- **Composition :** chaque patient possède un objet `Adresse` et un objet `PriseEnCharge`.
- **Agrégation :** les services et les médecins existent indépendamment des patients.
- **Polymorphisme :** chaque type de patient dispose de son propre calcul de facture.
- **Séparation des responsabilités :** la classe `Depot` gère les accès à la base de données, tandis que `Application` gère l’interface graphique.



