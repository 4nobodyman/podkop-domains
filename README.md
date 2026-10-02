# podkop-domains

Личный список доменов для раздельного туннелирования. Один источник правды на
две системы с разной семантикой суффиксов.

## Как пользоваться

Правится **только `domains.lst`** — голые домены, по одному на строку, `#` для
комментариев. Каждая запись трактуется как суффикс: домен и все его поддомены.

После пуша GitHub Action пересобирает `clash-domains.txt`. Руками его не трогать.

## Почему два файла

| Система | Файл | Формат |
|---|---|---|
| Podkop / sing-box (`remote_domain_lists`) | `domains.lst` | `healthchecks.io` — уже `domain_suffix`, поддомены покрыты |
| mihomo / Clash (`rule-providers`, `behavior: domain`, `format: text`) | `clash-domains.txt` | `+.healthchecks.io` — голый домен здесь означал бы только точное совпадение |

## Ссылки для конфигов

Podkop, `remote_domain_lists`:

```
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/domains.lst
```

mihomo, `rule-providers.my_domains.url`:

```
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/clash-domains.txt
```

## Локальная проверка

```bash
python3 scripts/build.py
```

Скрипт падает с ненулевым кодом, если в `domains.lst` попали wildcard-префиксы,
IP-адреса или подсети — подсети задаются в подкоп отдельной настройкой
`user_subnets`, не здесь.

Он также отклоняет **поглощённые домены**: запись суффиксная, поэтому
`playstation.com` уже покрывает `store.playstation.com`, и держать обе строки
незачем. Такая проверка не даёт списку обрасти мёртвыми записями, про которые
потом непонятно, нужны они ещё или нет.

Разные зоны поглощением не считаются: `notebooklm.google` и
`notebooklm.google.com` — две независимые записи, обе нужны.
