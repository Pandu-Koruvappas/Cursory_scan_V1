import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from groq import AsyncGroq
from dotenv import load_dotenv

# Load .env from the backend directory specifically
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(dotenv_path=env_path)

from openai import AsyncAzureOpenAI, AsyncOpenAI

AZURE_SERVICES_HOST = "services.ai.azure.com"
AZURE_INFERENCE_HOST = "inference.ml.azure.com"
NVIDIA_DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

class LLMService:
    def __init__(self):

        
        # Configure Primary Azure OpenAI
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_key = os.getenv("OPENAI_CREDENTIAL")
        self.azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini") # High-speed, low-cost
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.azure_client = None
        if self.azure_endpoint and self.azure_key:
            if AZURE_SERVICES_HOST in self.azure_endpoint or AZURE_INFERENCE_HOST in self.azure_endpoint:
                base_url = self.azure_endpoint.rstrip('/')
                if not base_url.endswith('/v1'):
                    base_url = f"{base_url}/v1"
                self.azure_client = AsyncOpenAI(
                    base_url=base_url,
                    api_key=self.azure_key,
                    timeout=120.0
                )
            else:
                self.azure_client = AsyncAzureOpenAI(
                    azure_endpoint=self.azure_endpoint,
                    api_key=self.azure_key,
                    api_version=self.azure_api_version,
                    timeout=120.0
                )

        # Configure Secondary / Fallback Azure OpenAI (Supports AZURE_OPENAI_*_2 and OPENAI_*)
        self.azure_endpoint_2 = os.getenv("AZURE_OPENAI_ENDPOINT_2") or os.getenv("OPENAI_ENDPOINT") or self.azure_endpoint
        self.azure_key_2 = os.getenv("OPENAI_CREDENTIAL_2") or os.getenv("OPENAI_CREDENTIAL") or self.azure_key
        self.azure_deployment_2 = os.getenv("AZURE_OPENAI_DEPLOYMENT_2") or os.getenv("OPENAI_DEPLOYMENT")
        self.azure_api_version_2 = os.getenv("AZURE_OPENAI_VERSION_2") or os.getenv("AZURE_OPENAI_API_VERSION_2") or os.getenv("OPENAI_API_VERSION") or "2025-08-07"
        
        self.azure_client_2 = None
        if self.azure_endpoint_2 and self.azure_key_2 and self.azure_deployment_2:
            # print(f" [LLMService] Secondary Azure OpenAI Deployment configured: '{self.azure_deployment_2}' at endpoint '{self.azure_endpoint_2}' (Version: {self.azure_api_version_2})")
            if AZURE_SERVICES_HOST in self.azure_endpoint_2 or AZURE_INFERENCE_HOST in self.azure_endpoint_2:
                base_url = self.azure_endpoint_2.rstrip('/')
                if base_url.endswith('/responses'):
                    base_url = base_url[:-10].rstrip('/')
                if not base_url.endswith('/v1'):
                    base_url = f"{base_url}/v1"
                self.azure_client_2 = AsyncOpenAI(
                    base_url=base_url,
                    api_key=self.azure_key_2,
                    timeout=120.0
                )
            else:
                self.azure_client_2 = AsyncAzureOpenAI(
                    azure_endpoint=self.azure_endpoint_2,
                    api_key=self.azure_key_2,
                    api_version=self.azure_api_version_2,
                    timeout=120.0
                )
            
        # Configure Azure OpenAI Embeddings
        self.azure_embedding_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
        self.azure_embedding_key = os.getenv("EMBEDDING_CREDENTIAL", self.azure_key)
        self.azure_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        self.azure_embedding_client = None
        if self.azure_embedding_endpoint and self.azure_embedding_key:
            self.azure_embedding_client = AsyncAzureOpenAI(
                azure_endpoint=self.azure_embedding_endpoint,
                api_key=self.azure_embedding_key,
                api_version="2024-02-15-preview",
                timeout=60.0
            )

        # Legacy alias for fallback client compatibility
        self.azure_fallback_client = self.azure_client_2 or self.azure_client
        self.azure_fallback_deployment = self.azure_deployment_2 or self.azure_deployment

        # Configure Kimi-K2.6
        self.kimi_endpoint = os.getenv("KIMI_OPENAI_ENDPOINT")
        self.kimi_key = os.getenv("KIMI_CREDENTIAL")
        self.kimi_deployment = os.getenv("KIMI_OPENAI_DEPLOYMENT", "Kimi-K2.6")
        self.kimi_client = None
        if self.kimi_endpoint and self.kimi_key:
            if "services.ai.azure.com" in self.kimi_endpoint or "inference.ml.azure.com" in self.kimi_endpoint:
                base_url = self.kimi_endpoint.rstrip('/')
                if not base_url.endswith('/v1'):
                    base_url = f"{base_url}/v1"
                self.kimi_client = AsyncOpenAI(
                    base_url=base_url,
                    api_key=self.kimi_key,
                    timeout=120.0
                )
            else:
                self.kimi_client = AsyncAzureOpenAI(
                    azure_endpoint=self.kimi_endpoint,
                    api_key=self.kimi_key,
                    api_version="2025-01-01-preview",
                    timeout=120.0
                )

        # Configure Groq with Rotation
        self.groq_keys = self._discover_keys("GROQ_CREDENTIAL")
        self.groq_index = 0
        self.groq_clients = [AsyncGroq(api_key=k, timeout=120.0) for k in self.groq_keys]
        self.groq_model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _discover_keys(self, prefix: str) -> list:
        keys = []
        base_key = os.getenv(prefix)
        if base_key: keys.append(base_key)
        for i in range(1, 11):
            indexed_key = os.getenv(f"{prefix}_{i}")
            if indexed_key: keys.append(indexed_key)
        return list(set(keys)) if keys else ["missing_key"]

    def _get_next_groq_client(self):
        if not self.groq_clients: return None
        client = self.groq_clients[self.groq_index % len(self.groq_clients)]
        self.groq_index += 1
        return client



    async def generate_with_groq(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None):
        import time
        from services.telemetry_service import TelemetryService
        
        client = self._get_next_groq_client()
        if not client: return "Groq Error"
        
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        kwargs = {
            "model": self.groq_model_name,
            "messages": messages
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            
        try:
            completion = await client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="groq", model_name=self.groq_model_name,
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message # Return the full message object so the caller can handle tools
                
            return message.content
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="groq", model_name=self.groq_model_name,
                latency_ms=latency, success=False, error_message=str(e)
            )
            return f"Groq Error: {str(e)}"

    async def generate_with_vision(self, image_path: str, prompt: str):
        """
        Uses Azure OpenAI (GPT-4o) to analyze an image (wireframe, whiteboard, etc.) 
        and extract textual descriptions or requirements.
        """
        # print(f"DEBUG: Calling Azure Vision for {image_path}")
        try:
            import base64
            import aiofiles
            async with aiofiles.open(image_path, "rb") as f:
                image_data = base64.b64encode(await f.read()).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]
            response = await self.azure_client.chat.completions.create(
                model=self.azure_deployment,
                messages=messages,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            # print(f"DEBUG: Azure Vision ERROR: {str(e)}")
            return f"Vision Error: {str(e)}"

    async def get_embeddings(self, text: str) -> list:
        """
        Generates semantic embeddings for vector search.
        Uses Gemini's embedding-004 model.
        """
        try:
            if getattr(self, 'azure_embedding_client', None):
                # We need exactly 1536 dims for text-embedding-3-small
                response = await self.azure_embedding_client.embeddings.create(
                    input=text,
                    model=self.azure_embedding_deployment
                )
                vector = response.data[0].embedding
                # If using a newer model like text-embedding-3-large, we might need padding/truncating, 
                # but text-embedding-3-small defaults to 1536. Just in case:
                if len(vector) < 1536:
                    vector = vector + [0.0] * (1536 - len(vector))
                elif len(vector) > 1536:
                    vector = vector[:1536]
                return vector
        except Exception:
            # print(f"DEBUG: Embedding Request ERROR: {e}")
            return [0.0] * 1536

    async def generate_with_azure(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None, response_format: dict = None, temperature: float = None):
        import time
        from services.telemetry_service import TelemetryService
        
        if not self.azure_client: return "Azure Error: Not Configured"
        
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        def _get_model_kwargs(dep_name: str, temp_val: float):
            dep_lower = (dep_name or "").lower()
            is_nextgen = any(k in dep_lower for k in ["gpt-5", "o1", "o3"])
            kw = {
                "model": dep_name,
                "messages": messages,
            }
            if is_nextgen:
                kw["max_completion_tokens"] = 16384
            else:
                kw["max_tokens"] = 16384
                kw["temperature"] = temp_val if temp_val is not None else 0.0
                kw["seed"] = 42
            if response_format:
                kw["response_format"] = response_format
            if tools:
                kw["tools"] = tools
                kw["tool_choice"] = tool_choice
                kw["parallel_tool_calls"] = False
            return kw

        kwargs = _get_model_kwargs(self.azure_deployment, temperature)
            
        try:
            completion = await self.azure_client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="azure", model_name=self.azure_deployment,
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message
                
            return message.content
        except Exception as e:
            err_str = str(e).lower()
            if "max_tokens" in err_str or "unsupported_parameter" in err_str:
                print(f"🔄 [LLMService] Adjusting parameters for '{self.azure_deployment}' (switching to max_completion_tokens)...")
                retry_kw = dict(kwargs)
                if "max_tokens" in retry_kw:
                    val = retry_kw.pop("max_tokens")
                    retry_kw["max_completion_tokens"] = val
                retry_kw.pop("temperature", None)
                retry_kw.pop("seed", None)
                try:
                    completion = await self.azure_client.chat.completions.create(**retry_kw)
                    latency = (time.time() - start_time) * 1000
                    message = completion.choices[0].message
                    usage = completion.usage
                    TelemetryService.log_call(
                        agent_name=agent_name, provider="azure", model_name=self.azure_deployment,
                        latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                        completion_tokens=usage.completion_tokens if usage else 0, success=True
                    )
                    if message.tool_calls:
                        return message
                    return message.content
                except Exception as e_retry:
                    e = e_retry

            print(f"❌ [LLMService ERROR] Primary Azure deployment '{self.azure_deployment}' failed: {e}")
            if self.azure_deployment_2 and self.azure_deployment_2 != self.azure_deployment:
                print(f"🔄 [LLMService] Retrying with secondary deployment '{self.azure_deployment_2}'...")
                try:
                    sec_kwargs = _get_model_kwargs(self.azure_deployment_2, temperature)
                    try:
                        completion = await self.azure_client_2.chat.completions.create(**sec_kwargs)
                    except Exception as e_sec_param:
                        if "max_tokens" in str(e_sec_param).lower() or "unsupported_parameter" in str(e_sec_param).lower():
                            sec_kwargs.pop("max_tokens", None)
                            sec_kwargs["max_completion_tokens"] = 16384
                            sec_kwargs.pop("temperature", None)
                            sec_kwargs.pop("seed", None)
                            completion = await self.azure_client_2.chat.completions.create(**sec_kwargs)
                        else:
                            raise e_sec_param

                    latency = (time.time() - start_time) * 1000
                    message = completion.choices[0].message
                    usage = completion.usage
                    TelemetryService.log_call(
                        agent_name=agent_name, provider="azure_deployment_2", model_name=self.azure_deployment_2,
                        latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                        completion_tokens=usage.completion_tokens if usage else 0, success=True
                    )
                    if message.tool_calls:
                        return message
                    return message.content
                except Exception as e2:
                    print(f"❌ [LLMService ERROR] Secondary Azure Deployment ALSO failed: {e2}")
                    e = e2

            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="azure", model_name=self.azure_deployment,
                latency_ms=latency, success=False, error_message=str(e)
            )
            return f"Azure Error: {str(e)}"

    async def generate_with_kimi(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None):
        import time
        from services.telemetry_service import TelemetryService
        
        if not self.kimi_client: return "Kimi Error: Not Configured"
        
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        kwargs = {
            "model": self.kimi_deployment,
            "messages": messages,
            "max_tokens": 4096
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            kwargs["parallel_tool_calls"] = False
            
        try:
            completion = await self.kimi_client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="kimi", model_name=self.kimi_deployment,
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message
                
            return message.content
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="kimi", model_name=self.kimi_deployment,
                latency_ms=latency, success=False, error_message=str(e)
            )
            # print(f"DEBUG: Kimi API ERROR: {str(e)}")
            return f"Kimi Error: {str(e)}"

    async def generate_with_azure_fallback(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None):
        import time
        from services.telemetry_service import TelemetryService
        
        if not self.azure_fallback_client: return "Azure Fallback Error: Not Configured"
        
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        kwargs = {
            "model": self.azure_fallback_deployment,
            "messages": messages
        }
        
        dep_lower = (self.azure_fallback_deployment or "").lower()
        is_nextgen = any(k in dep_lower for k in ["gpt-5", "o1", "o3"])
        if is_nextgen:
            kwargs["max_completion_tokens"] = 16384
        else:
            kwargs["max_tokens"] = 4096
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            kwargs["parallel_tool_calls"] = False
            
        try:
            completion = await self.azure_fallback_client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="azure_fallback", model_name=self.azure_fallback_deployment,
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message
                
            return message.content
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="azure_fallback", model_name=self.azure_fallback_deployment,
                latency_ms=latency, success=False, error_message=str(e)
            )
            # print(f"DEBUG: Azure Fallback API ERROR: {str(e)}")
            return f"Azure Fallback Error: {str(e)}"

    async def generate_with_groq(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None):
        import time
        from services.telemetry_service import TelemetryService
        from groq import AsyncGroq
        
        groq_key = os.getenv("GROQ_CREDENTIAL")
        if not groq_key: return "Groq Error: Not Configured"
        
        client = AsyncGroq(api_key=groq_key)
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        kwargs = {
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "messages": messages,
            "max_tokens": 4096
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            
        try:
            completion = await client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="groq", model_name=kwargs["model"],
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message
                
            return message.content
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="groq", model_name=kwargs["model"],
                latency_ms=latency, success=False, error_message=str(e)
            )
            return f"Groq Error: {str(e)}"

    async def generate_with_nvidia(self, prompt: str, agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None):
        import time
        from services.telemetry_service import TelemetryService
        from openai import AsyncOpenAI
        
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        if not nvidia_key: return "NVIDIA Error: Not Configured"
        
        # Standard OpenAI client pointing to NVIDIA API endpoint
        nvidia_client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key,
            timeout=120.0
        )
        
        start_time = time.time()
        
        if not messages:
            messages = [{"role": "user", "content": prompt}]
            
        kwargs = {
            "model": NVIDIA_DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": 8000
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            
        try:
            completion = await nvidia_client.chat.completions.create(**kwargs)
            latency = (time.time() - start_time) * 1000
            
            message = completion.choices[0].message
            usage = completion.usage
            
            TelemetryService.log_call(
                agent_name=agent_name, provider="nvidia", model_name=NVIDIA_DEFAULT_MODEL,
                latency_ms=latency, prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0, success=True
            )
            
            if message.tool_calls:
                return message
                
            return message.content
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            TelemetryService.log_call(
                agent_name=agent_name, provider="nvidia", model_name=NVIDIA_DEFAULT_MODEL,
                latency_ms=latency, success=False, error_message=str(e)
            )
            # print(f"DEBUG: NVIDIA API ERROR: {str(e)}")
            return f"NVIDIA Error: {str(e)}"

    async def call(self, prompt: str, provider: str = "azure_fallback", agent_name: str = "unknown", tools: list = None, tool_choice: str = "auto", messages: list = None, response_format: dict = None, temperature: float = None):
        # Apply PII Guardrails
        from services.guardrail_service import GuardrailService
        guardrail = GuardrailService()
        
        safe_prompt = guardrail.scrub_pii(prompt)
        safe_messages = None
        if messages:
            safe_messages = []
            for m in messages:
                new_m = m.copy()
                if new_m.get("content") and isinstance(new_m["content"], str):
                    new_m["content"] = guardrail.scrub_pii(new_m["content"])
                safe_messages.append(new_m)
                
        if agent_name == "unknown":
            import inspect
            try:
                # Try to get the class name of the caller
                frame = inspect.currentframe().f_back
                if 'self' in frame.f_locals:
                    agent_name = frame.f_locals['self'].__class__.__name__
                else:
                    agent_name = frame.f_code.co_name
            except Exception:
                pass
                
        try:
            if provider == "azure": result = await self.generate_with_azure(safe_prompt, agent_name, tools, tool_choice, safe_messages, response_format, temperature=temperature)
            elif provider == "kimi": result = await self.generate_with_kimi(safe_prompt, agent_name, tools, tool_choice, safe_messages)
            elif provider == "nvidia": result = await self.generate_with_nvidia(safe_prompt, agent_name, tools, tool_choice, safe_messages)
            else: result = await self.generate_with_groq(safe_prompt, agent_name, tools, tool_choice, safe_messages)
        except Exception as e:
            # print(f" [LLMService] Provider '{provider}' crashed with exception: {e}")
            result = f"Error: {str(e)}"
        
        # If a tool call object is returned, don't trigger fallback logic yet.
        if not isinstance(result, str):
            # print(f" [LLMService] Provider '{provider}' returned a tool call.")
            return result
            
        def is_error(res):
            if not res or not isinstance(res, str) or not res.strip():
                return True
            s = res.strip()
            return s.startswith("Azure Error") or s.startswith("Groq Error") or s.startswith("NVIDIA Error") or s.startswith("Vision Error") or s.startswith("Kimi Error") or s.startswith("Azure Fallback Error") or s.startswith("Error:")

        if is_error(result):
            print(f"⚠️ [LLMService WARN] Primary provider '{provider}' failed with: {result}")
            print("🔄 [LLMService] Initiating provider fallback chain...")
            fallbacks = ["azure", "groq", "azure_fallback", "nvidia"]
            if provider in fallbacks: fallbacks.remove(provider)
            for fb in fallbacks:
                print(f"   ► Attempting fallback provider: '{fb}'...")
                try:
                    if fb == "groq": result = await self.generate_with_groq(prompt, agent_name, tools, tool_choice, messages)
                    elif fb == "nvidia": result = await self.generate_with_nvidia(prompt, agent_name, tools, tool_choice, messages)
                    elif fb == "azure": result = await self.generate_with_azure(prompt, agent_name, tools, tool_choice, messages)
                    elif fb == "azure_fallback": result = await self.generate_with_azure_fallback(prompt, agent_name, tools, tool_choice, messages)
                except Exception as fb_err:
                    print(f"❌ [LLMService ERROR] Fallback provider '{fb}' crashed: {fb_err}")
                    continue
                
                # If tool call object is returned from fallback, return it
                if not isinstance(result, str):
                    return result
                if not is_error(result):
                    print(f"✅ [LLMService SUCCESS] Fallback provider '{fb}' succeeded!")
                    break
        return result
