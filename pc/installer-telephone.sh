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

# Boucle de fond : relance le relais toutes les 2 heures (il ne publie qu'une fois par jour)
cat > "$DIR/boucle.sh" <<BOUCLE
#!/data/data/com.termux/files/usr/bin/bash
PIDF="$CONF/boucle.pid"
if [ -f "\$PIDF" ] && kill -0 "\$(cat "\$PIDF")" 2>/dev/null; then exit 0; fi
echo \$\$ > "\$PIDF"
while true; do
  python "$DIR/agenda_zgz.py" >> "$CONF/lancements.txt" 2>&1
  sleep 7200
done
BOUCLE
chmod +x "$DIR/boucle.sh"

# Démarrage automatique à chaque ouverture de Termux
touch "$HOME/.bashrc"
grep -v "agenda-zaragoza" "$HOME/.bashrc" > "$HOME/.bashrc.tmp" || true
mv "$HOME/.bashrc.tmp" "$HOME/.bashrc"
cat >> "$HOME/.bashrc" <<RC
( nohup python "$DIR/agenda_zgz.py" >> "$CONF/lancements.txt" 2>&1 & ) ; ( nohup "$DIR/boucle.sh" >/dev/null 2>&1 & )   # agenda-zaragoza
RC

echo
echo "🚀 Premier essai..."
if python "$DIR/agenda_zgz.py" --force; then
  ( nohup "$DIR/boucle.sh" >/dev/null 2>&1 & )
  echo
  echo "✅ Installation terminée."
  echo "Laisse Termux ouvert en arrière-plan (ne le ferme pas depuis les applis récentes)."
  echo "Après un redémarrage du téléphone, ouvre simplement Termux une fois."
fi
