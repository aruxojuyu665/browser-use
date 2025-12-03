"""
Multi-Model Deep Search Testing Script

Tests 18 different models on OpenRouter with the same deep search task.
Collects comprehensive metrics and creates a comparison report.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm import ChatOpenRouter

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test query - deep search task
TEST_QUERY = """
Собери сравнительный обзор последних новостей о развитии open-source браузерных агентов
(AutoGPT, browser-use, CrewAI и др.) за последние 3 месяца и сделай краткую сводку
с ссылками на первоисточники.
"""

# Models to test (all 18 from user's list)
MODELS_TO_TEST = [
	"x-ai/grok-4.1-fast:free",
	"google/gemini-3-pro-preview",
	"moonshotai/kimi-linear-48b-a3b-instruct",
	"google/gemini-2.5-flash",
	"google/gemini-2.5-pro",
	"meta-llama/llama-4-maverick",
	"openai/gpt-4.1",
	"openai/gpt-4.1-mini",
	"minimax/minimax-01",
	"amazon/nova-2-lite-v1:free",
	"amazon/nova-premier-v1",
	"anthropic/claude-sonnet-4.5",
	"qwen/qwen-plus-2025-07-28:thinking",
	"openai/gpt-5.1",
	"openai/gpt-5-pro",
	"amazon/nova-pro-v1",
	"anthropic/claude-opus-4.5",
	"anthropic/claude-haiku-4.5",
]


class ModelTestResult:
	"""Container for model test results"""
	def __init__(self, model_name: str):
		self.model_name = model_name
		self.start_time = time.time()
		self.end_time = None
		self.success = False
		self.steps = 0
		self.result_text = None
		self.error = None
		self.metrics = {}
		self.fallback_used = False
		self.active_model = model_name

	def finish(self, success: bool, result: str = None, error: str = None):
		"""Mark test as finished"""
		self.end_time = time.time()
		self.success = success
		self.result_text = result
		self.error = error

	@property
	def duration(self) -> float:
		"""Duration in seconds"""
		if self.end_time:
			return self.end_time - self.start_time
		return time.time() - self.start_time

	def to_dict(self) -> dict:
		"""Convert to dictionary"""
		return {
			'model_name': self.model_name,
			'active_model': self.active_model,
			'duration_sec': round(self.duration, 2),
			'success': self.success,
			'steps': self.steps,
			'fallback_used': self.fallback_used,
			'result_preview': self.result_text[:500] if self.result_text else None,
			'error': self.error,
			'metrics': self.metrics,
		}


async def test_model(model_name: str, test_number: int, total_tests: int) -> ModelTestResult:
	"""
	Test a single model with the deep search query

	Args:
		model_name: OpenRouter model identifier
		test_number: Current test number (1-based)
		total_tests: Total number of tests

	Returns:
		ModelTestResult with test results and metrics
	"""
	logger.info("=" * 80)
	logger.info(f"TEST {test_number}/{total_tests}: {model_name}")
	logger.info("=" * 80)

	result = ModelTestResult(model_name)

	try:
		# Create ChatOpenRouter with metrics tracking
		llm = ChatOpenRouter(
			model=model_name,
			# No fallback - we want to test each model individually
			fallback_models=[],
			track_metrics=True,
			api_key=os.getenv('OPENROUTER_API_KEY'),
		)

		# Create agent with limited steps (to control cost)
		agent = Agent(
			task=TEST_QUERY,
			llm=llm,
			max_steps=15,  # Limit steps to control cost
			use_vision=False,
		)

		# Run agent
		logger.info(f"Starting agent for {model_name}...")
		agent_result = await agent.run()

		# Collect metrics
		metrics = llm.get_metrics()
		if metrics:
			result.metrics = {
				'total_requests': metrics.total_requests,
				'successful_requests': metrics.successful_requests,
				'failed_requests': metrics.failed_requests,
				'fallback_count': metrics.fallback_count,
				'total_tokens': metrics.total_tokens,
				'prompt_tokens': metrics.total_prompt_tokens,
				'completion_tokens': metrics.total_completion_tokens,
				'cost_usd': round(metrics.cost_estimate_usd, 6),
				'average_latency_ms': round(metrics.average_latency_ms, 2),
			}
			result.fallback_used = metrics.fallback_count > 0

		result.active_model = llm.active_model or model_name
		result.steps = len(agent.history.history) if hasattr(agent, 'history') else 0
		result.finish(success=True, result=str(agent_result))

		logger.info(f"[SUCCESS] {model_name}")
		logger.info(f"  Duration: {result.duration:.2f}s")
		logger.info(f"  Steps: {result.steps}")
		if metrics:
			logger.info(f"  Tokens: {metrics.total_tokens}")
			logger.info(f"  Cost: ${metrics.cost_estimate_usd:.6f}")

	except Exception as e:
		logger.error(f"[FAILED] {model_name}: {e}")
		result.finish(success=False, error=str(e))

	return result


async def main():
	"""Run multi-model testing"""
	logger.info("=" * 80)
	logger.info("MULTI-MODEL DEEP SEARCH TESTING")
	logger.info("=" * 80)
	logger.info(f"Testing {len(MODELS_TO_TEST)} models")
	logger.info(f"Query: {TEST_QUERY.strip()}")
	logger.info("=" * 80)
	logger.info("")

	results = []
	start_time = time.time()

	# Test each model sequentially
	for i, model_name in enumerate(MODELS_TO_TEST, 1):
		result = await test_model(model_name, i, len(MODELS_TO_TEST))
		results.append(result)

		# Save intermediate results after each test
		save_results(results, partial=True)

		# Small delay between tests
		await asyncio.sleep(2)

	total_duration = time.time() - start_time

	# Print summary
	logger.info("")
	logger.info("=" * 80)
	logger.info("TESTING COMPLETE")
	logger.info("=" * 80)
	logger.info(f"Total duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)")
	logger.info(f"Tests passed: {sum(1 for r in results if r.success)}/{len(results)}")
	logger.info("")

	# Print detailed summary
	print_summary(results)

	# Save final results
	save_results(results, partial=False)

	logger.info("=" * 80)
	logger.info("Results saved to userdocs/test_results/")
	logger.info("=" * 80)


def print_summary(results: list[ModelTestResult]):
	"""Print summary table of results"""
	logger.info("=" * 80)
	logger.info("RESULTS SUMMARY")
	logger.info("=" * 80)
	logger.info("")

	# Success rate
	successful = [r for r in results if r.success]
	failed = [r for r in results if not r.success]

	logger.info(f"Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
	logger.info("")

	# Successful tests
	if successful:
		logger.info("SUCCESSFUL TESTS:")
		logger.info("-" * 80)
		for r in successful:
			logger.info(f"  {r.model_name}")
			logger.info(f"    Duration: {r.duration:.2f}s | Steps: {r.steps}")
			if r.metrics:
				cost = r.metrics.get('cost_usd', 0)
				tokens = r.metrics.get('total_tokens', 0)
				logger.info(f"    Tokens: {tokens:,} | Cost: ${cost:.6f}")
			logger.info("")

	# Failed tests
	if failed:
		logger.info("FAILED TESTS:")
		logger.info("-" * 80)
		for r in failed:
			logger.info(f"  {r.model_name}")
			logger.info(f"    Error: {r.error}")
			logger.info("")

	# Cost summary
	total_cost = sum(r.metrics.get('cost_usd', 0) for r in results if r.metrics)
	total_tokens = sum(r.metrics.get('total_tokens', 0) for r in results if r.metrics)
	avg_duration = sum(r.duration for r in successful) / len(successful) if successful else 0

	logger.info("TOTALS:")
	logger.info("-" * 80)
	logger.info(f"  Total Cost: ${total_cost:.6f}")
	logger.info(f"  Total Tokens: {total_tokens:,}")
	logger.info(f"  Average Duration: {avg_duration:.2f}s")
	logger.info("")


def save_results(results: list[ModelTestResult], partial: bool = False):
	"""Save results to JSON file"""
	output_dir = Path('userdocs/test_results')
	output_dir.mkdir(parents=True, exist_ok=True)

	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	suffix = '_partial' if partial else '_final'
	output_file = output_dir / f'multi_model_test_{timestamp}{suffix}.json'

	# Prepare data
	data = {
		'timestamp': timestamp,
		'version': '0.0.4',
		'provider': 'OpenRouter',
		'query': TEST_QUERY.strip(),
		'total_tests': len(results),
		'successful_tests': sum(1 for r in results if r.success),
		'failed_tests': sum(1 for r in results if not r.success),
		'total_cost_usd': sum(r.metrics.get('cost_usd', 0) for r in results if r.metrics),
		'total_tokens': sum(r.metrics.get('total_tokens', 0) for r in results if r.metrics),
		'results': [r.to_dict() for r in results],
	}

	with open(output_file, 'w', encoding='utf-8') as f:
		json.dump(data, f, indent=2, ensure_ascii=False)

	logger.info(f"Results saved to: {output_file}")


if __name__ == '__main__':
	asyncio.run(main())
