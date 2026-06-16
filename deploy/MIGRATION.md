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

## 1. Konfiguration je Web vervollständigen
In `/etc/yats/<site>.ini` (owner `root:yats`, mode 640):
- `[database]` `DATABASE_NAME/USER/PASSWORD/HOST/PORT` = **die bestehende Cluster-Connection** der jeweiligen Web (aus der alten Konfiguration auf `10.150.19.14` übernehmen — dort `settings`/alte ini der py2-Instanz prüfen).
- `[signal] SIGNAL_USERNAME` = registrierte Nummer (siehe Schritt 3).
- Verbindung testen: `psql "host=<HOST> port=<PORT> dbname=<NAME> user=<USER>"`.

## 2. Dateien (Attachments) übernehmen
Alte `FILE_UPLOAD_PATH` je Web auf `10.150.19.14` feststellen (alte settings/ini), dann je Web:
```bash
rsync -a --info=progress2 root@10.150.19.14:<ALTER_FILE_UPLOAD_PATH>/ /var/web/<site>/files/
chown -R yats:yats /var/web/<site>/files
```

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
   for p in 8001 8002 8003; do curl -s -o /dev/null -w "%{http_code}\n" http://<PRIVATE_IP>:$p/; done   # 302 erwartet
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

## Offene Werte (vor dem Cutover beschaffen)
- Cluster-Connection je Web-DB (Host/Port/DB/User/Passwort) — aus alter py2-Konfiguration.
- Alte `FILE_UPLOAD_PATH` je Web (für rsync).
- Private IP von mf-yats-1 + mf-router-IP.
- 3 Signal-Nummern + SMS/Captcha-Zugang.
