# Agenda de Zaragoza — passerelle de données

Chaque nuit, une GitHub Action télécharge l'agenda officiel de la mairie de Zaragoza
(données ouvertes) pour les 16 jours suivants et l'enregistre dans `data/agenda.json`.
Ce fichier est lu par la tâche programmée Claude qui envoie l'agenda du week-end chaque mardi.
