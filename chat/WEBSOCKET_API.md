# WebSocket API: аккаунты и чаты

Документ описывает WebSocket-маршруты приложения `chat`.

> Отдельного WebSocket API аккаунта (профиль, presence/online, уведомления аккаунта) в текущем коде нет. `/ws/chats/` — персональный поток событий чатов авторизованного пользователя, а не общий канал аккаунта. Список чатов и их начальное состояние нужно получать через HTTP API.

## HTTP API

Корневые префиксы заданы в `project/urls.py`: API аккаунта — `/account/api/`, API чатов — `/chat/api/`. API принимает JSON, если для загрузки файла отдельно не указано `multipart/form-data`.

### Заголовки и авторизация

Для REST API передавайте секрет приложения:

```http
Dark-Talk-Secret-Key: <application-secret>--<application>|<version>
```

Проверяется часть до `--`. Суффикс `--<application>|<version>` необязателен; если он передан, укажите приложение и версию через `|`. Без суффикса используется `unofficial|0.0.0`. Значения записываются на устройство при регистрации и входе. Для запросов от имени пользователя передавайте также:

```http
Authorization: Token <device-token>
```

Регистрация и вход создают токен, поэтому для них нужен секрет приложения, но не существующий токен. Для остальных account и chat API используйте токен аккаунта. HTTP API чатов принимает только токенную аутентификацию.

### API аккаунта

| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/account/api/auth/register/` | Создать аккаунт, устройство и токен |
| `POST` | `/account/api/auth/login/` | Войти или начать 2FA challenge |
| `GET`, `PATCH` | `/account/api/2fa/` | Прочитать или изменить настройку 2FA |
| `POST` | `/account/api/auth/2fa/verify/` | Проверить код 2FA и завершить вход |
| `POST` | `/account/api/auth/2fa/resend/` | Выпустить новый код для challenge |
| `POST` | `/account/api/auth/logout/` | Отозвать токен устройства |
| `GET`, `PATCH` | `/account/api/profile/` | Получить или изменить профиль текущего пользователя |
| `GET` | `/account/api/users/search/?username={query}` | Найти активные аккаунты по username |
| `GET` | `/account/api/login-history/` | Получить историю входов |
| `GET` | `/account/api/devices/` | Получить устройства текущего пользователя |
| `GET`, `PATCH`, `DELETE` | `/account/api/devices/{device_id}/` | Получить, изменить или удалить устройство |

#### Регистрация

`POST /account/api/auth/register/`

```json
{
  "email": "user@example.com",
  "password": "secret-password",
  "username": "user",
  "language": "Russian",
  "date_of_birth": "2000-01-31",
  "device_id": "optional-client-device-id"
}
```

Обязательны `email` и `password`. `username` по умолчанию берётся из части email до `@`; `language` по умолчанию `Russian`, допустимые значения `Russian` и `English`. `date_of_birth` и `device_id` необязательны. Информация об устройстве также определяется по заголовкам запроса.

Ответ `201`:

```json
{
  "status": "success",
  "token": "<device-token>",
  "user": {"id": 7, "username": "user"},
  "device": {"id": "<uuid>", "device_id": "<client-or-generated-id>"}
}
```

В примере `user` и `device` показаны сокращённо; полный состав полей определяется `DarkAccountSerializer` и `DeviceSerializer`. Возможные ошибки `400`: `EMAIL_PASSWORD_NOT_PROVIDED`, `LANGUAGE_NOT_SUPPORTED`.

#### Вход и выход

`POST /account/api/auth/login/` принимает:

```json
{"username":"user","password":"secret-password","device_id":"optional-client-device-id"}
```

Обязательны `username` и `password`; `device_id` необязателен. Если 2FA выключена, ответ `200` содержит `status`, `token`, `user` и `device`. Если 2FA включена, сервер отправляет шестизначный код на почту и отвечает `202` без токена:

```json
{
  "status": "two_factor_required",
  "challenge_id": "<uuid>",
  "expires_at": "2026-09-28T12:10:00Z"
}
```

Код и challenge действуют 10 минут. Ошибки: `400 USERNAME_PASSWORD_NOT_PROVIDED`, `400 TWO_FACTOR_EMAIL_NOT_CONFIGURED`, `401 INVALID_CREDENTIALS`, `403` с `detail`, если устройство заблокировано. Password login, verify и resend ограничены десятью запросами в минуту на IP; при превышении DRF возвращает `429`.

`POST /account/api/auth/2fa/verify/` принимает `{"challenge_id":"<uuid>","code":"123456"}`. Необязательный `device_id` можно передать, чтобы привязать токен к идентификатору устройства. При успешной проверке ответ `200` содержит `status`, `token`, `user` и `device`; challenge становится одноразовым. Неверный, просроченный или уже использованный код даёт `400 INVALID_OR_EXPIRED_TWO_FACTOR_CODE`; отсутствующие поля — `400 CHALLENGE_CODE_NOT_PROVIDED`; некорректный `device_id` — `400 INVALID_DEVICE_ID`.

`POST /account/api/auth/2fa/resend/` принимает `{"challenge_id":"<uuid>"}`. Предыдущий challenge становится недействительным, сервер отправляет новый код и возвращает `200` с новым `challenge_id` и `expires_at`. Недействительный или истёкший challenge даёт `400 INVALID_OR_EXPIRED_TWO_FACTOR_CHALLENGE`.

`GET /account/api/2fa/` требует действующий токен и возвращает текущее состояние в `two_factor_enabled`. `PATCH /account/api/2fa/` принимает `{"enabled":true}` или `{"enabled":false}` и возвращает обновлённое состояние. Включение требует email; неверный тип `enabled` даёт `400 INVALID_TWO_FACTOR_ENABLED`, отсутствующий email — `400 TWO_FACTOR_EMAIL_NOT_CONFIGURED`. При фактическом изменении настройки все незавершённые коды аккаунта отзываются. Изменение настройки требует аутентифицированного токена и секрета приложения.

`POST /account/api/auth/logout/` принимает `{"device_id":"<client-device-id>"}`. При отсутствии ID возвращает `400 DEVICE_ID_NOT_PROVIDED`. Удаляет токен устройства и обновляет `last_online`; ответ — `204 No Content`.

#### Профиль, история входов и устройства

- `GET /account/api/profile/` возвращает `{"status":"success","user":{...}}` для текущего токена.
- `PATCH /account/api/profile/` частично обновляет профиль текущего пользователя. Допустимые поля: `username`, `avatar` (multipart-файл), `avatar_access` (`all`, `authenticated` или `nobody`), `info`, `date_of_birth` (формат `YYYY-MM-DD` или `null`) и `language` (`Russian` или `English`). Пример JSON: `{"username":"new-name","info":"О себе","language":"English"}`. Ответ содержит обновлённый `user` в формате `DarkAccountSerializer`. Неподдерживаемые поля, включая `email` и `password`, и значения с неверным форматом дают `400`.
- `GET /account/api/users/search/?username={query}` ищет активные аккаунты по частичному совпадению username без учёта регистра; возвращает не более 20 результатов в алфавитном порядке: `{"status":"success","users":[{"id":7,"username":"user","avatar":"/media/..."}]}`. Email и другие приватные данные не выдаются. `avatar` будет `null`, если владелец запретил его показ (`avatar_access: nobody`) или аватар не задан. Пустой параметр `username` даёт `400 USERNAME_NOT_PROVIDED`.
- `GET /account/api/login-history/` возвращает `{"status":"success","login_history":[...]}`. Элемент содержит ID записи, устройство и его имя, IP, страну, город, статус, причину и время.
- `GET /account/api/devices/` возвращает `{"status":"success","devices":[...]}`. Список ограничен устройствами текущего пользователя.
- `GET /account/api/devices/{device_id}/` возвращает `{"status":"success","device":{...}}`; неизвестный ID даёт `404 DEVICE_NOT_FOUND`.
- `PATCH /account/api/devices/{device_id}/` принимает любые из полей `name` и `trusted`, например `{"name":"Рабочий ноутбук","trusted":true}`. Возвращает обновлённый объект `device`; ошибки сериализатора имеют статус `400`.
- `DELETE /account/api/devices/{device_id}/` задуман для удаления устройства с ответом `204`, но текущая реализация вызывает `Device.objects.delete(...)` вместо удаления найденной записи и, вероятно, завершится `500`. Кроме того, `GET` и `PATCH` ищут устройство только по `device_id`, не проверяя владельца. До исправления не используйте эти два метода с недоверенным ID.

Устройство сериализуется полями `id`, `user`, `device_id`, `name`, `device_type`, ОС/браузера/приложения, IP и геоданными, `trusted`, `blocked`, `created_at`, `last_seen`. Профиль включает поля сериализатора аккаунта: `id`, `username`, `email`, `avatar`, `info`, `date_of_birth`, `language`, `is_online`, `last_online`, `email_confirmed`, `two_factor_enabled`, `date_joined`.

### API чатов

| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/chat/api/chats/create/` | Создать личный или групповой чат |
| `GET` | `/chat/api/chats/` | Список чатов и число непрочитанных сообщений |
| `GET`, `PATCH`, `DELETE` | `/chat/api/chats/{chat_id}/` | Прочитать, изменить или удалить чат |
| `GET` | `/chat/api/chats/{chat_id}/messages/` | История сообщений с пагинацией |
| `POST` | `/chat/api/chats/{chat_id}/read/` | Отметить входящие сообщения чата прочитанными |
| `POST` | `/chat/api/chats/{chat_id}/participants/` | Добавить участников |
| `PATCH`, `DELETE` | `/chat/api/chats/{chat_id}/participants/{user_id}/` | Изменить участника или удалить его из чата |
| `POST` | `/chat/api/messages/create/` | Создать сообщение, в том числе с вложением |
| `PATCH`, `DELETE` | `/chat/api/messages/{message_id}/` | Изменить или удалить сообщение |
| `POST` | `/chat/api/messages/read/{message_id}/` | Отметить отдельное сообщение прочитанным |
| `POST`, `DELETE` | `/chat/api/messages/reaction/{message_id}/` | Добавить или удалить свою реакцию |

