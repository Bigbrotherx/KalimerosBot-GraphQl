# KalimerosBot - GraphQL

## Описание  
KalimerosBot — это приложение, работающее с FastAPI и GraphQL.  

## Подготовка перед запуском  
1. Создайте файл `.env` в корневой директории проекта и добавьте следующие переменные:  

    ```env
    DOMAIN=
    API_AUDIENCE=
    ISSUER=
    ALGORITHMS=

    CLIENT_ID=
    CLIENT_SECRET=

    APP_SECRET_KEY=
    SCOPES=
    ```

   ⚠️ Обязательно замените значения переменных на актуальные данные вашего приложения.  

---

## Запуск Docker Compose  
Выполните следующую команду для сборки и запуска приложения:  

```bash
  docker-compose up --build -d
```
Приложение будет запущено и станет доступным по ссылке:

[GraphQL Playground](http://localhost:8000/graphql)
