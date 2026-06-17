# Migration der 3 Webs auf mf-yats-1 (mf / bagarino / schiwago)

Ausgangslage: altes **Python-2**-YATS auf `10.150.19.14`; DB liegt im **bestehenden
PostgreSQL-Cluster** und bleibt dort. Der neue Server nutzt **dieselbe DB-Connection** —
es werden **keine DB-Daten kopiert**, nur das Schema per `migrate` auf Django 5.2 gehoben.
Zu übernehmen sind: hochgeladene **Dateien** (liegen lokal auf dem alten Server) und die
**Signal**-Konfiguration (Nummern neu registrieren).

> Reihenfolge: erst Server aufsetzen & alles ohne DB vorbereiten (bootstrap), dann im
> Wartungsfenster den Cutover (alte App stoppen → migrate → neue App starten → mf-router umstellen).

## 0. Server aufsetzen
1. Hetzner-Server `mf-yats-1` aus `deploy/cloud-init.yaml` erstellen, an das **Private Network** hängen (Cluster + mf-router erreichbar). SSH-Key und `MF_ROUTER_IP` vorher eintragen.
2. cloud-init ruft am Ende `deploy/bootstrap.sh` auf → installiert App, venv, systemd-Units, signal-cli, legt `/etc/yats/<site>.ini` + `/var/web/<site>/…` an, `collectstatic`/`compilemessages`. Dienste sind **enabled, aber noch nicht gestartet**.

## Aus dem Altsystem ermittelt (Host `reed` = 10.150.19.14, Debian 10)
- Webs: `/var/web/sites/yats_{mf,bagarino,schiwago}/` (Apache+mod_wsgi). Modelle (`web/models.py`) bei allen 3 **identisch** → eine Codebasis trägt alle.
- DB: **PostgreSQL-Cluster `116.202.5.80:5432`** (öffentliche IP!), User `yats`, je Web eine DB: `yats_mf`, `yats_bagarino`, `yats_schiwago`.
- Mail-Relay: **`EMAIL_HOST = 10.150.20.2`** (neuer Mailserver; in den INIs bereits gesetzt).
- Signal-Nummern: mf `+494516195602`, bagarino `+494516195603`, schiwago = **eigene neue Nummer** (Altsystem nutzte fälschlich die mf-Nummer). **Alle per Voice registrieren** (Festnetz).
- Alte Upload-Pfade: `/var/web/sites/yats_<site>/files/`.
- Neue Server-IP (Hetzner Privatnetz): **`10.150.20.7`** → gunicorn-Bind + mf-router-Upstreams.

## 1. Konfiguration je Web — bereits vorbereitet
Die **fertig ausgefüllten** INIs liegen (gitignored, da DB-Passwort enthalten) unter
`deploy/etc-yats/{mf,bagarino,schiwago}.ini` — alle Werte aus dem Altsystem übernommen
(DB, Pfade→`/var/web/<site>/…`, Signal, Jabber für bagarino, API_KEY mf, `LOGIN_URL`
schiwago=`/client_intern`, `KEEP_IT_SIMPLE_DEFAULT_COMPONENT` bag=8, je-Web `TICKET_NON_PUBLIC_FIELDS`).
- Auf den Server kopieren: `scp deploy/etc-yats/<site>.ini root@mf-yats-1:/etc/yats/<site>.ini` (dann `chown root:yats`, `chmod 640`).
- `bootstrap.sh` legt sonst Templates mit `CHANGEME` an — die vorbereiteten INIs ersetzen diese.
- Verbindung testen: `PGPASSWORD=… psql -h 116.202.5.80 -p 5432 -U yats -d yats_<site> -c '\dt' | head`.

## 2. Dateien (Attachments) übernehmen
```bash
for s in mf bagarino schiwago; do
  rsync -a --info=progress2 root@10.150.19.14:/var/web/sites/yats_$s/files/ /var/web/$s/files/
done
chown -R yats:yats /var/web/{mf,bagarino,schiwago}/files
```