Доступ к чатам, сообщениям и участникам проверяется по членству пользователя. Для операций управления участниками и чатом требуются соответствующие роли; ограничения перечислены у операций ниже.

#### Чаты

`POST /chat/api/chats/create/` принимает `chat_type` со значением `direct` или `group`.

Для личного чата передайте `{"chat_type":"direct","participant_name":"username"}`. Нельзя создать чат с самим собой (`400 CANNOT_CREATE_CHAT_WITH_SELF`); без имени вернётся `400 PARTICIPANT_NAME_NOT_PROVIDED`. Успешный ответ содержит `chat_id`; статус `201` для нового чата и `200`, если личный чат уже существует.

Для группы передайте `{"chat_type":"group","participant_names":"alice,bob","title":"Название","description":"Описание"}`. `participant_names` — строка имён, разделённых запятыми, и обязательное поле. `title` необязателен; при отсутствии создаётся название по умолчанию. Файл `avatar` передаётся multipart-запросом. Ответ `201` содержит `chat_id`.

`GET /chat/api/chats/` возвращает `{"chats":[...]}`. Каждый элемент включает `id`, `chat_type`, `title`, описание и аватар, создателя, даты, `unread_count` и список участников с ролью и `is_muted`.

`GET /chat/api/chats/{chat_id}/` возвращает сведения о чате и участников. В личном чате `title`, `description`, `avatar`, `created_by` равны `null`.

`PATCH /chat/api/chats/{chat_id}/` доступен владельцу или администратору. Необязательные поля: `new_participants` и `del_participants` (имена через запятую), `new_title`, `new_description`, `new_avatar` (multipart) и `new_role` в формате `username:admin` или `username:member`. Ответ: `{"status":"success","chat_id":...}`. `DELETE` доступен владельцу или администратору; успешный ответ — `204`, недостаточные права дают `403 INSUFFICIENT_ACCOUNT_PERMISSIONS`.

#### Сообщения и чтение

`GET /chat/api/chats/{chat_id}/messages/?limit=50&before_id=124` возвращает страницу сообщений в хронологическом порядке: `messages`, `has_more`, `next_before_id`, `chat_id` и `status`. `limit` по умолчанию `50` и ограничен диапазоном `1–100`; `before_id` необязателен. Некорректные параметры дают `400 INVALID_PAGINATION`.

