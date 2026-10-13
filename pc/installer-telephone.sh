#!/data/data/com.termux/files/usr/bin/bash
# Installation du relais "Agenda Zaragoza" sur Android (Termux) — à lancer une seule fois
set -e
echo "📦 Installation des outils (1 à 3 minutes)..."
pkg install -y python termux-api curl >/dev/null 2>&1 || { echo "❌ Échec de l'installation des paquets. Lance 'pkg update' puis recommence."; exit 1; }

DIR="$HOME/.local/share/agenda-zaragoza"
CONF="$HOME/.config/agenda-zaragoza"
mkdir -p "$DIR" "$CONF"
curl -fsSL "https://raw.githubusercontent.com/ChrisSorbadere/agenda-zaragoza/main/pc/agenda_zgz.py?t=$(date +%s)" -o "$DIR/agenda_zgz.py"

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

# Lanceur appelé par Android
cat > "$DIR/lancer.sh" <<LANCEUR
#!/data/data/com.termux/files/usr/bin/bash
python "$DIR/agenda_zgz.py" >> "$CONF/lancements.txt" 2>&1
LANCEUR
chmod +x "$DIR/lancer.sh"

echo
echo "⏰ Programmation (toutes les 2 heures, quand il y a du réseau)..."
termux-job-scheduler --cancel --job-id 1717 >/dev/null 2>&1 || true
timeout 20 termux-job-scheduler --job-id 1717 --script "$DIR/lancer.sh" \
  --period-ms 7200000 --persisted true --network any >/dev/null 2>&1 \
  || { echo "❌ La programmation a échoué : l'application Termux:API est-elle installée ?"; exit 1; }

echo
echo "🚀 Premier essai..."
python "$DIR/agenda_zgz.py" --force && echo && echo "✅ Installation terminée. Le téléphone mettra l'agenda à jour tout seul chaque jour."
