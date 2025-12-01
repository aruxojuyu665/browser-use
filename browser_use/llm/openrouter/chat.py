import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar, overload

import httpx
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params.response_format_json_schema import (
	JSONSchema,
	ResponseFormatJSONSchema,
)
from pydantic import BaseModel

from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.metrics import LLMMetrics, RequestMetrics
from browser_use.llm.openrouter.serializer import OpenRouterMessageSerializer
from browser_use.llm.schema import ProviderType, SchemaOptimizer
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# Type alias for fallback callback
FallbackCallback = Callable[[str, str, Exception], None]


@dataclass
class ChatOpenRouter(BaseChatModel):
	"""
	A wrapper around OpenRouter's chat API, which provides access to various LLM models
	through a unified OpenAI-compatible interface.

	This class implements the BaseChatModel protocol for OpenRouter's API.
	"""

	# Model configuration
	model: str

	# Model params
	temperature: float | None = None
	top_p: float | None = None
	seed: int | None = None

	# Client initialization parameters
	api_key: str | None = None
	http_referer: str | None = None  # OpenRouter specific parameter for tracking
	base_url: str | httpx.URL = 'https://openrouter.ai/api/v1'
	timeout: float | httpx.Timeout | None = None
	max_retries: int = 10
	default_headers: Mapping[str, str] | None = None
	default_query: Mapping[str, object] | None = None
	http_client: httpx.AsyncClient | None = None
	_strict_response_validation: bool = False
	extra_body: dict[str, Any] | None = None

	# Anthropic compatibility mode
	# None = auto-detect based on model name
	# True = force Anthropic-compatible schema optimization
	# False = use full JSON Schema with validation constraints
	anthropic_compatible_mode: bool | None = None

	# Fallback configuration
	# List of fallback models to try if the primary model fails
	fallback_models: list[str] = field(default_factory=list)
	# Callback to notify when a fallback occurs: (from_model, to_model, error) -> None
	on_fallback: FallbackCallback | None = None

	# Metrics configuration
	# Enable metrics tracking (costs, latency, token usage)
	track_metrics: bool = False
	# External metrics instance (if None and track_metrics=True, creates internal one)
	metrics: LLMMetrics | None = None

	# Internal state for tracking active model
	_active_model: str | None = field(default=None, repr=False)

	# Static
	@property
	def provider(self) -> str:
		return 'openrouter'

	def __post_init__(self) -> None:
		"""Initialize active model and metrics tracking."""
		self._active_model = self.model
		# Initialize internal metrics if tracking enabled but no external metrics provided
		if self.track_metrics and self.metrics is None:
			self.metrics = LLMMetrics()

	def get_metrics(self) -> LLMMetrics | None:
		"""
		Get the metrics instance.

		Returns:
			LLMMetrics if tracking is enabled, None otherwise
		"""
		return self.metrics

	def get_estimated_cost(self) -> float:
		"""
		Get the estimated cost in USD for all tracked requests.

		Returns:
			Estimated cost in USD, or 0.0 if metrics tracking is disabled
		"""
		if self.metrics is None:
			return 0.0
		return self.metrics.cost_estimate_usd

	def _get_client_params(self) -> dict[str, Any]:
		"""Prepare client parameters dictionary."""
		# Define base client params
		base_params = {
			'api_key': self.api_key,
			'base_url': self.base_url,
			'timeout': self.timeout,
			'max_retries': self.max_retries,
			'default_headers': self.default_headers,
			'default_query': self.default_query,
			'_strict_response_validation': self._strict_response_validation,
			'top_p': self.top_p,
			'seed': self.seed,
		}

		# Create client_params dict with non-None values
		client_params = {k: v for k, v in base_params.items() if v is not None}

		# Add http_client if provided
		if self.http_client is not None:
			client_params['http_client'] = self.http_client

		return client_params

	def get_client(self) -> AsyncOpenAI:
		"""
		Returns an AsyncOpenAI client configured for OpenRouter.

		Returns:
		    AsyncOpenAI: An instance of the AsyncOpenAI client with OpenRouter base URL.
		"""
		if not hasattr(self, '_client'):
			client_params = self._get_client_params()
			self._client = AsyncOpenAI(**client_params)
		return self._client

	@property
	def name(self) -> str:
		return str(self.model)

	def _get_provider_type(self) -> ProviderType:
		"""
		Detect the provider type based on model name.

		Returns:
		    ProviderType enum indicating the detected provider
		"""
		return ProviderType.from_model_name(self.model)

	def _is_anthropic_model(self) -> bool:
		"""
		Detect if the model is from Anthropic based on model name.

		Returns:
		    True if model appears to be from Anthropic (contains 'anthropic' or 'claude')
		"""
		return self._get_provider_type() == ProviderType.ANTHROPIC

	def _is_google_model(self) -> bool:
		"""
		Detect if the model is from Google based on model name.

		Returns:
		    True if model appears to be from Google (contains 'google' or 'gemini')
		"""
		return self._get_provider_type() == ProviderType.GOOGLE

	def _is_deepseek_model(self) -> bool:
		"""
		Detect if the model is from DeepSeek based on model name.

		Returns:
		    True if model appears to be from DeepSeek (contains 'deepseek')
		"""
		return self._get_provider_type() == ProviderType.DEEPSEEK

	def _get_usage(self, response: ChatCompletion) -> ChatInvokeUsage | None:
		"""Extract usage information from the OpenRouter response."""
		if response.usage is None:
			return None

		prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
		cached_tokens = prompt_details.cached_tokens if prompt_details else None

		return ChatInvokeUsage(
			prompt_tokens=response.usage.prompt_tokens,
			prompt_cached_tokens=cached_tokens,
			prompt_cache_creation_tokens=None,
			prompt_image_tokens=None,
			# Completion
			completion_tokens=response.usage.completion_tokens,
			total_tokens=response.usage.total_tokens,
		)

	def _get_schema_for_model(self, output_format: type[BaseModel], model_name: str) -> dict[str, Any]:
		"""
		Get optimized schema for a specific model.

		Args:
			output_format: Pydantic model class for structured output
			model_name: The model name to optimize for

		Returns:
			Optimized JSON schema dict
		"""
		if self.anthropic_compatible_mode is True:
			# Explicitly force Anthropic mode
			return SchemaOptimizer.create_schema_for_provider(output_format, ProviderType.ANTHROPIC)
		elif self.anthropic_compatible_mode is False:
			# Explicitly use full schema
			return SchemaOptimizer.create_optimized_json_schema(output_format)
		else:
			# Auto-detect based on model name (default)
			return SchemaOptimizer.create_schema_for_provider(output_format, model_name)

	def _record_metrics(
		self,
		model_name: str,
		usage: ChatInvokeUsage | None,
		latency_ms: float,
		success: bool = True,
		error: str | None = None,
		is_fallback: bool = False,
		from_model: str | None = None,
	) -> None:
		"""Record request metrics if tracking is enabled."""
		if self.metrics is None:
			return

		self.metrics.record_request(
			RequestMetrics(
				model=model_name,
				prompt_tokens=usage.prompt_tokens if usage else 0,
				completion_tokens=usage.completion_tokens if usage else 0,
				total_tokens=usage.total_tokens if usage else 0,
				latency_ms=latency_ms,
				success=success,
				error=error,
				is_fallback=is_fallback,
				from_model=from_model,
				cached_tokens=usage.prompt_cached_tokens or 0 if usage else 0,
			)
		)

	async def _invoke_with_model(
		self,
		model_name: str,
		openrouter_messages: list[ChatCompletionMessageParam],
		extra_headers: dict[str, str],
		output_format: type[T] | None = None,
		is_fallback: bool = False,
		from_model: str | None = None,
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		"""
		Internal method to invoke a specific model.

		Args:
			model_name: The model to invoke
			openrouter_messages: Serialized messages
			extra_headers: Extra HTTP headers
			output_format: Optional Pydantic model class for structured output
			is_fallback: Whether this is a fallback request
			from_model: If fallback, the model that failed

		Returns:
			ChatInvokeCompletion with the response
		"""
		start_time = time.perf_counter()

		if output_format is None:
			# Return string response
			response = await self.get_client().chat.completions.create(
				model=model_name,
				messages=openrouter_messages,
				temperature=self.temperature,
				top_p=self.top_p,
				seed=self.seed,
				extra_headers=extra_headers,
				**(self.extra_body or {}),
			)

			usage = self._get_usage(response)
			latency_ms = (time.perf_counter() - start_time) * 1000

			# Record metrics
			self._record_metrics(
				model_name=model_name,
				usage=usage,
				latency_ms=latency_ms,
				is_fallback=is_fallback,
				from_model=from_model,
			)

			return ChatInvokeCompletion(
				completion=response.choices[0].message.content or '',
				usage=usage,
			)

		else:
			# Create a JSON schema for structured output
			schema = self._get_schema_for_model(output_format, model_name)

			response_format_schema: JSONSchema = {
				'name': 'agent_output',
				'strict': True,
				'schema': schema,
			}

			# Return structured response
			response = await self.get_client().chat.completions.create(
				model=model_name,
				messages=openrouter_messages,
				temperature=self.temperature,
				top_p=self.top_p,
				seed=self.seed,
				response_format=ResponseFormatJSONSchema(
					json_schema=response_format_schema,
					type='json_schema',
				),
				extra_headers=extra_headers,
				**(self.extra_body or {}),
			)

			if response.choices[0].message.content is None:
				raise ModelProviderError(
					message='Failed to parse structured output from model response',
					status_code=500,
					model=model_name,
				)
			usage = self._get_usage(response)
			latency_ms = (time.perf_counter() - start_time) * 1000

			# Record metrics
			self._record_metrics(
				model_name=model_name,
				usage=usage,
				latency_ms=latency_ms,
				is_fallback=is_fallback,
				from_model=from_model,
			)

			parsed = output_format.model_validate_json(response.choices[0].message.content)

			return ChatInvokeCompletion(
				completion=parsed,
				usage=usage,
			)

	def _log_fallback(self, from_model: str, to_model: str, error: Exception) -> None:
		"""Log a fallback event."""
		logger.warning(f'Fallback: {from_model} -> {to_model} (error: {error})')

	def _notify_fallback(self, from_model: str, to_model: str, error: Exception) -> None:
		"""Notify callback about fallback if configured."""
		if self.on_fallback:
			try:
				self.on_fallback(from_model, to_model, error)
			except Exception as callback_error:
				logger.warning(f'Fallback callback error: {callback_error}')

	@property
	def active_model(self) -> str:
		"""Get the currently active model (may differ from primary if fallback occurred)."""
		return self._active_model or self.model

	@overload
	async def ainvoke(self, messages: list[BaseMessage], output_format: None = None) -> ChatInvokeCompletion[str]: ...

	@overload
	async def ainvoke(self, messages: list[BaseMessage], output_format: type[T]) -> ChatInvokeCompletion[T]: ...

	async def ainvoke(
		self, messages: list[BaseMessage], output_format: type[T] | None = None
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		"""
		Invoke the model with the given messages through OpenRouter.

		If fallback_models are configured, will automatically try each fallback
		model in order if the primary model fails.

		Args:
		    messages: List of chat messages
		    output_format: Optional Pydantic model class for structured output

		Returns:
		    Either a string response or an instance of output_format

		Raises:
		    ModelRateLimitError: If all models hit rate limits
		    ModelProviderError: If all models fail with provider errors
		"""
		openrouter_messages = OpenRouterMessageSerializer.serialize_messages(messages)

		# Set up extra headers for OpenRouter
		extra_headers = {}
		if self.http_referer:
			extra_headers['HTTP-Referer'] = self.http_referer

		# Build list of models to try: primary + fallbacks
		models_to_try = [self.model] + list(self.fallback_models)
		last_error: Exception | None = None
		previous_model: str | None = None

		for i, current_model in enumerate(models_to_try):
			is_fallback = i > 0
			try:
				result = await self._invoke_with_model(
					model_name=current_model,
					openrouter_messages=openrouter_messages,
					extra_headers=extra_headers,
					output_format=output_format,
					is_fallback=is_fallback,
					from_model=previous_model,
				)
				# Success - update active model and return
				self._active_model = current_model
				return result

			except RateLimitError as e:
				last_error = e
				# Record failed request metrics
				self._record_metrics(
					model_name=current_model,
					usage=None,
					latency_ms=0,
					success=False,
					error=str(e),
					is_fallback=is_fallback,
					from_model=previous_model,
				)
				# If we have more models to try, attempt fallback
				if i < len(models_to_try) - 1:
					next_model = models_to_try[i + 1]
					self._log_fallback(current_model, next_model, e)
					self._notify_fallback(current_model, next_model, e)
					previous_model = current_model
					continue
				# No more fallbacks - raise as ModelRateLimitError
				raise ModelRateLimitError(message=e.message, model=current_model) from e

			except APIConnectionError as e:
				last_error = e
				self._record_metrics(
					model_name=current_model,
					usage=None,
					latency_ms=0,
					success=False,
					error=str(e),
					is_fallback=is_fallback,
					from_model=previous_model,
				)
				if i < len(models_to_try) - 1:
					next_model = models_to_try[i + 1]
					self._log_fallback(current_model, next_model, e)
					self._notify_fallback(current_model, next_model, e)
					previous_model = current_model
					continue
				raise ModelProviderError(message=str(e), model=current_model) from e

			except APIStatusError as e:
				last_error = e
				self._record_metrics(
					model_name=current_model,
					usage=None,
					latency_ms=0,
					success=False,
					error=str(e),
					is_fallback=is_fallback,
					from_model=previous_model,
				)
				if i < len(models_to_try) - 1:
					next_model = models_to_try[i + 1]
					self._log_fallback(current_model, next_model, e)
					self._notify_fallback(current_model, next_model, e)
					previous_model = current_model
					continue
				raise ModelProviderError(message=e.message, status_code=e.status_code, model=current_model) from e

			except Exception as e:
				last_error = e
				self._record_metrics(
					model_name=current_model,
					usage=None,
					latency_ms=0,
					success=False,
					error=str(e),
					is_fallback=is_fallback,
					from_model=previous_model,
				)
				if i < len(models_to_try) - 1:
					next_model = models_to_try[i + 1]
					self._log_fallback(current_model, next_model, e)
					self._notify_fallback(current_model, next_model, e)
					previous_model = current_model
					continue
				raise ModelProviderError(message=str(e), model=current_model) from e

		# Should not reach here, but handle edge case
		assert last_error is not None
		raise ModelProviderError(message=str(last_error), model=self.model) from last_error