`POST /chat/api/messages/create/` принимает JSON с `chat_id`, `text`, `message_type`, `reply_to`, `metadata`, `client_message_id`. Для вложений используйте multipart-поле `attachment`; сервер заполняет имя и размер файла. `message_type` должен быть одним из `text`, `voice_message`, `image`, `file`, `system`. `chat_id` обязателен; `reply_to` должен указывать на сообщение этого чата. Успех — `201` с `chat_id` и `message_id`. Создание публикует `message_created` в WebSocket-потоки участников.

`PATCH /chat/api/messages/{message_id}/` принимает `{"text":"Новый текст"}`. Изменять можно только своё неудалённое сообщение; успех возвращает объект `message`, попытка изменить чужое сообщение — `403`.

`DELETE /chat/api/messages/{message_id}/` удаляет сообщение логически: текст очищается, запись сохраняется. Автор может удалить своё сообщение; владелец или администратор также может удалить чужое. Ответ `200` содержит `message_id`.

`POST /chat/api/messages/read/{message_id}/` отмечает одно сообщение прочитанным и возвращает `message_id` и `read_at`. `POST /chat/api/chats/{chat_id}/read/` отмечает все входящие сообщения чата прочитанными; необязательное поле `last_message_id` ограничивает обработку этим сообщением. Ответ содержит `chat_id` и `last_read_message_id`.

#### Реакции и участники

`POST /chat/api/messages/reaction/{message_id}/` принимает `{"emoji":"❤️"}`; если emoji не передан, используется `🔥`. Успех возвращает `message_reaction` с ID, `user_id`, emoji и временем. Пустая строка, нестроковое значение или длина больше 32 дают `400 INVALID_EMOJI`. Пользователь может иметь несколько разных реакций на одно сообщение, но одинаковая реакция не дублируется.

`DELETE /chat/api/messages/reaction/{message_id}/` принимает emoji в JSON или query-параметре. Если параметр не передан, ответ `400 EMOJI_NOT_PROVIDED`; если своей реакции нет, `404 REACTION_NOT_FOUND`; иначе `200`.

`POST /chat/api/chats/{chat_id}/participants/` доступен владельцу и администратору. Принимает `{"usernames":["alice","bob"]}` или строку `{"usernames":"alice,bob"}` (также поддерживается ключ `username`). Ответ содержит список фактически добавленных имён в `added`.

`PATCH /chat/api/chats/{chat_id}/participants/{user_id}/` принимает одно или оба поля: `role` (`admin` или `member`) и `is_muted` (boolean). Менять роли может только владелец; администратор может менять `is_muted`. Ответ возвращает `user_id`, `role` и `is_muted`.

`DELETE /chat/api/chats/{chat_id}/participants/{user_id}/` позволяет участнику покинуть чат, кроме владельца; владелец не может быть удалён. Администратор или владелец может удалить другого участника, но не владельца. Успех — `200 {"status":"success"}`.

### Account-маршруты страниц

Следующие URL из `account/urls.py` обслуживают HTML-страницы и формы, а не JSON API:

| Методы | Путь | Назначение |
| --- | --- | --- |
| `GET`, `POST` | `/account/register/` | Регистрация |
| `GET`, `POST` | `/account/login/` | Вход |
| `GET`, `POST` | `/account/login/verify/` | Проверка 2FA-кода |
| `POST` | `/account/login/verify/resend/` | Повторная отправка 2FA-кода |
| `POST` | `/account/login/verify/cancel/` | Отмена входа с 2FA |
| `GET`, `POST` | `/account/logout/` | Подтверждение и выполнение выхода |
| `GET`, `POST` | `/account/`, `/account/profile/` | Просмотр и изменение профиля |
| `GET` | `/account/profile/security/` | Настройки безопасности |
| `POST` | `/account/profile/security/2fa/` | Переключение 2FA |
| `GET` | `/account/profile/devices/` | Страница устройств |
| `POST` | `/account/profile/devices/{uuid}/trust/` | Переключить доверие устройства |
| `POST` | `/account/profile/devices/{uuid}/block/` | Переключить блокировку устройства |
| `POST` | `/account/profile/devices/{uuid}/delete/` | Удалить устройство |
| `GET` | `/account/profile/login-history/` | Страница истории входов |
| `GET`, `POST` | `/account/email/confirm/` | Отправка и ввод кода подтверждения почты |
| `POST` | `/account/email/confirm/resend/` | Повторная отправка кода подтверждения |
| `GET`, `POST` | `/account/password-reset/` | Запрос сброса пароля |
| `GET`, `POST` | `/account/password-reset/confirm/` | Подтверждение кода и смена пароля |

