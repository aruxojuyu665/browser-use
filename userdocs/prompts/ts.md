# Update

<current_version> = 0.0.1
<version_update> = <current_version> + 0.0.1
<future_version> = <version_update> + 0.0.1
**example:** 0.8.1 + 0.0.1 = 0.8.2

# Введение
Хорошо, давай доработаем ПО для полной поддержки anthropic/claude-4.5-sonnet-20250929

# Цель
Модернизировать текущее ПО для полной поддержки Openrouter Anthropic моделей

# Данные
- Документация OpenRouter: .userdocs/OpenRouterDocs-main
- Предыдущие отчеты: .userdocs/reports
- Директория с пользовательской документацией: .userdocs/
- Директория для основной документации: .userdocs/main/

# Задачи
- Запуск всех имеющихся тестов для проверки реализованного функционала
- Формирование TODO листа для достижения целей обновления в .userdocs/todo/<version_update>.md
- Добавление в TODO лист уже выполненных задач за текущую сессию (с пометкой "выполнено")
- Обновление текущего ПО согласно сформированному TODO листу
- Комплексное тестирование нововведений и багфикс
- При необходимости сформируй TODO лист для следующей версии и сохрани его в .userdocs/todo/<future_version>.md (Если какие-то из задач не были выполнены в текущей сессии, необходимо перенести их в TODO лист для следующего обновления)
- Обновление документации проекта в .userdocs/main/
- Добавление отчета в .userdocs/reports/<version_update>.md
- git add . && git commit -m "<version_update>" && git push

# Критические принципы
- **Первые принципы** по Маску - необходимо стараться принимать решения исходя из первых принципов Илона Маска
- **Принципы SOLID** - Single Responsibility Principle (Принцип единственной ответственности), Open/Closed Principle (Принцип открытости/закрытости), Liskov Substitution Principle (Принцип подстановки Лисков), Interface Segregation Principle (Принцип разделения интерфейса), Dependency Inversion Principle (Принцип инверсии зависимостей)
- **KISS (Keep It Simple, Stupid)** - максимальная простота
- **DRY (Don't Repeat Yourself)** - избегать дублирования