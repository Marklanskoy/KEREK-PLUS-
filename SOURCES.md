# Источники и происхождение выпуска KEREK 3.3.0

1. Основа: Marklanskoy/KEREK-PLUS-, commit `0d9d9228b29a25efb93f90410c25286ed65cc92a`, KEREK3.2.0. release.json, app.js и права репозитория прочитаны через подключённый GitHub 13 октября 2026. Доступ только чтение, публикация не выполнялась.
2. Соответствие локального предыдущего исходника проверено по Git blob SHA app.js `1478fbd4533fc0d5769a7a1324ca5d1abbd850f3`. Готовый HTML основы: SHA256 `eafae6b5fb2487b776340c57028c33e18830463d27b1a892da99d7205aa5bbf6`.
3. Запрос пользователя основан на `KEREK_3_2_Cart_Audit_2026-10-13.md`, замечания A1–A11. Отчёт прочитан целиком. Он описывает предыдущую3.2, а не результаты исправленной версии.
4. MDN, Working with History API: https://developer.mozilla.org/en-US/docs/Web/API/History_API/Working_with_the_History_API — внутренняя история и восстановление состояния экрана.
5. MDN, HTMLElement.focus: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus — восстановление фокуса, preventScroll.
6. W3C, Understanding Status Messages: https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html — ненавязчивое сообщение изменения количества/итога.
7. Сохранённые решения3.2: MDN Web Locks API https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API и ServiceWorkerRegistration.update https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/update .
8. Иконка — ранее сгенерированная по запросу пользователя оранжево-жёлтая K с корзиной. Размеры и подключение сохранены. Фотографии каталога — иллюстративные Unsplash-ссылки, не фотографии подтверждённых магазинных SKU.

В тестах только вымышленные данные. DOM-стенд специально блокирует изображения/сеть и подставляет модель localStorage/Web Locks; эмодзи в скриншотах не доказывают отсутствие изображений на сайте. Секреты, платёжные данные, личные базы пользователя в комплект не включены.