Большинство изменяющих операций этих страниц требуют входа и CSRF-токен; они используют Django-сессию и перенаправления, в отличие от JSON API.

## Подключение

Все соединения используют JSON-сообщения и доступны по протоколу `ws://` локально или `wss://` за HTTPS-прокси.

| Назначение | Путь |
| --- | --- |
| События чатов текущего пользователя | `/ws/chats/` |
| События отдельного чата | `/ws/chat/{chat_id}/` |

`chat_id` — числовой ID чата. Подключение к нему разрешено только активному участнику: запись участника должна существовать и иметь `left_at = null`.

### Авторизация

Поддерживаются два варианта:

1. **Django-сессия.** Передайте cookie авторизованной сессии; соединение использует `AuthMiddlewareStack`.
2. **Токен устройства.** Передайте оба заголовка:

```http
Authorization: Token <device-token>
Dark-Talk-Secret-Key: <application-secret>--<version>
```

Суффикс `--<version>` необязателен для проверки WebSocket: сервер сравнивает с `DARK_TALK_SECRET_KEY` часть до `--`. Токен должен принадлежать незаблокированному устройству активного аккаунта. При токенной авторизации секрет приложения обязателен.

WebSocket-маршруты защищены проверкой Origin по `ALLOWED_HOSTS` Django.

### Успешное подключение

Сервер сразу отправляет одно JSON-сообщение:

```json
{"type":"connection_ready","scope":"chats"}
```

Для конкретного чата ответ содержит его ID:

```json
{"type":"connection_ready","chat_id":42}
```

### Отклонение подключения

| Close code | Значение |
| --- | --- |
| `4001` | Не пройдена аутентификация или проверка секрета приложения |
| `4003` | Пользователь не является активным участником чата |

## Поток `/ws/chats/`

Поток подписан на события чатов текущего пользователя. Он не принимает команды клиента: отправка JSON в этот сокет не обрабатывается. События поступают, пока пользователь является активным участником соответствующих чатов.

В этом потоке публикуются события `chat_created`, `message_created`, `message_updated`, `message_deleted` и `message_read` из участвующих чатов. Событие `typing` в этот поток не отправляется.

При создании нового чата каждый его участник получает `chat_created` с данными чата и его участниками. Повторный запрос, вернувший уже существующий direct-чат, это событие не создаёт.

```json
{
  "type": "chat_created",
  "chat_id": 42,
  "chat": {
    "id": 42,
    "chat_type": "direct",
    "title": null,
    "description": "",
    "avatar": null,
    "created_by": {"id": 7, "username": "user"},
    "created_at": "2026-10-02T12:00:00Z",
    "updated_at": "2026-10-02T12:00:00Z",
    "participants": [
      {"user": {"id": 7, "username": "user"}, "role": "owner", "is_muted": false},
      {"user": {"id": 8, "username": "peer"}, "role": "member", "is_muted": false}
    ]
  }
}
```

При подключении список чатов и история сообщений не отправляются. Получите их через HTTP API, например `GET /chat/api/chats/` и `GET /chat/api/chats/{chat_id}/messages/`.

## Поток `/ws/chat/{chat_id}/`

Команды передаются JSON-объектами с полем `type`.

### `send_message`

Создаёт текстовое сообщение. Непустой текст обязателен. Ответное сообщение, если задано, должно принадлежать этому же чату.

```json
{
  "type": "send_message",
  "text": "Привет!",
  "reply_to": 123,
  "client_message_id": "local-001"
}
```

