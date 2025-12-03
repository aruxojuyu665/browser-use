"""
Testing basic OpenRouter API functionality with new features from version 0.0.4.

Tests:
1. Basic OpenRouter API connection
2. Automatic Model Fallback
3. LLM Metrics Tracking
4. Cost Estimation
5. Metrics Export
"""

import asyncio
import os
import json
from dotenv import load_dotenv

from browser_use.llm import ChatOpenRouter, UserMessage, SystemMessage

load_dotenv(override=True)  # Force reload from .env file


async def test_basic_connection():
	"""Test 1: Basic OpenRouter API connection"""
	print("=" * 80)
	print("TEST 1: Basic OpenRouter API connection")
	print("=" * 80)

	llm = ChatOpenRouter(
		model='anthropic/claude-3.5-sonnet',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		track_metrics=True,
	)

	messages = [
		SystemMessage(content="You are a helpful assistant."),
		UserMessage(content="Say 'Hello, OpenRouter!' in one sentence."),
	]

	try:
		result = await llm.ainvoke(messages)
		print(f"[PASS] Connection successful!")
		print(f"  Model: {llm.active_model}")
		print(f"  Response: {result.completion}")
		print(f"  Tokens: {result.usage.total_tokens if result.usage else 'N/A'}")
		return True
	except Exception as e:
		print(f"[FAIL] Connection error: {e}")
		return False


async def test_automatic_fallback():
	"""Test 2: Automatic Model Fallback"""
	print("\n" + "=" * 80)
	print("TEST 2: Automatic Model Fallback")
	print("=" * 80)

	fallback_calls = []

	def on_fallback(from_model, to_model, error):
		fallback_calls.append({
			'from': from_model,
			'to': to_model,
			'error': str(error)
		})
		print(f"  -> Fallback: {from_model} -> {to_model}")

	llm = ChatOpenRouter(
		model='anthropic/claude-3.5-sonnet',
		fallback_models=[
			'openai/gpt-4o',
			'google/gemini-2.0-flash-exp:free',
		],
		api_key=os.getenv('OPENROUTER_API_KEY'),
		on_fallback=on_fallback,
		track_metrics=True,
	)

	messages = [
		UserMessage(content="What is 2+2? Answer in one word."),
	]

	try:
		result = await llm.ainvoke(messages)
		print(f"[PASS] Request completed successfully")
		print(f"  Active model: {llm.active_model}")
		print(f"  Fallback count: {len(fallback_calls)}")
		print(f"  Response: {result.completion}")
		return True
	except Exception as e:
		print(f"[FAIL] Error: {e}")
		print(f"  Fallback attempts: {len(fallback_calls)}")
		return False


async def test_metrics_tracking():
	"""Test 3: LLM Metrics Tracking"""
	print("\n" + "=" * 80)
	print("TEST 3: LLM Metrics Tracking")
	print("=" * 80)

	llm = ChatOpenRouter(
		model='anthropic/claude-3.5-sonnet',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		track_metrics=True,
	)

	# Multiple requests
	test_messages = [
		[UserMessage(content="What is the capital of France?")],
		[UserMessage(content="What is 5+7?")],
		[UserMessage(content="Name a color.")],
	]

	try:
		for i, messages in enumerate(test_messages, 1):
			result = await llm.ainvoke(messages)
			print(f"  Request {i}: {result.usage.total_tokens if result.usage else 0} tokens")

		# Get metrics
		metrics = llm.get_metrics()
		if metrics:
			print(f"\n[PASS] Metrics collected successfully:")
			print(f"  Total requests: {metrics.total_requests}")
			print(f"  Successful: {metrics.successful_requests}")
			print(f"  Failed: {metrics.failed_requests}")
			print(f"  Total tokens: {metrics.total_tokens}")
			print(f"  Avg latency: {metrics.average_latency_ms:.2f} ms")

			# Model breakdown
			breakdown = metrics.get_model_breakdown()
			print(f"\n  Model breakdown:")
			for model, stats in breakdown.items():
				print(f"    {model}:")
				print(f"      Requests: {stats['requests']}")
				print(f"      Tokens: {stats['prompt_tokens'] + stats['completion_tokens']}")

			return True
		else:
			print("[FAIL] Metrics were not collected")
			return False

	except Exception as e:
		print(f"[FAIL] Error: {e}")
		return False


