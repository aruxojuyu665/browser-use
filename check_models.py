"""
Check which models from the user's list exist on OpenRouter
"""
import json
import os
from pathlib import Path

# User's requested models
requested_models = [
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

# Load available models from OpenRouter
with open('openrouter_models.json', 'r', encoding='utf-8') as f:
	data = json.load(f)

available_models = {model['id']: model for model in data['data']}

print("=" * 80)
print("MODEL AVAILABILITY CHECK")
print("=" * 80)
print()

# Check each requested model
found_models = []
not_found_models = []
similar_models = {}

for requested in requested_models:
	if requested in available_models:
		model_info = available_models[requested]
		found_models.append(requested)
		print(f"[OK] FOUND: {requested}")
		print(f"   Name: {model_info['name']}")
		print(f"   Context: {model_info['context_length']:,}")
		pricing = model_info['pricing']
		print(f"   Pricing: ${pricing['prompt']}/1K prompt, ${pricing['completion']}/1K completion")
		print()
	else:
		not_found_models.append(requested)
		print(f"[X] NOT FOUND: {requested}")

		# Try to find similar models
		base_name = requested.split('/')[0] if '/' in requested else requested
		similar = [
			model_id for model_id in available_models.keys()
			if base_name.lower() in model_id.lower()
		]
		if similar:
			similar_models[requested] = similar[:3]  # Top 3 similar
			print(f"   Similar models found:")
			for sim in similar[:3]:
				print(f"     • {sim}")
		print()

print("=" * 80)
print(f"SUMMARY: {len(found_models)}/{len(requested_models)} models found")
print("=" * 80)
print()

if found_models:
	print(f"[OK] AVAILABLE ({len(found_models)}):")
	for model in found_models:
		print(f"  - {model}")
	print()

if not_found_models:
	print(f"[X] NOT AVAILABLE ({len(not_found_models)}):")
	for model in not_found_models:
		print(f"  - {model}")
		if model in similar_models:
			print(f"    Alternatives: {', '.join(similar_models[model][:2])}")
	print()

# Suggest top models for testing
print("=" * 80)
print("RECOMMENDED MODELS FOR TESTING (Top tier, actually available):")
print("=" * 80)
print()

# Filter for top models that support function calling
top_models = []
for model_id, model_info in available_models.items():
	if (
		('tool_choice' in model_info.get('supported_parameters', []) or
		 'tools' in model_info.get('supported_parameters', [])) and
		(
			'anthropic' in model_id.lower() or
			'openai' in model_id.lower() or
			'google' in model_id.lower() or
			'x-ai' in model_id.lower() or
			'amazon/nova' in model_id.lower() or
			'qwen' in model_id.lower() or
			'meta-llama' in model_id.lower()
		)
	):
		pricing = model_info['pricing']
		# Calculate average price
		if pricing['prompt'] != "0" and pricing['completion'] != "0":
			avg_price = (float(pricing['prompt']) + float(pricing['completion'])) / 2
		else:
			avg_price = 0

		top_models.append({
			'id': model_id,
			'name': model_info['name'],
			'context': model_info['context_length'],
			'avg_price': avg_price,
		})

# Sort by quality indicators (context length and reasonable pricing)
top_models_sorted = sorted(
	top_models,
	key=lambda x: (x['context'] > 100000, -x['avg_price'] if x['avg_price'] > 0 else 0),
	reverse=True
)[:15]

for i, model in enumerate(top_models_sorted, 1):
	price_str = f"${model['avg_price']:.6f}/1K" if model['avg_price'] > 0 else "FREE"
	print(f"{i:2d}. {model['id']}")
	print(f"    {model['name']}")
	print(f"    Context: {model['context']:,} | Price: {price_str}")
	print()
