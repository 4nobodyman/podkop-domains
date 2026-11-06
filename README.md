# podkop-domains

Личный список доменов для раздельного туннелирования. Один источник правды на
две системы с разной семантикой суффиксов.

## Как пользоваться

Для доменов правится **только `domains.lst`** — голые домены, по одному на строку, `#` для
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

## AmneziaVPN: ежедневный JSON

`ip-list-amnezia.json` — файл для импорта в режим «Только адреса из списка через VPN».
GitHub Actions обновляет его ежедневно в 06:17 по Москве и при изменении
`domains.lst` или `user_subnets.lst`. Сборка объединяет действующие источники
Podkop: `russia_inside`, `telegram` (домены и IPv4-подсети), `google_ai`,
ручной `domains.lst` и ручной `user_subnets.lst` (включая `17.0.0.0/8`
для FaceTime). Правьте только эти два ручных исходных файла; JSON генерируется.

Скачать готовый файл:

```
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/ip-list-amnezia.json
```

Запуск вручную: Actions → `build routing lists` → Run workflow.
Для локальной сборки: `python3 scripts/build_amnezia.py`.

Формат Amnezia хранит домены как отдельные записи, но не воспроизводит
семантику `domain_suffix` Podkop и не обновляет IP-адреса при изменении DNS.
На macOS есть [отчёт о проблеме с маршрутами для доменных записей](https://github.com/amnezia-vpn/amnezia-client/issues/3240);
CIDR-записи работают независимо от этой особенности.
