"""
Deep Search Testing Script for browser-use 0.0.4 with OpenRouter API

This script tests the deep research capabilities of browser-use agent
using OpenRouter API (Claude 3.5 Sonnet) with new 0.0.4 features:
- Automatic Model Fallback
- LLM Metrics Tracking
- Cost Estimation
- Provider Detection

Testing scenarios from 25_prompts_testing.md
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


class TestResult:
	"""Container for test results"""
	def __init__(self, test_name: str, query: str):
		self.test_name = test_name
		self.query = query
		self.start_time = time.time()
		self.end_time = None
		self.success = False
		self.steps = 0
		self.result = None
		self.error = None
		self.metrics = {}

	def finish(self, success: bool, result: str | None = None, error: str | None = None):
		"""Mark test as finished"""
		self.end_time = time.time()
		self.success = success
		self.result = result
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
			'test_name': self.test_name,
			'query': self.query,
			'duration_sec': round(self.duration, 2),
			'success': self.success,
			'steps': self.steps,
			'result': self.result,
			'error': self.error,
			'metrics': self.metrics,
		}


async def test_openrouter_docs_search():
	"""
	Test #6: OpenRouter Documentation Search
	Complexity: Medium
	Expected steps: 3-5
	"""
	test_name = "Test #6: OpenRouter Documentation"
	query = """
	Find information about OpenRouter's web search capabilities.
	Look for:
	1. How to enable web search (online models)
	2. Pricing for web search
	3. Difference between native and Exa search

	Provide a brief summary with links to the documentation.
	"""

	logger.info(f"Starting {test_name}")
	test = TestResult(test_name, query)

	try:
		# Initialize ChatOpenRouter with 0.0.4 features
		llm = ChatOpenRouter(
			model='anthropic/claude-3.5-sonnet',
			fallback_models=[
				'openai/gpt-4o',
				'google/gemini-2.0-flash-exp:free',
			],
			track_metrics=True,
			on_fallback=lambda from_m, to_m, err: logger.warning(
				f"Fallback: {from_m} -> {to_m} (reason: {err})"
			),
			api_key=os.getenv('OPENROUTER_API_KEY'),
		)

		# Create agent
		agent = Agent(
			task=query,
			llm=llm,
			max_steps=10,  # Limit steps for testing
			use_vision=False,
		)

		# Run agent
		result = await agent.run()

		# Collect metrics
		metrics = llm.get_metrics()
		if metrics:
			test.metrics = {
				'total_requests': metrics.total_requests,
				'successful_requests': metrics.successful_requests,
				'failed_requests': metrics.failed_requests,
				'fallback_count': metrics.fallback_count,
				'total_tokens': metrics.total_tokens,
				'cost_usd': round(metrics.cost_estimate_usd, 6),
				'average_latency_ms': round(metrics.average_latency_ms, 2),
				'active_model': llm.active_model,
			}

		test.steps = len(agent.history.history) if hasattr(agent, 'history') else 0
		test.finish(success=True, result=str(result))

		logger.info(f"{test_name} completed successfully")
		logger.info(f"Duration: {test.duration:.2f}s, Steps: {test.steps}")
		if metrics:
			logger.info(f"Tokens: {metrics.total_tokens}, Cost: ${metrics.cost_estimate_usd:.6f}")

	except Exception as e:
		logger.error(f"{test_name} failed: {e}", exc_info=True)
		test.finish(success=False, error=str(e))

	return test


async def test_simplified_search():
	"""
	Simplified Test: Just check OpenRouter connectivity and basic search
	This is a quick sanity check before running full deep search tests
	"""
	test_name = "Simplified Test: Basic Search"
	query = "Search for 'OpenRouter API documentation' and return the first result URL"

	logger.info(f"Starting {test_name}")
	test = TestResult(test_name, query)

	try:
		llm = ChatOpenRouter(
			model='anthropic/claude-3.5-sonnet',
			fallback_models=['openai/gpt-4o'],
			track_metrics=True,
			api_key=os.getenv('OPENROUTER_API_KEY'),
		)

		agent = Agent(
			task=query,
			llm=llm,
			max_steps=5,
			use_vision=False,
		)

		result = await agent.run()

		# Collect metrics
		metrics = llm.get_metrics()
		if metrics:
			test.metrics = {
				'total_tokens': metrics.total_tokens,
				'cost_usd': round(metrics.cost_estimate_usd, 6),
				'active_model': llm.active_model,
			}

		test.steps = len(agent.history.history) if hasattr(agent, 'history') else 0
		test.finish(success=True, result=str(result))

		logger.info(f"{test_name} completed")
		logger.info(f"Duration: {test.duration:.2f}s, Steps: {test.steps}")

	except Exception as e:
		logger.error(f"{test_name} failed: {e}", exc_info=True)
		test.finish(success=False, error=str(e))

	return test


async def main():
	"""Run deep search tests"""
	logger.info("=" * 80)
	logger.info("Deep Search Testing - browser-use 0.0.4 + OpenRouter API")
	logger.info("=" * 80)

	results = []

	# Test 1: Simplified search (quick sanity check)
	logger.info("\n" + "=" * 80)
	result1 = await test_simplified_search()
	results.append(result1)

	# Test 2: OpenRouter documentation search (if simplified test passed)
	if result1.success:
		logger.info("\n" + "=" * 80)
		result2 = await test_openrouter_docs_search()
		results.append(result2)
	else:
		logger.warning("Skipping OpenRouter docs test due to simplified test failure")

	# Print summary
	logger.info("\n" + "=" * 80)
	logger.info("TEST SUMMARY")
	logger.info("=" * 80)

	for result in results:
		status = "✓ PASS" if result.success else "✗ FAIL"
		logger.info(f"{status}: {result.test_name}")
		logger.info(f"  Duration: {result.duration:.2f}s")
		logger.info(f"  Steps: {result.steps}")
		if result.metrics:
			logger.info(f"  Tokens: {result.metrics.get('total_tokens', 'N/A')}")
			logger.info(f"  Cost: ${result.metrics.get('cost_usd', 0):.6f}")
		if result.error:
			logger.info(f"  Error: {result.error}")
		logger.info("")

	# Save results to file
	output_dir = Path('userdocs/test_results')
	output_dir.mkdir(parents=True, exist_ok=True)

	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	output_file = output_dir / f'deep_search_test_{timestamp}.json'

	with open(output_file, 'w', encoding='utf-8') as f:
		json.dump(
			{
				'timestamp': timestamp,
				'version': '0.0.4',
				'provider': 'OpenRouter',
				'results': [r.to_dict() for r in results],
			},
			f,
			indent=2,
			ensure_ascii=False,
		)

	logger.info(f"Results saved to: {output_file}")

	# Calculate totals
	total_tests = len(results)
	passed = sum(1 for r in results if r.success)
	total_duration = sum(r.duration for r in results)
	total_cost = sum(r.metrics.get('cost_usd', 0) for r in results if r.metrics)

	logger.info("=" * 80)
	logger.info(f"Total: {passed}/{total_tests} tests passed")
	logger.info(f"Total duration: {total_duration:.2f}s")
	logger.info(f"Total cost: ${total_cost:.6f}")
	logger.info("=" * 80)


if __name__ == '__main__':
	asyncio.run(main())
