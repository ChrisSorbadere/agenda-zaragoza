#!/data/data/com.termux/files/usr/bin/bash
# Installation du relais "Agenda Zaragoza" sur Android (Termux du Play Store) — à lancer une seule fois
echo "📦 Installation des outils (1 à 3 minutes)..."
pkg install -y python curl >/dev/null 2>&1 || { echo "❌ Échec de l'installation. Tape : pkg update   puis recommence."; exit 1; }

DIR="$HOME/.local/share/agenda-zaragoza"
CONF="$HOME/.config/agenda-zaragoza"
mkdir -p "$DIR" "$CONF"
curl -fsSL "https://raw.githubusercontent.com/ChrisSorbadere/agenda-zaragoza/main/pc/agenda_zgz.py?t=$(date +%s)" -o "$DIR/agenda_zgz.py" \
  || { echo "❌ Téléchargement du script impossible. Vérifie la connexion."; exit 1; }

if [ "$1" = "--nouveau-jeton" ]; then rm -f "$CONF/token"; fi
while [ ! -s "$CONF/token" ]; do
  echo
  echo "🔑 Colle ton jeton GitHub (appui long > Coller). Il ne s'affiche pas. Puis Entrée :"
  read -rs TOKEN; echo
  TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"
  case "$TOKEN" in
    github_pat_*|ghp_*)
      if curl -fsS -o /dev/null -H "Authorization: Bearer $TOKEN" https://api.github.com/repos/ChrisSorbadere/agenda-zaragoza; then
        printf '%s' "$TOKEN" > "$CONF/token"; echo "✅ Jeton accepté."
      else echo "❌ GitHub refuse ce jeton. Recommence."; fi ;;
    *) echo "❌ Ce n'est pas un jeton GitHub (il doit commencer par github_pat_). Recommence." ;;
  esac
done
chmod 600 "$CONF/token"

# Lanceur du relais
printf '#!/data/data/com.termux/files/usr/bin/bash\npython "$HOME/.local/share/agenda-zaragoza/agenda_zgz.py" >> "$HOME/.config/agenda-zaragoza/lancements.txt" 2>&1\n' > "$HOME/relais.sh"
chmod +x "$HOME/relais.sh"

# Planificateur Android (intégré à Termux du Play Store) : toutes les 2 heures, même si Termux est fermé
command -v termux-job-scheduler >/dev/null || pkg install -y termux-api >/dev/null 2>&1
termux-job-scheduler --cancel --job-id 1717 >/dev/null 2>&1
termux-job-scheduler --job-id 1717 --script "$HOME/relais.sh" --period-ms 7200000 --persisted true --network any >/dev/null

# Démarrage automatique au redémarrage du téléphone
mkdir -p "$HOME/.termux/boot"
cp "$HOME/relais.sh" "$HOME/.termux/boot/agenda.sh"; chmod +x "$HOME/.termux/boot/agenda.sh"

# Essai à chaque ouverture de Termux
touch "$HOME/.bashrc"
grep -v "agenda-zaragoza" "$HOME/.bashrc" > "$HOME/.bashrc.tmp" || true
mv "$HOME/.bashrc.tmp" "$HOME/.bashrc"
echo '( nohup python "$HOME/.local/share/agenda-zaragoza/agenda_zgz.py" >> "$HOME/.config/agenda-zaragoza/lancements.txt" 2>&1 & )   # agenda-zaragoza' >> "$HOME/.bashrc"

echo
echo "🚀 Premier essai..."
if python "$DIR/agenda_zgz.py" --force; then
  echo
  termux-job-scheduler -p
  echo
  echo "✅ Installation terminée. Android relancera le relais toutes les 2 heures, même Termux fermé."
fi