## 3a. Migrations-Historie prüfen (Dry-Run) — WICHTIG
Die `web`-App-Historie divergiert: Altsystem und Repo teilen `web.0001–0003`, danach haben
beide **anders benannte** Auto-Migrationen (Repo: `0004_auto_20180911`,`0005_auto_20210117`;
mf/schiwago: `0004_auto_20180904`; bagarino: `0004_auto_20180823`,`0005_auto_20180827`).
Alle Abweichungen sind **reine `AlterField`** (choices/verbose/null — keine neuen Spalten) und
das Modell ist identisch → `migrate` sollte diese als No-ops anwenden. **Vorher verifizieren:**
```bash
sudo -u yats /opt/yats/deploy/dryrun-migrate.sh mf            # READ-ONLY: zeigt migrate --plan
SCRATCH=1 sudo -u yats /opt/yats/deploy/dryrun-migrate.sh mf  # klont DB -> scratch und migriert testweise
```
Erwartung: `migrate` läuft durch, `makemigrations --check` meldet höchstens den bekannten
BigAutoField-/choices-Drift. Falls Django `InconsistentMigrationHistory` für `web` meldet:
Schema entspricht bereits dem Repo-Modell → reconcilen mit
`manage.py migrate web 0005 --fake` (markiert Repo-`web`-Migrationen als angewandt, ohne DDL),
danach normal `migrate`. Für jede der 3 Web-DBs einzeln prüfen (mf=schiwago gleich, bagarino abweichend).

## 3. Signal neu registrieren
Pro Web Nummer registrieren/verifizieren — siehe `deploy/signal/register.md`. Danach
`SIGNAL_USERNAME` in der INI eintragen.

## 4. Cutover (Wartungsfenster)
1. **DB-Backup** je Web-DB als Sicherung vor dem Schema-Upgrade:
   `pg_dump "host=<HOST> dbname=<NAME> user=<USER>" > /root/backup-<site>-$(date +%F).sql`
2. **Alte App stoppen** auf `10.150.19.14` (Apache/mod_wsgi-vhosts der 3 Webs) — verhindert Schreibzugriffe während der Migration.
3. **Schema migrieren + Index bauen + Dienste starten** auf mf-yats-1:
   ```bash
   sudo RUN_DB_STEPS=1 bash /opt/yats/deploy/bootstrap.sh
   ```
   (führt je Web `migrate` → `clear_index`/`update_index` → `systemctl restart yats-web@<site> yats-tasks@<site>` aus). Die bereits angewandten Migrationen — inkl. der `NullBooleanField→BooleanField(null=True)`-Anpassung — erzeugen **denselben DB-Spaltentyp**, daher kein Schema-Drift.
4. **Health-Check** je gunicorn:
   ```bash
   for p in 8001 8002 8003; do curl -s -o /dev/null -w "%{http_code}\n" http://10.150.20.7:$p/; done   # 302 erwartet
   ```
5. **mf-router umstellen**: `deploy/openresty/yats-upstreams.conf` als Vorlage auf mf-router anwenden (Private-IP + Ports eintragen), `nginx -t && systemctl reload openresty`. DNS bleibt unverändert (mf-router terminiert TLS).

## 5. Smoke-Test je Domain (über mf-router)
- Login (lokal), Ticketliste, Ticket anlegen.
- Anhang hochladen → ClamAV-Scan greift; Vorschau (PDF/Bild) via ImageMagick/libreoffice.
- Suche (Xapian) liefert Treffer.
- CalDAV: `/tickets/dav/<user>/` mit einem Client (Thunderbird/Apple) abonnieren; Report erscheint als Todo-Liste; VTODO abhaken → Ticket schließt.
- Signal-Testnachricht je Web (`deploy/signal/register.md`).

## 6. Rollback
Falls nötig: mf-router-Upstreams zurück auf `10.150.19.14`, alte App wieder starten,
DB aus `pg_dump`-Backup wiederherstellen (nur falls das Schema-`migrate` zurückgerollt werden muss).

## Offen / noch zu klären
- ✅ Cluster-Connection, DB-Namen, Upload-Pfade, Per-Web-Settings, neuer Mailserver (10.150.20.2), Server-IP (10.150.20.7) — **ermittelt/gesetzt** (in `deploy/etc-yats/*.ini` bzw. `openresty/yats-upstreams.conf`).
- **mf-router-IP** → in cloud-init (`MF_ROUTER_IP`) eintragen (Firewall-Freigabe der gunicorn-Ports).
- **schiwago** braucht eine **eigene Signal-Nummer** → registrieren (Voice), dann `SIGNAL_USERNAME` in `schiwago.ini` setzen (aktuell leer = Signal inaktiv).
- Mailserver `10.150.20.2` vom Privatnetz erreichbar? (Test: `nc -vz 10.150.20.2 25`).
- Voice-Registrierung: Zugang zu den Festnetz-Nummern (Anruf entgegennehmen) + Captcha.
- `SECRET_KEY` ist altbekannt/öffentlich (war im Repo) — nach dem Umzug rotieren (invalidiert nur Sessions).
