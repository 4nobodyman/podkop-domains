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

Сборка объединяет категории, включённые на роутере 6 ноября 2026 года,
и дополнительные IP-диапазоны для воспроизведения медиа на iPhone:

1. `russia_inside` — домены из
   [`Russia/inside-raw.lst`](https://github.com/itdoginfo/allow-domains/blob/main/Russia/inside-raw.lst).
2. `telegram` — [домены](https://github.com/itdoginfo/allow-domains/blob/main/Services/telegram.lst)
   и [IPv4-подсети](https://github.com/itdoginfo/allow-domains/blob/main/Subnets/IPv4/telegram.lst).
3. `google_ai` — [домены](https://github.com/itdoginfo/allow-domains/blob/main/Services/google_ai.lst).
4. Ручные `domains.lst` и `user_subnets.lst` из этого репозитория.
5. [IPv4-диапазоны Meta](https://github.com/itdoginfo/allow-domains/blob/main/Subnets/IPv4/meta.lst)
   для медиа Instagram.
6. [Диапазоны Google](https://www.gstatic.com/ipranges/goog.json) за вычетом
   [Google Cloud](https://www.gstatic.com/ipranges/cloud.json) для видео YouTube.
   Вычитание соответствует [рекомендации Google](https://knowledge.workspace.google.com/admin/security/obtain-google-ip-address-ranges).
7. [IPv4-диапазон Anthropic `160.79.104.0/23`](https://platform.claude.com/docs/en/api/ip-addresses),
   проверенный на iPhone для Claude.

Пункты 5–7 добавлены для Amnezia после проверки на iPhone: одних IP
корневых доменов не хватало для видео YouTube и загрузки Instagram. Они
направляют через VPN и другой трафик к адресам Google и Meta. Настройки
Podkop на роутере при этом не меняются.

GitHub Action `build routing lists` запускается ежедневно примерно в 06:17
по Москве, при изменении ручных исходников и вручную через Actions → Run
workflow. При изменении содержимого он коммитит оба готовых файла в `main`.
Если внешний список недоступен, пуст или разрешилось менее 80% доменов,
сборка падает и оставляет последний готовый JSON без изменений. Списки на роутере и JSON не обновляются атомарно;
для нового ручного правила меняйте соответствующий файл здесь и настройку
роутера, если она применяется там отдельно.

## Как устроен импорт AmneziaVPN на iPhone

Генератор запрашивает IPv4-адреса каждого домена и его `www`-варианта
через Google DNS-over-HTTPS. В JSON у доменной записи заполнены `ips` и
`ip`. AmneziaVPN использует эти адреса для маршрутов; одно имя с пустым
`ip` не даёт надёжного результата. Адреса из непубличных сетей
(например, подставные `198.18.0.0/15`) отклоняются.

Для CIDR генератор хранит саму подсеть в `ips` и `ip`, а в
`hostname` помещает уникальное имя с зоной `.invalid`. Это обход
[ошибки импорта CIDR на iOS](https://github.com/amnezia-vpn/amnezia-client/issues/2939):
в затронутой версии AmneziaVPN маска, записанная в `hostname`, теряется.
Имя `.invalid` не используется как адрес назначения.

Импортируйте файл в режиме «Только адреса из списка через VPN»,
выбрав **«Заменить список»**, затем переподключите VPN. Обновление JSON
в GitHub **не обновляет список на iPhone автоматически**: после нужного
обновления скачайте файл и импортируйте его снова.

## Ограничения AmneziaVPN

Podkop сопоставляет доменные суффиксы и все поддомены, а JSON Amnezia
хранит снимок IP-адресов основного домена и `www`. Для YouTube и Instagram
добавлены сетевые диапазоны Google и Meta; другие поддомены и новые
CDN-адреса всё ещё могут потребовать отдельной записи или нового импорта. Если DNS не вернул публичный IPv4-адрес, домен
пропускается; список пропусков выводится в лог сборки. При временном
сбое DNS генератор сохраняет ранее полученные публичные IP из
предыдущего JSON. Запись `.ua` из `russia_inside` пропускается,
поскольку это суффикс всей зоны, который нельзя однозначно разрешить
в набор IP-адресов.

Поэтому JSON приближает, но не полностью повторяет правила Podkop.
На iOS раздельное туннелирование Amnezia поддерживает только IPv4;
приложения, использующие несколько динамических адресов или IPv6, могут
не работать с таким списком. В частности, добавление отдельных известных
адресов ChatGPT не обеспечило работу его iOS-приложения на мобильной сети.
Для таких приложений используйте полный VPN.
FaceTime дополнительно покрыт подсетью Apple `17.0.0.0/8`; работу
видеозвонка проверяйте на устройстве.

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
JSON с полями `hostname`, `ips` и `ip`.
