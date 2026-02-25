"""
LLM Client Adapter - Soporte OpenAI y Anthropic para Bruce W

Switcheable via env vars:
  LLM_PROVIDER=openai|anthropic (default: openai)
  LLM_MODEL=gpt-4o-mini|claude-haiku-4-5-20251001 (default: gpt-4o-mini)
  ANTHROPIC_API_KEY=sk-ant-xxx (solo si anthropic)
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Mapeo de modelos "potentes" para retry (FIX 204)
_RETRY_MODEL = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-6",
}


class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.default_model = LLM_MODEL
        self.client = None

        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
                if not api_key:
                    print("[LLM] WARN: ANTHROPIC_API_KEY no configurada, fallback a openai")
                    self.provider = "openai"
                else:
                    self.client = Anthropic(api_key=api_key)
                    print(f"[LLM] Provider: Anthropic, Model: {self.default_model}")
            except ImportError:
                print("[LLM] WARN: anthropic package no instalado, fallback a openai")
                self.provider = "openai"

        if self.provider == "openai":
            # El cliente OpenAI se maneja externamente (openai_client global en agente_ventas.py)
            # Solo registramos el provider
            if self.client is None:
                print(f"[LLM] Provider: OpenAI, Model: {self.default_model}")

    def get_retry_model(self):
        """Retorna el modelo potente para reintentos anti-repeticion"""
        return _RETRY_MODEL.get(self.provider, "gpt-4o")

    def chat_completion(self, messages, openai_client=None, model_override=None,
                        temperature=0.7, max_tokens=150, timeout=4.0,
                        frequency_penalty=0.0, presence_penalty=0.0,
                        top_p=1.0, stream=False):
        """
        Genera respuesta de chat. Compatible con OpenAI y Anthropic.

        Args:
            messages: Lista de dicts [{"role": "system"|"user"|"assistant", "content": "..."}]
            openai_client: Cliente OpenAI (requerido si provider=openai)
            model_override: Modelo especifico (override default)
            temperature, max_tokens, timeout: Parametros estandar
            frequency_penalty, presence_penalty, top_p: Solo OpenAI (ignorados en Anthropic)

        Returns:
            str: Texto de la respuesta
        """
        model = model_override or self.default_model
        inicio = time.time()

        if self.provider == "anthropic":
            result = self._call_anthropic(messages, model, temperature, max_tokens, timeout)
        else:
            result = self._call_openai(messages, openai_client, model, temperature,
                                       max_tokens, timeout, frequency_penalty,
                                       presence_penalty, top_p, stream)

        duracion = time.time() - inicio
        print(f"   [LLM] {self.provider}/{model} -> {len(result)} chars en {duracion:.2f}s")
        return result

    def _call_openai(self, messages, openai_client, model, temperature,
                     max_tokens, timeout, frequency_penalty, presence_penalty,
                     top_p, stream):
        """Llamada directa a OpenAI API"""
        if openai_client is None:
            raise ValueError("[LLM] openai_client requerido para provider=openai")

        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            stream=stream,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, messages, model, temperature, max_tokens, timeout):
        """Llamada a Anthropic API con conversion de formato"""
        # 1. Extraer mensajes system -> parametro system
        system_parts = []
        conv_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                conv_messages.append({"role": msg["role"], "content": msg["content"]})

        system_text = "\n\n".join(system_parts) if system_parts else ""

        # 2. Fusionar mensajes consecutivos del mismo role (requerimiento Anthropic)
        merged = []
        for msg in conv_messages:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1]["content"] += "\n" + msg["content"]
            else:
                merged.append({"role": msg["role"], "content": msg["content"]})

        # 3. Asegurar que el primer mensaje sea user (requerimiento Anthropic)
        if merged and merged[0]["role"] == "assistant":
            merged.insert(0, {"role": "user", "content": "[inicio de conversacion]"})

        # 4. Si no hay mensajes, agregar uno minimo
        if not merged:
            merged = [{"role": "user", "content": "[sin contexto previo]"}]

        # 5. Llamar a Anthropic
        kwargs = {
            "model": model,
            "messages": merged,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        response = self.client.messages.create(**kwargs)
        return response.content[0].text


# Instancia global
llm_client = LLMClient()
