# Источники и основания выпуска KEREK 3.4

Проверка исходного состояния через подключённый GitHub: `Marklanskoy/KEREK-PLUS-`, ветка main, commit `161d5b6872ea8febed75f26f54ee6cacb1fcdab6`, release.json 3.3.0. Локальная исходная сборка побайтово проверена по всем полям files manifest. Исходники получены из ранее предоставленного в этом разговоре Source.zip и изменены в рабочем контейнере. Прав на push в соединении нет.

Первичные технические источники, просмотренные при подготовке (13 октября 2026):

- MDN Web Locks: https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API
- MDN Request.integrity: https://developer.mozilla.org/en-US/docs/Web/API/Request/integrity
- MDN Using Service Workers: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers
- MDN Cache: https://developer.mozilla.org/en-US/docs/Web/API/Cache
- Playwright Service Workers: https://playwright.dev/python/docs/service-workers

Выпуск использует собственную проверку SHA-256 содержимого. Документация integrity не выдаётся за автоматическую проверку её реализации. Контрольные суммы не заменяют доверенную подпись.

Результаты тестов — только реально выполненные команды из TEST_REPORT.md. Скриншоты и UI-тесты используют явные модели хранилища/блокировок, отключённые фотографии и тестовые данные. Они не являются источником утверждений о работе реального магазина или состоянии личной базы пользователя.

В KEREK используются текущие демонстрационные товарные сведения и изображения-иллюстрации прежнего проекта; это не актуальный прайс магазина. Новая иконка из прошлых выпусков сохранена без перерисовки.
