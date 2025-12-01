```md

# New Update

<current_version> = 0.0.3
<version_update> = <current_version> + 0.0.1
<future_version> = <version_update> + 0.0.1
**example:** 0.8.1 + 0.0.1 = 0.8.2

# Контекст
- Список задач: .userdocs\todo\<version_update>.md

# Документация
...

# Задачи
- Изучи документацию проекта в корне репозитория для понимания текущего состояния проекта (<current_version>)
- Изучи TODO лист для предстоящего обновления: .userdocs\todo\<version_update>.md
- Выполни обновление согласно TODO листу
- Создай отчет об обновлении в .userdocs\reports\<version_update>.md
- Сформируй TODO лист для следующей версии и сохрани его в .userdocs\todo\<future_version>.md (Если какие-то из задач не были выполнены в текущей сессии, необходимо перенести их в TODO лист для следующего обновления)
- Обнови TODO лист, отметив выполненные задачи: .userdocs\todo\<version_update>.md
- Если можно упростить документацию не жертвуя ее полезностью, необходимо упростить ее (например, исключить дублирования)
- Обнови документацию проекта и проверь ее актуальность: .userdocs\main\
- Поставь текущую версию в .userdocs\prompts\update.md

# Критические принципы
- **Первые принципы** по Маску - необходимо стараться принимать решения исходя из первых принципов Илона Маска
- **Принципы SOLID** - Single Responsibility Principle (Принцип единственной ответственности), Open/Closed Principle (Принцип открытости/закрытости), Liskov Substitution Principle (Принцип подстановки Лисков), Interface Segregation Principle (Принцип разделения интерфейса), Dependency Inversion Principle (Принцип инверсии зависимостей)
- **KISS (Keep It Simple, Stupid)** - максимальная простота
- **DRY (Don't Repeat Yourself)** - избегать дублирования

```