`reply_to` и `client_message_id` необязательны. Допускается только `message_type: "text"`; файлы и остальные типы сообщений отправляйте через HTTP API.

Участники чата получают событие `message_created`:

```json
{
  "type": "message_created",
  "chat_id": 42,
  "message": {
    "id": 124,
    "chat_id": 42,
    "sender": {"id": 7, "username": "user"},
    "reply_to": 123,
    "message_type": "text",
    "text": "Привет!",
    "attachment": null,
    "attachment_name": "",
    "attachment_size": null,
    "metadata": {},
    "is_edited": false,
    "is_deleted": false,
    "created_at": "2026-09-28T12:00:00Z",
    "updated_at": "2026-09-28T12:00:00Z",
    "reactions": [],
    "read_by": []
  },
  "client_message_id": "local-001"
}
```

`sender` сериализован через `DarkAccountSerializer`; его полный набор полей определяется этим сериализатором. `client_message_id` возвращается без изменений и может отсутствовать.

### `typing`

Передаёт состояние набора текста всем подключениям конкретного чата:

```json
{"type":"typing","is_typing":true}
```

Серверное событие содержит ID чата и пользователя:

```json
{"type":"typing","chat_id":42,"user_id":7,"is_typing":true}
```

Если `is_typing` не равен JSON `true`, сервер публикует `false`. Событие не сохраняется и не попадает в поток `/ws/chats/`.

### `read_message`

Отмечает сообщение прочитанным текущим пользователем и обновляет курсор прочтения участника, если переданное сообщение новее текущего.

```json
{"type":"read_message","message_id":124}
```

В ответ все участники получают:

```json
{
  "type":"message_read",
  "chat_id":42,
  "message_id":124,
  "user_id":7,
  "read_at":"2026-09-28T12:01:00+00:00"
}
```

### `edit_message`

Редактирует только собственное неудалённое сообщение в текущем чате. Текст должен быть непустой строкой.

```json
{"type":"edit_message","message_id":124,"text":"Исправленный текст"}
```

Участники чата и подписчики `/ws/chats/` получают `message_updated` с полями `chat_id` и обновлённым объектом `message` (формат объекта — как в `message_created`).

### `delete_message`

Удаляет только собственное неудалённое сообщение в текущем чате. Удаление логическое: запись остаётся, текст очищается.

```json
{"type":"delete_message","message_id":124}
```

Участники чата и подписчики `/ws/chats/` получают:

```json
{"type":"message_deleted","chat_id":42,"message_id":124}
```

## Ошибки команд

Ошибки отправляются JSON-сообщениями вида `{"type":"error","code":"..."}`; поле `message` добавляется для некоторых ошибок.

| Код | Причина |
| --- | --- |
| `invalid_payload` | Получено сообщение, которое не является JSON-объектом |
| `unknown_event` | Неизвестное значение `type` |
| `empty_text` | Для `send_message` передан пустой или нестроковый текст |
| `unsupported_message_type` | Запрошен тип сообщения, отличный от `text`; вложения нужно отправлять через HTTP API |
| `invalid_reply` | `reply_to` не является ID сообщения этого чата |
| `invalid_message` | Сообщение для `read_message` не найдено в текущем чате |
| `edit_forbidden` | Сообщение нельзя отредактировать: неверный ID, оно чужое/удалено или текст пустой |
| `delete_forbidden` | Сообщение нельзя удалить: неверный ID, оно чужое или уже удалено |

Проверка членства выполняется и для каждой входящей команды. Если пользователь перестал быть активным участником, соединение закрывается с кодом `4003`.

## Доставка событий и HTTP API

Создание чата через `POST /chat/api/chats/create/` публикует `chat_created`, а создание сообщения через `POST /chat/api/messages/create/` публикует `message_created` в сокеты чата и пользовательские потоки участников после фиксации транзакции. Изменения и реакции через HTTP API не гарантируют соответствующих WebSocket-событий.

Команды `edit_message` и `delete_message` через WebSocket разрешены только автору сообщения. HTTP API для удаления имеет отдельное правило: администратор или владелец чата может удалить сообщение другого участника.
