# Agenda de Zaragoza — passerelle de données

Le site de la mairie de Zaragoza n'accepte que les connexions depuis l'Espagne.
Un petit relais installé sur le PC de Chris (Linux Mint) télécharge donc une fois par jour
l'agenda officiel (données ouvertes) pour les 16 jours suivants et le publie ici dans
`data/agenda.json`. La tâche programmée Claude du mardi lit ce fichier pour préparer
l'email « Agenda de Zaragoza — week-end ».

Installation sur le PC (une seule fois) :

    bash <(curl -fsSL https://raw.githubusercontent.com/ChrisSorbadere/agenda-zaragoza/main/pc/installer.sh)

Journal du relais : `~/.config/agenda-zaragoza/journal.txt`
Forcer une mise à jour : `python3 ~/.local/share/agenda-zaragoza/agenda_zgz.py --force`
