from agents import OpenAIResponsesModel, set_tracing_disabled
from openai import AsyncOpenAI
from runner.config.settings import acme_settings

main_client = AsyncOpenAI(
    base_url = f"{acme_settings.main_endpoint}/openai/v1/",
    api_key = acme_settings.main_api_key,
)

mini_client = AsyncOpenAI(
    base_url = f"{acme_settings.mini_endpoint}/openai/v1/",
    api_key = acme_settings.mini_api_key,
)

def main_model() -> OpenAIResponsesModel:
    set_tracing_disabled(True)
    _main_model = OpenAIResponsesModel(model = acme_settings.main_model_name, openai_client = main_client)
    return _main_model

def mini_model() -> OpenAIResponsesModel:
    set_tracing_disabled(True)
    _mini_model = OpenAIResponsesModel(model = acme_settings.mini_model_name, openai_client = mini_client)
    return _mini_model 

