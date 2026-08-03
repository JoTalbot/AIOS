# Доступ к AIOS CRM

CRM Dashboard v3 публикуется через защищённый HTTPS-префикс:

```text
https://api.autosklo.org.ua/crm/
```

Доступ защищён HTTP Basic Auth. Учётные данные хранятся только в
`/etc/nginx/.htpasswd_aios_crm` с ограниченными правами и не включаются в Git.

Дашборд остаётся привязанным к `127.0.0.1:8090`; наружу он доступен только через
Nginx с Basic Auth. Для изменения пароля:

```bash
PASSWORD='<новый пароль>'
printf 'crm:%s\n' "$(openssl passwd -6 "$PASSWORD")" > /etc/nginx/.htpasswd_aios_crm
chmod 640 /etc/nginx/.htpasswd_aios_crm
chown root:www-data /etc/nginx/.htpasswd_aios_crm
systemctl reload nginx
```
