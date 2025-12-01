# OpenRouter Integration Guide

Browser-Use имеет нативную поддержку OpenRouter для доступа к множеству LLM моделей через единый API.

## Быстрый старт

```python
from browser_use import Agent
from browser_use.llm import ChatOpenRouter
import os

# Создание LLM клиента
llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet-20250929',  # любая модель OpenRouter
    api_key=os.getenv('OPENROUTER_API_KEY'),
)

# Создание агента
agent = Agent(
    task='Find browser-use GitHub stars',
    llm=llm,
)

# Запуск
import asyncio
asyncio.run(agent.run())
```

## Настройка

### Переменные окружения

Добавьте в `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

Или установите через системные переменные:
```bash
export OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

## Поддерживаемые модели

OpenRouter предоставляет доступ к множеству моделей:

### Anthropic (рекомендуется)
- `anthropic/claude-4.5-sonnet-20250929` - самая новая, мощная
- `anthropic/claude-3.5-sonnet` - быстрая и качественная
- `anthropic/claude-3.5-haiku` - бюджетная

**Важно:** Для Anthropic моделей автоматически применяется оптимизация JSON Schema (удаление validation constraints).

### OpenAI
- `openai/gpt-4o` - полная поддержка JSON Schema
- `openai/gpt-4o-mini` - бюджетная версия
- `openai/o1-preview` - reasoning модель

### Google
- `google/gemini-2.0-flash` - быстрая
- `google/gemini-2.5-pro` - мощная

### Другие
- `deepseek/deepseek-chat` - код-ориентированная
- `x-ai/grok-beta` - альтернативная

Полный список: https://openrouter.ai/models

## Параметры ChatOpenRouter

```python
llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet-20250929',
    api_key='sk-or-v1-xxxxx',

    # Параметры генерации
    temperature=0.7,              # креативность (0.0-2.0)
    top_p=0.9,                    # nucleus sampling
    seed=42,                      # воспроизводимость

    # OpenRouter specific
    http_referer='https://your-app.com',  # для tracking в OpenRouter

    # Anthropic compatibility
    anthropic_compatible_mode=None,  # None = авто-детекция
                                     # True = принудительно
                                     # False = отключить

    # Fallback (v0.0.4+)
    fallback_models=['anthropic/claude-3.5-sonnet', 'openai/gpt-4o'],  # резервные модели
    on_fallback=lambda from_m, to_m, err: print(f"Fallback: {from_m} -> {to_m}"),

    # Metrics (v0.0.4+)
    track_metrics=True,           # включить сбор метрик
)
```

## Автоматическая оптимизация для Anthropic

Browser-Use автоматически определяет Anthropic модели и применяет необходимую оптимизацию JSON Schema:

- ❌ Удаляет `minimum`, `maximum` (не поддерживаются Anthropic)
- ❌ Удаляет `minLength`, `maxLength`
- ❌ Удаляет `pattern`
- ❌ Удаляет `minItems`
- ❌ Удаляет `default`

**Детекция:**
- По имени модели: содержит `anthropic` или `claude`
- Можно переопределить через `anthropic_compatible_mode=True/False`

**Примеры:**
```python
# Auto-detect (рекомендуется)
llm = ChatOpenRouter(model='anthropic/claude-4.5-sonnet', api_key=key)
# anthropic_compatible_mode = None (auto) -> True

# Принудительно включить для custom моделей
llm = ChatOpenRouter(
    model='custom/anthropic-proxy',
    api_key=key,
    anthropic_compatible_mode=True
)

# Принудительно отключить
llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    anthropic_compatible_mode=False  # использует полную schema (может вызвать ошибки!)
)
```

## Использование через get_llm_by_name()

Для удобства можно использовать фабричный метод:

```python
from browser_use.llm import get_llm_by_name
import os

os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-xxxxx'

# Создание через имя
llm = get_llm_by_name('openrouter_anthropic_claude_4_5_sonnet')
# преобразуется в: model='anthropic/claude-4-5-sonnet'
```

**Именование:**
- Формат: `openrouter_provider_model_name`
- `_` заменяется на `/` для provider/model
- Остальные `_` заменяются на `-`

**Примеры:**
```python
'openrouter_anthropic_claude_4_5_sonnet' → 'anthropic/claude-4-5-sonnet'
'openrouter_openai_gpt_4o'                → 'openai/gpt-4o'
'openrouter_google_gemini_2_0_flash'      → 'google/gemini-2-0-flash'
```

## Лучшие практики

### 1. Используйте правильные модели для задач

