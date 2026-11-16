"""Per-turn input limit; Qwen settings never inherit Gemini budgets."""
def input_budget(config):
    if getattr(config, 'leny_llm_provider', 'ollama') == 'gemini':
        return config.leny_gemini_input_token_budget
    return config.leny_num_ctx-config.leny_num_predict-256
