"""
LLM Metrics tracking for monitoring usage, performance, and costs.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RequestMetrics(BaseModel):
	"""Metrics for a single LLM request."""

	model_config = ConfigDict(extra='forbid')

	model: str
	"""Model used for this request."""

	prompt_tokens: int = 0
	"""Number of tokens in the prompt."""

	completion_tokens: int = 0
	"""Number of tokens in the completion."""

	total_tokens: int = 0
	"""Total tokens used."""

	latency_ms: float = 0.0
	"""Request latency in milliseconds."""

	success: bool = True
	"""Whether the request succeeded."""

	error: str | None = None
	"""Error message if request failed."""

	is_fallback: bool = False
	"""Whether this request was a fallback from another model."""

	from_model: str | None = None
	"""If fallback, the model that failed."""

	cached_tokens: int = 0
	"""Number of cached tokens (if applicable)."""

	timestamp: float = Field(default_factory=time.time)
	"""Unix timestamp of the request."""


class ModelPricing(BaseModel):
	"""Pricing information for a model."""

	model_config = ConfigDict(extra='forbid')

	prompt_per_million: float = 0.0
	"""Price per million prompt tokens in USD."""

	completion_per_million: float = 0.0
	"""Price per million completion tokens in USD."""

	cached_prompt_per_million: float | None = None
	"""Price per million cached prompt tokens (if different)."""


# Known pricing for common models (USD per million tokens)
# Prices as of late 2024 - should be updated periodically
KNOWN_MODEL_PRICING: dict[str, ModelPricing] = {
	# Anthropic models
	'anthropic/claude-4.5-sonnet': ModelPricing(prompt_per_million=3.0, completion_per_million=15.0),
	'anthropic/claude-4.5-sonnet-20250929': ModelPricing(prompt_per_million=3.0, completion_per_million=15.0),
	'anthropic/claude-3.5-sonnet': ModelPricing(prompt_per_million=3.0, completion_per_million=15.0),
	'anthropic/claude-3.5-haiku': ModelPricing(prompt_per_million=0.80, completion_per_million=4.0),
	# OpenAI models
	'openai/gpt-4o': ModelPricing(prompt_per_million=2.50, completion_per_million=10.0),
	'openai/gpt-4o-mini': ModelPricing(prompt_per_million=0.15, completion_per_million=0.60),
	'openai/o1-preview': ModelPricing(prompt_per_million=15.0, completion_per_million=60.0),
	# Google models
	'google/gemini-2.0-flash': ModelPricing(prompt_per_million=0.10, completion_per_million=0.40),
	'google/gemini-2.5-pro': ModelPricing(prompt_per_million=1.25, completion_per_million=5.0),
	# DeepSeek models
	'deepseek/deepseek-chat': ModelPricing(prompt_per_million=0.14, completion_per_million=0.28),
}


@dataclass
class LLMMetrics:
	"""
	Aggregate metrics for LLM usage tracking.

	Thread-safe metrics collection for monitoring LLM requests,
	token usage, latency, errors, and cost estimation.

	Example:
		metrics = LLMMetrics()

		# Track a request
		metrics.record_request(RequestMetrics(
			model='anthropic/claude-4.5-sonnet',
			prompt_tokens=100,
			completion_tokens=50,
			total_tokens=150,
			latency_ms=1500.0,
		))

		# Get summary
		print(f"Total cost: ${metrics.cost_estimate_usd:.4f}")
		print(f"Avg latency: {metrics.average_latency_ms:.1f}ms")
	"""

	# Request tracking
	_requests: list[RequestMetrics] = field(default_factory=list)

	# Counters
	total_requests: int = 0
	successful_requests: int = 0
	failed_requests: int = 0
	fallback_count: int = 0

	# Token tracking
	total_prompt_tokens: int = 0
	total_completion_tokens: int = 0
	total_cached_tokens: int = 0

	# Custom pricing overrides
	_pricing_overrides: dict[str, ModelPricing] = field(default_factory=dict)

	def record_request(self, request: RequestMetrics) -> None:
		"""
		Record a completed LLM request.

		Args:
			request: The request metrics to record
		"""
		self._requests.append(request)
		self.total_requests += 1

		if request.success:
			self.successful_requests += 1
			self.total_prompt_tokens += request.prompt_tokens
			self.total_completion_tokens += request.completion_tokens
			self.total_cached_tokens += request.cached_tokens
		else:
			self.failed_requests += 1

		if request.is_fallback:
			self.fallback_count += 1

	def record_fallback(self, from_model: str, to_model: str, error: str) -> None:
		"""
		Record a fallback event (for tracking purposes without full request data).

		Args:
			from_model: The model that failed
			to_model: The model we're falling back to
			error: The error that triggered the fallback
		"""
		self.fallback_count += 1

	def set_pricing(self, model: str, pricing: ModelPricing) -> None:
		"""
		Set custom pricing for a model.

		Args:
			model: Model identifier
			pricing: Pricing information
		"""
		self._pricing_overrides[model] = pricing

	def get_pricing(self, model: str) -> ModelPricing:
		"""
		Get pricing for a model.

		Args:
			model: Model identifier

		Returns:
			ModelPricing for the model (or zeros if unknown)
		"""
		# Check overrides first
		if model in self._pricing_overrides:
			return self._pricing_overrides[model]

		# Check known pricing
		if model in KNOWN_MODEL_PRICING:
			return KNOWN_MODEL_PRICING[model]

		# Try partial match for versioned models
		for known_model, pricing in KNOWN_MODEL_PRICING.items():
			if model.startswith(known_model) or known_model.startswith(model):
				return pricing

		# Unknown model - return zero pricing
		return ModelPricing()

	@property
	def total_tokens(self) -> int:
		"""Total tokens used (prompt + completion)."""
		return self.total_prompt_tokens + self.total_completion_tokens

	@property
	def error_count(self) -> int:
		"""Number of failed requests."""
		return self.failed_requests

	@property
	def average_latency_ms(self) -> float:
		"""Average latency in milliseconds for successful requests."""
		successful = [r for r in self._requests if r.success]
		if not successful:
			return 0.0
		return sum(r.latency_ms for r in successful) / len(successful)

	@property
	def cost_estimate_usd(self) -> float:
		"""
		Estimated total cost in USD based on token usage and known pricing.

		Note: This is an estimate. Actual costs may vary based on:
		- Cached token pricing
		- Time-based pricing changes
		- Volume discounts
		"""
		total_cost = 0.0

		for request in self._requests:
			if not request.success:
				continue

			pricing = self.get_pricing(request.model)

			# Calculate prompt cost (subtract cached tokens if cached pricing differs)
			prompt_tokens = request.prompt_tokens
			if request.cached_tokens > 0 and pricing.cached_prompt_per_million is not None:
				# Non-cached tokens at full price
				non_cached = prompt_tokens - request.cached_tokens
				prompt_cost = (non_cached / 1_000_000) * pricing.prompt_per_million
				# Cached tokens at cached price
				cached_cost = (request.cached_tokens / 1_000_000) * pricing.cached_prompt_per_million
				total_cost += prompt_cost + cached_cost
			else:
				# All prompt tokens at full price
				total_cost += (prompt_tokens / 1_000_000) * pricing.prompt_per_million

			# Completion cost
			total_cost += (request.completion_tokens / 1_000_000) * pricing.completion_per_million

		return total_cost

	def get_model_breakdown(self) -> dict[str, dict[str, Any]]:
		"""
		Get usage breakdown by model.

		Returns:
			Dict mapping model names to their usage stats
		"""
		breakdown: dict[str, dict[str, Any]] = {}

		for request in self._requests:
			if request.model not in breakdown:
				breakdown[request.model] = {
					'requests': 0,
					'successful': 0,
					'failed': 0,
					'prompt_tokens': 0,
					'completion_tokens': 0,
					'total_latency_ms': 0.0,
					'cost_usd': 0.0,
				}

			stats = breakdown[request.model]
			stats['requests'] += 1

			if request.success:
				stats['successful'] += 1
				stats['prompt_tokens'] += request.prompt_tokens
				stats['completion_tokens'] += request.completion_tokens
				stats['total_latency_ms'] += request.latency_ms

				# Calculate cost for this request
				pricing = self.get_pricing(request.model)
				cost = (request.prompt_tokens / 1_000_000) * pricing.prompt_per_million
				cost += (request.completion_tokens / 1_000_000) * pricing.completion_per_million
				stats['cost_usd'] += cost
			else:
				stats['failed'] += 1

		# Calculate averages
		for model, stats in breakdown.items():
			if stats['successful'] > 0:
				stats['avg_latency_ms'] = stats['total_latency_ms'] / stats['successful']
			else:
				stats['avg_latency_ms'] = 0.0
			del stats['total_latency_ms']

		return breakdown

	def reset(self) -> None:
		"""Reset all metrics to initial state."""
		self._requests.clear()
		self.total_requests = 0
		self.successful_requests = 0
		self.failed_requests = 0
		self.fallback_count = 0
		self.total_prompt_tokens = 0
		self.total_completion_tokens = 0
		self.total_cached_tokens = 0

	def to_dict(self) -> dict[str, Any]:
		"""
		Export metrics as a dictionary.

		Returns:
			Dict with all metric values
		"""
		return {
			'total_requests': self.total_requests,
			'successful_requests': self.successful_requests,
			'failed_requests': self.failed_requests,
			'fallback_count': self.fallback_count,
			'total_prompt_tokens': self.total_prompt_tokens,
			'total_completion_tokens': self.total_completion_tokens,
			'total_tokens': self.total_tokens,
			'total_cached_tokens': self.total_cached_tokens,
			'average_latency_ms': self.average_latency_ms,
			'cost_estimate_usd': self.cost_estimate_usd,
			'model_breakdown': self.get_model_breakdown(),
		}

	def to_prometheus(self) -> str:
		"""
		Export metrics in Prometheus format.

		Returns:
			Prometheus-compatible metrics string
		"""
		lines = [
			'# HELP llm_requests_total Total number of LLM requests',
			'# TYPE llm_requests_total counter',
			f'llm_requests_total {self.total_requests}',
			'',
			'# HELP llm_requests_successful_total Successful LLM requests',
			'# TYPE llm_requests_successful_total counter',
			f'llm_requests_successful_total {self.successful_requests}',
			'',
			'# HELP llm_requests_failed_total Failed LLM requests',
			'# TYPE llm_requests_failed_total counter',
			f'llm_requests_failed_total {self.failed_requests}',
			'',
			'# HELP llm_fallbacks_total Number of model fallbacks',
			'# TYPE llm_fallbacks_total counter',
			f'llm_fallbacks_total {self.fallback_count}',
			'',
			'# HELP llm_tokens_prompt_total Total prompt tokens used',
			'# TYPE llm_tokens_prompt_total counter',
			f'llm_tokens_prompt_total {self.total_prompt_tokens}',
			'',
			'# HELP llm_tokens_completion_total Total completion tokens used',
			'# TYPE llm_tokens_completion_total counter',
			f'llm_tokens_completion_total {self.total_completion_tokens}',
			'',
			'# HELP llm_latency_avg_ms Average request latency in milliseconds',
			'# TYPE llm_latency_avg_ms gauge',
			f'llm_latency_avg_ms {self.average_latency_ms:.2f}',
			'',
			'# HELP llm_cost_usd_total Estimated total cost in USD',
			'# TYPE llm_cost_usd_total counter',
			f'llm_cost_usd_total {self.cost_estimate_usd:.6f}',
		]

		# Add per-model metrics
		for model, stats in self.get_model_breakdown().items():
			safe_model = model.replace('/', '_').replace('-', '_')
			lines.extend([
				'',
				f'# HELP llm_model_requests_total Requests for model {model}',
				f'# TYPE llm_model_requests_total counter',
				f'llm_model_requests_total{{model="{model}"}} {stats["requests"]}',
			])

		return '\n'.join(lines)