- **Browser automation:** `anthropic/claude-4.5-sonnet` (reasoning + vision)
- **Простые задачи:** `anthropic/claude-3.5-haiku` (дешево)
- **Код:** `deepseek/deepseek-chat` (специализация)

### 2. Мониторинг затрат

OpenRouter показывает расходы в dashboard: https://openrouter.ai/activity

```python
# Добавьте http_referer для tracking
llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    http_referer='https://myapp.com/feature-x',  # отслеживание по источникам
)
```

### 3. Обработка ошибок

```python
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError

try:
    result = await agent.run()
except ModelRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Переключитесь на другую модель или подождите
except ModelProviderError as e:
    print(f"Provider error: {e}")
    # Проверьте API key, model name, credits
```

### 4. Оптимизация стоимости

```python
# Начните с быстрой модели для тестов
llm_test = ChatOpenRouter(model='anthropic/claude-3.5-haiku', api_key=key)
agent_test = Agent(task='test task', llm=llm_test)

# Переключитесь на мощную для production
llm_prod = ChatOpenRouter(model='anthropic/claude-4.5-sonnet', api_key=key)
agent_prod = Agent(task='real task', llm=llm_prod)
```

## Troubleshooting

### Ошибка: "OPENROUTER_API_KEY is not set"

```python
# Убедитесь что ключ установлен
import os
print(os.getenv('OPENROUTER_API_KEY'))  # должно вывести ваш ключ

# Или передайте напрямую
llm = ChatOpenRouter(model='...', api_key='sk-or-v1-xxxxx')
```

### Ошибка: "property 'minimum' is not supported"

Если видите эту ошибку с Anthropic моделью:

```python
# Проверьте автодетекцию
llm = ChatOpenRouter(model='anthropic/claude-4.5-sonnet', api_key=key)
print(llm._is_anthropic_model())  # должно быть True

# Принудительно включите совместимость
llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    anthropic_compatible_mode=True  # явно
)
```

### Низкая скорость ответа

- OpenRouter использует proxying → может быть медленнее direct API
- Некоторые модели популярны → queue time
- Решение: используйте модели с меньшей нагрузкой или direct API

## Примеры

### Пример 1: Простая навигация

```python
from browser_use import Agent
from browser_use.llm import ChatOpenRouter
import os

llm = ChatOpenRouter(
    model='anthropic/claude-3.5-haiku',  # быстрая модель
    api_key=os.getenv('OPENROUTER_API_KEY'),
)

agent = Agent(
    task='Go to google.com and search for "browser automation"',
    llm=llm,
)

import asyncio
result = asyncio.run(agent.run(max_steps=5))
print(result.final_result())
```

### Пример 2: Сложная задача с vision

```python
from browser_use import Agent
from browser_use.llm import ChatOpenRouter
import os

llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',  # мощная с vision
    api_key=os.getenv('OPENROUTER_API_KEY'),
    temperature=0.5,  # более детерминированное поведение
)

agent = Agent(
    task='Find browser-use GitHub repo, count stars, and check latest release',
    llm=llm,
    use_vision=True,  # используем vision для сложных страниц
)

import asyncio
result = asyncio.run(agent.run(max_steps=10))
print(result.final_result())
```

### Пример 3: Сравнение моделей

```python
from browser_use import Agent
from browser_use.llm import ChatOpenRouter
import os
import asyncio

models = [
    'anthropic/claude-4.5-sonnet',
    'openai/gpt-4o',
    'google/gemini-2.0-flash',
]

async def test_model(model_name):
    llm = ChatOpenRouter(model=model_name, api_key=os.getenv('OPENROUTER_API_KEY'))
    agent = Agent(task='Go to google.com', llm=llm)
    result = await agent.run(max_steps=3)
    return model_name, result

async def main():
    results = await asyncio.gather(*[test_model(m) for m in models])
    for model, result in results:
        print(f"{model}: {result.is_done()}")

asyncio.run(main())
```

## Автоматический fallback между моделями (v0.0.4+)

Если основная модель недоступна (rate limit, ошибка сервера), автоматически переключается на резервную.

### Настройка fallback

```python
from browser_use.llm import ChatOpenRouter

llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    fallback_models=['anthropic/claude-3.5-sonnet', 'openai/gpt-4o'],
)

# При ошибке claude-4.5-sonnet:
# 1. Попробует claude-3.5-sonnet
# 2. Если не получится - попробует gpt-4o
# 3. Если все не получилось - выбросит исключение
```

### Callback для уведомлений

```python
def on_fallback(from_model: str, to_model: str, error: Exception):
    print(f"Switching from {from_model} to {to_model}")
    # Можно добавить логирование, алерты и т.д.

llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    fallback_models=['openai/gpt-4o'],
    on_fallback=on_fallback,
)
```

