# Журнал изменений

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
проект следует принципам [Semantic Versioning](https://semver.org/lang/ru/).

## [0.0.4] - 2025-12-01

### Added
- **Automatic Model Fallback**: Resilient model switching on failures
  - `fallback_models: list[str]` parameter for backup models
  - `on_fallback: Callable` callback for fallback notifications
  - `active_model` property to check which model was used
  - Automatic retry on RateLimitError, APIConnectionError, APIStatusError
- **LLM Metrics Tracking**: Comprehensive usage monitoring
  - New `browser_use/llm/metrics.py` module
  - `LLMMetrics` class with request/token/latency tracking
  - `RequestMetrics` class for individual request data
  - `track_metrics: bool` parameter to enable tracking
  - `get_metrics()` method to access metrics instance
- **Cost Estimation**: Real-time cost tracking
  - `ModelPricing` class with per-model pricing
  - `KNOWN_MODEL_PRICING` database for common models
  - `cost_estimate_usd` property for total cost
  - `get_estimated_cost()` shortcut method
- **Metrics Export**: Multiple export formats
  - `to_dict()` for JSON export
  - `to_prometheus()` for Prometheus format
  - `get_model_breakdown()` for per-model statistics

### Changed
- `ChatOpenRouter.ainvoke()` now supports fallback chain execution
- Refactored `_invoke_with_model()` to track timing and metrics
- Added `_record_metrics()`, `_log_fallback()`, `_notify_fallback()` helper methods

---

## [0.0.3] - 2025-12-01

### Added
- **Extended Provider Detection**: Auto-detection for 6 LLM providers
  - `ProviderType` enum: OPENAI, ANTHROPIC, GOOGLE, DEEPSEEK, META, MISTRAL, UNKNOWN
  - `ProviderType.from_model_name(model)` method for auto-detection
  - `_get_provider_type()`, `_is_google_model()`, `_is_deepseek_model()` methods in `ChatOpenRouter`
- **Schema Optimization Profiles**: Provider-specific schema optimization
  - `SchemaOptimizationProfile` enum: FULL, ANTHROPIC, GOOGLE, DEEPSEEK, MINIMAL
  - `ProviderType.get_schema_profile()` method
  - `SchemaOptimizer.create_schema_for_provider(model, provider)` method
- **Emoji Utilities**: Windows compatibility utilities
  - `EMOJI_TO_ASCII` mapping (43 emoji -> ASCII)
  - `sanitize_emoji()` function
  - `is_windows_legacy_encoding()` detection
  - `safe_print()` wrapper function

### Fixed
- **BUG-001**: Windows cp1251 emoji encoding error - RESOLVED
  - `EmojiSanitizingFilter` class in `logging_config.py`
  - Auto-detection of legacy Windows encodings (cp1251, cp1252, etc.)
  - Automatic sanitization of log messages with emojis
  - Fixed print statements in `SignalHandler` class

### Changed
- `ChatOpenRouter.ainvoke()` now uses `create_schema_for_provider()` for all providers
- Refactored `_is_anthropic_model()` to use `ProviderType` enum

---

## [0.0.2] - 2025-12-01

### Added
- **OpenRouter Integration**: Native support for OpenRouter as LLM provider
  - `ChatOpenRouter` class with full browser-use compatibility
  - `OPENROUTER_API_KEY` configuration support
  - Auto-detection of Anthropic models via `_is_anthropic_model()` method
  - `anthropic_compatible_mode` parameter for manual control
- **Schema Optimization**: Enhanced `SchemaOptimizer` for Anthropic compatibility
  - New `remove_validation_constraints` parameter
  - Automatic removal of unsupported JSON Schema fields (`minimum`, `maximum`, `minLength`, `maxLength`, `pattern`)
- **Documentation**: Comprehensive OpenRouter guide (`userdocs/main/openrouter.md`)
- **Type Stubs**: Added stubs for popular OpenRouter models

### Changed
- `get_llm_by_name()` now supports `openrouter` provider prefix
- Model name conversion: `openrouter_anthropic_claude_4_5_sonnet` → `anthropic/claude-4-5-sonnet`

### Fixed
- JSON Schema validation errors when using Anthropic models through OpenRouter
  - Error: "property 'minimum' is not supported" - RESOLVED

## [0.0.1] - 2025-11-30

### Added
- Initial OpenRouter integration attempt
- Basic `ChatOpenRouter` class implementation
- Diagnostic report for JSON Schema compatibility issues

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
