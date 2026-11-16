"""Fixed provider registry; no dynamic imports from input or automatic failover."""
from app.services.leny_llm_contracts import ChatProvider, LenyError


def create_provider(config) -> ChatProvider:
    if config.leny_llm_provider == 'ollama':
        from app.services.leny_ollama import OllamaProvider
        return OllamaProvider(config)
    if config.leny_llm_provider == 'gemini':
        from app.services.leny_gemini import GeminiProvider
        return GeminiProvider(config)
    raise LenyError('LENY_PROVIDER_INVALID', 'El proveedor de LENY no está permitido.', 503)