### Проверка активной модели

```python
# После вызова ainvoke() можно проверить какая модель использовалась
result = await llm.ainvoke(messages)
print(f"Used model: {llm.active_model}")  # может отличаться от primary если был fallback
```

---

## Мониторинг и метрики (v0.0.4+)

Встроенный сбор метрик для отслеживания использования, производительности и затрат.

### Включение метрик

```python
from browser_use.llm import ChatOpenRouter

llm = ChatOpenRouter(
    model='anthropic/claude-4.5-sonnet',
    api_key=key,
    track_metrics=True,  # включить сбор метрик
)

# После выполнения запросов
metrics = llm.get_metrics()
print(f"Total requests: {metrics.total_requests}")
print(f"Total tokens: {metrics.total_tokens}")
print(f"Average latency: {metrics.average_latency_ms:.1f}ms")
print(f"Estimated cost: ${metrics.cost_estimate_usd:.4f}")
```

### Доступные метрики

```python
from browser_use.llm.metrics import LLMMetrics

metrics: LLMMetrics = llm.get_metrics()

# Счетчики запросов
metrics.total_requests        # всего запросов
metrics.successful_requests   # успешных
metrics.failed_requests       # неудачных
metrics.fallback_count        # количество fallback'ов

# Токены
metrics.total_prompt_tokens      # токены в промптах
metrics.total_completion_tokens  # токены в ответах
metrics.total_tokens             # всего токенов
metrics.total_cached_tokens      # кэшированных токенов

# Производительность
metrics.average_latency_ms    # средняя задержка в мс

# Стоимость
metrics.cost_estimate_usd     # оценка затрат в USD
```

### Экспорт метрик

```python
# JSON формат
data = metrics.to_dict()

# Prometheus формат
prometheus_output = metrics.to_prometheus()

# Breakdown по моделям
breakdown = metrics.get_model_breakdown()
for model, stats in breakdown.items():
    print(f"{model}: {stats['requests']} requests, ${stats['cost_usd']:.4f}")
```

### Быстрый доступ к стоимости

```python
# Короткий способ получить оценку затрат
cost = llm.get_estimated_cost()
print(f"Total cost: ${cost:.4f}")
```

### Внешний экземпляр метрик

```python
from browser_use.llm.metrics import LLMMetrics

# Создаем общий экземпляр для нескольких клиентов
shared_metrics = LLMMetrics()

llm1 = ChatOpenRouter(model='anthropic/claude-4.5-sonnet', api_key=key, metrics=shared_metrics)
llm2 = ChatOpenRouter(model='openai/gpt-4o', api_key=key, metrics=shared_metrics)

# Все запросы агрегируются в shared_metrics
print(f"Combined cost: ${shared_metrics.cost_estimate_usd:.4f}")
```

---

## Расширенная детекция провайдеров (v0.0.3+)

Browser-Use автоматически определяет провайдера по имени модели и применяет соответствующую оптимизацию schema.

### Поддерживаемые провайдеры

| Провайдер | Паттерны | Профиль |
|-----------|----------|---------|
| Anthropic | `anthropic/`, `claude` | anthropic (без validation constraints) |
| Google | `google/`, `gemini` | google |
| DeepSeek | `deepseek/` | deepseek |
| OpenAI | `openai/`, `gpt`, `o1` | full |
| Meta | `meta/`, `llama` | full |
| Mistral | `mistral/`, `mixtral` | full |

### Использование ProviderType

```python
from browser_use.llm.schema import ProviderType, SchemaOptimizer

# Автоопределение провайдера
provider = ProviderType.from_model_name('google/gemini-2.0-flash')
print(provider)  # ProviderType.GOOGLE

# Получение профиля оптимизации
profile = provider.get_schema_profile()
print(profile)  # SchemaOptimizationProfile.GOOGLE

# Создание schema для провайдера
from pydantic import BaseModel

class MyModel(BaseModel):
    field: str

schema = SchemaOptimizer.create_schema_for_provider(MyModel, 'anthropic/claude-4.5-sonnet')
```

## Дополнительные ресурсы

- OpenRouter Docs: https://openrouter.ai/docs
- OpenRouter Models: https://openrouter.ai/models
- OpenRouter Pricing: https://openrouter.ai/models (see each model)
- OpenRouter Dashboard: https://openrouter.ai/activity

## Версия

- Добавлено в версии: `0.0.2`
- Расширенная детекция провайдеров: `0.0.3`
- Fallback и метрики: `0.0.4`
- Последнее обновление: 2025-12-01