async def test_cost_estimation():
	"""Test 4: Cost Estimation"""
	print("\n" + "=" * 80)
	print("TEST 4: Cost Estimation")
	print("=" * 80)

	llm = ChatOpenRouter(
		model='anthropic/claude-3.5-sonnet',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		track_metrics=True,
	)

	messages = [
		UserMessage(content="Write a 3-sentence story about a robot."),
	]

	try:
		result = await llm.ainvoke(messages)
		cost = llm.get_estimated_cost()

		print(f"[PASS] Cost estimation completed:")
		print(f"  Response: {result.completion}")
		print(f"  Tokens: {result.usage.total_tokens if result.usage else 0}")
		print(f"  Estimated cost: ${cost:.6f}")

		return True
	except Exception as e:
		print(f"[FAIL] Error: {e}")
		return False


async def test_metrics_export():
	"""Test 5: Metrics Export"""
	print("\n" + "=" * 80)
	print("TEST 5: Metrics Export")
	print("=" * 80)

	llm = ChatOpenRouter(
		model='anthropic/claude-3.5-sonnet',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		track_metrics=True,
	)

	messages = [
		UserMessage(content="Say hello."),
	]

	try:
		await llm.ainvoke(messages)

		metrics = llm.get_metrics()
		if metrics:
			# Export to dict
			metrics_dict = metrics.to_dict()
			print(f"[PASS] Export to dict completed:")
			print(f"  Structure: {list(metrics_dict.keys())}")

			# Export to Prometheus
			prometheus_format = metrics.to_prometheus()
			print(f"\n[PASS] Export to Prometheus completed:")
			print(f"  Output size: {len(prometheus_format)} characters")
			print(f"  First 200 characters:")
			print(f"  {prometheus_format[:200]}...")

			# Save for report
			with open('userdocs/metrics_export_sample.json', 'w', encoding='utf-8') as f:
				json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
			print(f"\n  Metrics saved to userdocs/metrics_export_sample.json")

			return True
		else:
			print("[FAIL] Metrics were not collected")
			return False

	except Exception as e:
		print(f"[FAIL] Error: {e}")
		return False


async def test_provider_detection():
	"""Test 6: Provider Detection for different models"""
	print("\n" + "=" * 80)
	print("TEST 6: Provider Detection")
	print("=" * 80)

	test_models = [
		'anthropic/claude-3.5-sonnet',
		'openai/gpt-4o',
		'google/gemini-2.0-flash-exp:free',
	]

	results = []

	for model_name in test_models:
		try:
			llm = ChatOpenRouter(
				model=model_name,
				api_key=os.getenv('OPENROUTER_API_KEY'),
				track_metrics=True,
			)

			provider_type = llm._get_provider_type()

			messages = [UserMessage(content="Say 'test' in one word.")]
			result = await llm.ainvoke(messages)

			results.append({
				'model': model_name,
				'provider': provider_type.value,
				'success': True,
				'tokens': result.usage.total_tokens if result.usage else 0
			})

			print(f"  [PASS] {model_name}")
			print(f"    Provider: {provider_type.value}")
			print(f"    Tokens: {result.usage.total_tokens if result.usage else 0}")

		except Exception as e:
			results.append({
				'model': model_name,
				'provider': 'unknown',
				'success': False,
				'error': str(e)
			})
			print(f"  [FAIL] {model_name}: {e}")

	successful = sum(1 for r in results if r['success'])
	print(f"\n  Successfully tested: {successful}/{len(test_models)}")

	return successful > 0


async def main():
	"""Run all tests"""
	print("\n" + "=" * 80)
	print("TESTING BROWSER-USE 0.0.4 WITH OPENROUTER API")
	print("=" * 80)

	results = {
		'Basic Connection': await test_basic_connection(),
		'Automatic Fallback': await test_automatic_fallback(),
		'Metrics Tracking': await test_metrics_tracking(),
		'Cost Estimation': await test_cost_estimation(),
		'Metrics Export': await test_metrics_export(),
		'Provider Detection': await test_provider_detection(),
	}

	print("\n" + "=" * 80)
	print("FINAL RESULTS")
	print("=" * 80)

	for test_name, result in results.items():
		status = "[PASS]" if result else "[FAIL]"
		print(f"  {status}: {test_name}")

	total = len(results)
	passed = sum(1 for r in results.values() if r)

	print(f"\nTotal: {passed}/{total} tests passed")

	return passed == total


if __name__ == '__main__':
	success = asyncio.run(main())
	exit(0 if success else 1)
