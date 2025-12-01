"""
Простой тест для проверки исправления JSON Schema с Anthropic через OpenRouter.
"""

import asyncio
import os
from dotenv import load_dotenv

from browser_use import Agent, BrowserProfile, BrowserSession
from browser_use.llm import ChatOpenRouter

load_dotenv(override=True)

# Claude 4.5 Sonnet через OpenRouter с автодетекцией
llm = ChatOpenRouter(
	model='anthropic/claude-4.5-sonnet-20250929',
	api_key=os.getenv('OPENROUTER_API_KEY'),
	http_referer='https://browser-use.com',
	temperature=0.7,
)

print(f"Model: {llm.model}")
print(f"Anthropic auto-detect: {llm._is_anthropic_model()}")
print(f"Anthropic compatible mode: {llm.anthropic_compatible_mode}")
print("-" * 50)

browser_profile = BrowserProfile(
	enable_default_extensions=False,
	headless=False,
)

browser_session = BrowserSession(browser_profile=browser_profile)

# Простая задача для быстрого теста
SIMPLE_TASK = "Go to google.com and find the search box"

agent = Agent(
	task=SIMPLE_TASK,
	llm=llm,
	browser_session=browser_session,
	use_vision=True,
	max_actions_per_step=3,
)


async def main():
	print(f"Task: {SIMPLE_TASK}")
	print("Starting agent...")
	print("=" * 50)

	try:
		result = await agent.run(max_steps=3)

		print("\n" + "=" * 50)
		print("RESULT:")
		print("=" * 50)
		if result and result.final_result():
			print(result.final_result())
		else:
			print("No result")

		print("\nSUCCESS! No JSON Schema errors!")

	except Exception as e:
		print(f"\nERROR: {e}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())
