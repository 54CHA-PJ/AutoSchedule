## INSTALLATION

**1. Intaller Tesseract-OCR**

[LIEN ICI](https://stackoverflow.com/questions/50951955/pytesseract-tesseractnotfound-error-tesseract-is-not-installed-or-its-not-i)


**2. Installer ChromeDriver**

[LIEN ICI](https://googlechromelabs.github.io/chrome-for-testing/)

- Prendre une version stable
- sauvegarder l'éxécutable sous le dossier "driver" à la racine du projet

**3. Installer les librairies python**

```bash
conda create --name <env> --file requirements.txt
```

## CONFIGURATION

**1. Créer le fichier .env**

Regardez le fichier `.env_example` pour voir les variables à mettre

- Mettez les chemins d'accès aux éxécutables
- Mettez le dossier de téléchargements par défaut de chrome (vous pouvez vérifier en regardant où se télécharge le planning en executant le programme)
- Mettez le lien de Login de ECN (Onboard)
- Mettez les identifiants de connexion

**2. Créez le fichier client.json**

- Ouvrez Google Cloud Platform [ICI](https://console.cloud.google.com/) 
- Créez un projet
- Activez Google Calendar API (APIs & Services > Library > Google Calendar API > Activer)
- Créez des identifiants (APIs & Services > Credentials > ... > OAuth client ID)
- Exportez le client au format JSON
- Renommez le fichier en `client.json` et mettez le à la racine du projet

## Lancer le programme

```bash
python main.py
```

Le programme va ouvrir un navigateur, se connecter à ECN Onboard, télécharger le planning et l'ajouter à votre calendrier Google




