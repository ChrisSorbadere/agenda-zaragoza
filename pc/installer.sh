#!/bin/bash
# Installation du relais "Agenda Zaragoza" sur Linux Mint (à lancer une seule fois)
set -e
DIR="$HOME/.local/share/agenda-zaragoza"
CONF="$HOME/.config/agenda-zaragoza"
mkdir -p "$DIR" "$CONF"
echo "Téléchargement du script..."
curl -fsSL https://raw.githubusercontent.com/ChrisSorbadere/agenda-zaragoza/main/pc/agenda_zgz.py -o "$DIR/agenda_zgz.py"
chmod +x "$DIR/agenda_zgz.py"
if [ "$1" = "--nouveau-jeton" ]; then rm -f "$CONF/token"; fi
while [ ! -s "$CONF/token" ]; do
  echo
  echo "Colle ton jeton GitHub avec Ctrl+Maj+V (il ne s'affichera pas), puis Entrée :"
  read -rs TOKEN; echo
  TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"
  case "$TOKEN" in
    github_pat_*|ghp_*)
      if curl -fsS -o /dev/null -H "Authorization: Bearer $TOKEN" https://api.github.com/repos/ChrisSorbadere/agenda-zaragoza; then
        printf '%s' "$TOKEN" > "$CONF/token"; echo "Jeton accepté."
      else echo "❌ GitHub refuse ce jeton. Recommence."; fi ;;
    *) echo "❌ Ce n'est pas un jeton GitHub (il doit commencer par github_pat_). Recommence." ;;
  esac
done
chmod 600 "$CONF/token"
# Tâches planifiées : au démarrage (après 3 min) + toutes les 2 heures.
# Le script ne travaille qu'une fois par jour.
LIGNE1="@reboot sleep 180 && /usr/bin/python3 $DIR/agenda_zgz.py >/dev/null 2>&1"
LIGNE2="17 */2 * * * /usr/bin/python3 $DIR/agenda_zgz.py >/dev/null 2>&1"
( crontab -l 2>/dev/null | grep -v agenda_zgz.py ; echo "$LIGNE1" ; echo "$LIGNE2" ) | crontab -
echo
echo "Premier essai..."
/usr/bin/python3 "$DIR/agenda_zgz.py" --force && echo && echo "✅ Installation terminée. Le relais tournera tout seul chaque jour."
