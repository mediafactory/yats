# signal-cli — Registrierung je Web (mf / bagarino / schiwago)

Auf dem alten System „geht Signal nicht mehr“ — Ursache ist i. d. R. eine veraltete
signal-cli-Version bzw. ein abgelaufener Account-Status. Mit aktueller signal-cli +
Java 21 und Neuregistrierung der Nummern ist es wieder funktionsfähig.

Jede Web hat **eine eigene Nummer** und einen **eigenen Config-Dir**
`/var/lib/signal-cli/<site>` (von `install-signal-cli.sh` angelegt, owner `yats`).

> Wichtig: signal-cli wird im Betrieb über `sudo` als root aufgerufen
> (`SIGNAL_BIN = sudo /usr/local/bin/signal-cli`). Damit Account-State und
> Berechtigungen konsistent sind, die Registrierung **ebenfalls mit `sudo`** und
> demselben `--config` ausführen.

## 1. Captcha holen
Signal verlangt bei der Registrierung meist ein Captcha:
- https://signalcaptchas.org/registration/generate.html öffnen,
- Captcha lösen, den `signalcaptcha://…`-Link kopieren (Rechtsklick → Link kopieren),
- als `--captcha 'signalcaptcha://...'` übergeben.

## 2. Registrieren + verifizieren (pro Nummer wiederholen)
```bash
SITE=mf
NUM=+49XXXXXXXXXX            # die Nummer dieser Web
CFG=/var/lib/signal-cli/$SITE

# Registrierung anstoßen (SMS):
sudo signal-cli --config "$CFG" -a "$NUM" register --captcha 'signalcaptcha://...'
# (Sprachanruf statt SMS: zusätzlich --voice)

# Code aus der SMS verifizieren:
sudo signal-cli --config "$CFG" -a "$NUM" verify 123456

# Profilnamen setzen (optional, erscheint beim Empfänger):
sudo signal-cli --config "$CFG" -a "$NUM" updateProfile --name "YATS $SITE"
```

## 3. Testnachricht
```bash
sudo signal-cli --config /var/lib/signal-cli/mf -u +49XXXXXXXXXX \
    send -m "YATS mf: Signal läuft" +49ZIELNUMMER
```
Entspricht exakt dem Aufruf in [modules/yats/tasks.py](../../modules/yats/tasks.py)
(`-u <SIGNAL_USERNAME> send -m "..." <rcpt>`).

## 4. In die Web-INI eintragen
In `/etc/yats/<site>.ini`:
```ini
[signal]
SIGNAL_BIN: sudo /usr/local/bin/signal-cli
SIGNAL_CONFIG: /var/lib/signal-cli/<site>
SIGNAL_USERNAME: +49XXXXXXXXXX
```
Danach `systemctl restart yats-tasks@<site>` — der Task-Worker versendet Signal-Nachrichten.

## Empfänger-Nummern der Nutzer
Pro Benutzer wird die Signal-Nummer im `UserProfile.signal`-Feld gepflegt
(kommagetrennt für mehrere) — siehe Django-Admin / API.

## Fehlersuche
- Versand-Fehler landen in `/tmp/signal_err` (siehe `do_send_signal`).
- `sudo signal-cli --config <CFG> -a <NUM> receive` prüft die Verbindung.
- Rate-Limit/Captcha-Fehler: neues Captcha holen und erneut `register`.
