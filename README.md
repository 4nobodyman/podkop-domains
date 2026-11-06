# podkop-domains

Личные правила раздельного туннелирования для Podkop, mihomo/Clash и AmneziaVPN.

## Что править

- `domains.lst` — ручные домены, по одному на строку. Запись охватывает домен
  и все его поддомены в Podkop. Здесь уже есть `facetime.apple.com`.
- `user_subnets.lst` — ручные IPv4-подсети для JSON Amnezia. Сейчас содержит
  `17.0.0.0/8` для сервисов Apple и FaceTime. При изменении этого файла
  синхронизируйте `user_subnets` на роутере вручную: GitHub Actions роутер
  не перенастраивает.

`clash-domains.txt` и `ip-list-amnezia.json` генерируются автоматически.
Их не нужно редактировать.

## Файлы для использования

| Клиент | Файл | Как использовать |
|---|---|---|
| Podkop / sing-box | [`domains.lst`](domains.lst) | URL в `remote_domain_lists`; записи работают как `domain_suffix` |
| mihomo / Clash | [`clash-domains.txt`](clash-domains.txt) | `rule-provider` с `behavior: domain`, `format: text`; записи имеют префикс `+.` |
| AmneziaVPN | [`ip-list-amnezia.json`](ip-list-amnezia.json) | Импорт списка сайтов/IP в режиме «Только адреса из списка через VPN» |

Прямые ссылки для конфигов и загрузки:

```text
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/domains.lst
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/clash-domains.txt
https://raw.githubusercontent.com/4nobodyman/podkop-domains/main/ip-list-amnezia.json
```

Для AmneziaVPN скачайте последний URL как файл и импортируйте его в настройках
раздельного туннелирования сайтов/IP. Выберите «Заменить список», если хотите
точно этот набор правил, или «Добавить к существующему», если свои записи
должны сохраниться. После импорта переподключите VPN.
[Официальная инструкция AmneziaVPN](https://docs.amnezia.org/documentation/instructions/vpn-split-tunneling/).

## Откуда берётся JSON Amnezia

Сборка объединяет те же категории, что были включены на роутере 6 ноября
2026 года:

1. `russia_inside` — домены из
   [`Russia/inside-raw.lst`](https://github.com/itdoginfo/allow-domains/blob/main/Russia/inside-raw.lst).
2. `telegram` — [домены](https://github.com/itdoginfo/allow-domains/blob/main/Services/telegram.lst)
   и [IPv4-подсети](https://github.com/itdoginfo/allow-domains/blob/main/Subnets/IPv4/telegram.lst).
3. `google_ai` — [домены](https://github.com/itdoginfo/allow-domains/blob/main/Services/google_ai.lst).
4. Ручные `domains.lst` и `user_subnets.lst` из этого репозитория.

GitHub Action `build routing lists` запускается ежедневно примерно в 06:17
по Москве, при изменении ручных исходников и вручную через Actions → Run
workflow. При изменении содержимого он коммитит оба готовых файла в `main`.
Если внешний список недоступен или пуст, сборка падает и оставляет последний
готовый JSON без изменений. Списки на роутере и JSON не обновляются атомарно;
для нового ручного правила меняйте соответствующий файл здесь и настройку
роутера, если она применяется там отдельно.

## Ограничения AmneziaVPN

JSON содержит CIDR-подсети и доменные имена. Podkop умеет сопоставлять
`domain_suffix` и все поддомены; AmneziaVPN может обрабатывать импортированные
имена иначе. Запись `.ua` из `russia_inside` пропускается, потому что это
суффикс зоны, а не импортируемый адрес сайта. Поэтому JSON не является точной
копией поведения Podkop.

Для macOS есть [отчёт о проблеме](https://github.com/amnezia-vpn/amnezia-client/issues/3240):
в некоторых версиях импорт доменов с пустым `ip` не создаёт маршруты,
тогда как CIDR-записи работают. Проверяйте нужные сайты и FaceTime после
импорта; работа видеозвонка зависит также от сети и разрешённых UDP-портов.

## Локальная сборка и проверка

```bash
python3 scripts/build.py
python3 scripts/build_amnezia.py
```

`build.py` отклоняет wildcard, IP-адреса и поглощённые домены в
`domains.lst`: например, `playstation.com` уже покрывает
`store.playstation.com`. Разные зоны, такие как `notebooklm.google` и
`notebooklm.google.com`, независимы. `build_amnezia.py` проверяет
корректность подсетей и наличие правил FaceTime, удаляет повторы и выдаёт
JSON с полями `hostname` и `ip`.
