"""
Custom LLM abstraction layer replacing LangChain dependencies.

This module provides a unified interface for interacting with different LLM providers
(Gemini, OpenAI, Anthropic) with tool calling support.

Main components:
- Tool: Base class for defining tools (replaces LangChain's BaseTool)
- LLMProvider: Abstract base class for LLM providers
- GeminiProvider, OpenAIProvider, AnthropicProvider: Concrete implementations
- AgentExecutor: Tool-calling loop (ReAct pattern)
- Message classes: SystemMessage, UserMessage, AssistantMessage, ToolResultMessage
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict


def _log_event(message: str) -> None:
    """Print a timestamped debug log line for agent execution."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[LLM {timestamp}] {message}", flush=True)


# =============================================================================
# MESSAGE CLASSES
# =============================================================================

@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class Message:
    """Base message class."""
    role: str
    content: str


@dataclass
class SystemMessage(Message):
    """System message."""
    def __init__(self, content: str):
        super().__init__(role="system", content=content)


@dataclass
class UserMessage(Message):
    """User message."""
    def __init__(self, content: str):
        super().__init__(role="user", content=content)


@dataclass
class AssistantMessage(Message):
    """Assistant message, optionally with tool calls."""
    tool_calls: List[ToolCall] = field(default_factory=list)

    def __init__(self, content: str, tool_calls: Optional[List[ToolCall]] = None):
        super().__init__(role="assistant", content=content)
        self.tool_calls = tool_calls or []


@dataclass
class ToolResultMessage(Message):
    """Result of a tool execution."""
    tool_call_id: str

    def __init__(self, tool_call_id: str, content: str):
        super().__init__(role="tool", content=content)
        self.tool_call_id = tool_call_id


# =============================================================================
# TOOL BASE CLASS
# =============================================================================

class Tool(BaseModel):
    """
    Base class for tools. Replaces LangChain's BaseTool.

    Subclasses should:
    - Set `name`, `description`, and `args_schema`
    - Implement the `run()` method

    Example:
        class MyTool(Tool):
            name: str = "my_tool"
            description: str = "Does something useful"
            args_schema: Type[BaseModel] = MyToolInput

            def run(self, param1: str, param2: int) -> str:
                return f"Result: {param1}, {param2}"
    """

    # Allow attrs objects in Pydantic fields
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel] = BaseModel

    def run(self, **kwargs) -> str:
        """Execute the tool. Override in subclass."""
        raise NotImplementedError("Subclass must implement run()")

    def to_openai_schema(self) -> Dict:
        """Convert to OpenAI function schema format."""
        schema = self.args_schema.model_json_schema()
        # Clean up schema - remove $defs and title
        schema.pop("$defs", None)
        schema.pop("title", None)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema
        }

    def to_anthropic_schema(self) -> Dict:
        """Convert to Anthropic tool schema format."""
        schema = self.args_schema.model_json_schema()
        schema.pop("$defs", None)
        schema.pop("title", None)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema
        }

    def to_gemini_schema(self) -> Dict:
        """Convert to Gemini function declaration format."""
        schema = self.args_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", [])
            }
        }


# =============================================================================
# LLM PROVIDER INTERFACE
# =============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None
    ) -> AssistantMessage:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: Conversation history
            tools: Optional list of tools the LLM can call

        Returns:
            AssistantMessage with content and/or tool_calls
        """
        pass


# =============================================================================
# GEMINI PROVIDER
# =============================================================================

class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name (default: gemini-2.5-flash)
            temperature: Temperature for generation (default: 0)
        """
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai is required for Gemini. "
                "Install with: pip install google-generativeai"
            )

        genai.configure(api_key=api_key)
        self.genai = genai
        self.model_name = model
        self.temperature = temperature

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert messages to Gemini format, extracting system prompt."""
        system_prompt = None
        contents = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, UserMessage):
                contents.append({"role": "user", "parts": [msg.content]})
            elif isinstance(msg, AssistantMessage):
                if msg.tool_calls:
                    # Assistant requested tool calls
                    parts = []
                    for tc in msg.tool_calls:
                        parts.append(self.genai.protos.Part(
                            function_call=self.genai.protos.FunctionCall(
                                name=tc.name,
                                args=tc.arguments
                            )
                        ))
                    contents.append({"role": "model", "parts": parts})
                else:
                    contents.append({"role": "model", "parts": [msg.content]})
            elif isinstance(msg, ToolResultMessage):
                # Tool result
                contents.append({
                    "role": "user",
                    "parts": [self.genai.protos.Part(
                        function_response=self.genai.protos.FunctionResponse(
                            name=msg.tool_call_id.split("_")[0] if "_" in msg.tool_call_id else msg.tool_call_id,
                            response={"result": msg.content}
                        )
                    )]
                })

        return system_prompt, contents

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None
    ) -> AssistantMessage:
        """Send messages to Gemini and get response."""
        system_prompt, contents = self._convert_messages(messages)

        # Build tool declarations
        tool_config = None
        if tools:
            tool_declarations = [t.to_gemini_schema() for t in tools]
            tool_config = [{"function_declarations": tool_declarations}]

        # Create model
        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            tools=tool_config,
            system_instruction=system_prompt
        )

        # Generate response
        _log_event(
            f"[Gemini] request sent to API | messages={len(messages)} "
            f"converted_parts={len(contents)} tools={len(tools or [])}"
        )
        response = model.generate_content(
            contents,
            generation_config={"temperature": self.temperature}
        )
        _log_event("[Gemini] response received from API")

        # Parse response
        if not response.candidates:
            return AssistantMessage(content="No response generated.")

        candidate = response.candidates[0]
        content_parts = candidate.content.parts

        # Check for function calls
        tool_calls = []
        text_content = ""

        for part in content_parts:
            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                # Convert protobuf args to dict
                args = dict(fc.args) if fc.args else {}
                tool_calls.append(ToolCall(
                    id=f"{fc.name}_{uuid.uuid4().hex[:8]}",
                    name=fc.name,
                    arguments=args
                ))
            elif hasattr(part, "text"):
                text_content += part.text

        return AssistantMessage(content=text_content, tool_calls=tool_calls)


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-mini",
        temperature: float = 0
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-5-mini)
            temperature: Temperature for generation (default: 0)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai is required for OpenAI. "
                "Install with: pip install openai"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert messages to OpenAI format."""
        openai_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, UserMessage):
                openai_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AssistantMessage):
                msg_dict = {"role": "assistant"}
                if msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                    msg_dict["content"] = msg.content or ""
                else:
                    msg_dict["content"] = msg.content
                openai_messages.append(msg_dict)
            elif isinstance(msg, ToolResultMessage):
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content
                })

        return openai_messages

    def _is_gpt5_family(self) -> bool:
        """Check whether the configured model is in the GPT-5 family."""
        return self.model.lower().startswith("gpt-5")

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None
    ) -> AssistantMessage:
        """Send messages to OpenAI and get response."""
        openai_messages = self._convert_messages(messages)

        # Build tools list
        openai_tools = None
        if tools:
            openai_tools = [
                {"type": "function", "function": t.to_openai_schema()}
                for t in tools
            ]

        # Make API call
        kwargs = {
            "model": self.model,
            "messages": openai_messages
        }
        # GPT-5 family currently only supports its default temperature behavior.
        # Keep explicit temperature for older model families.
        if not self._is_gpt5_family():
            kwargs["temperature"] = self.temperature
        else:
            _log_event(
                f"[OpenAI] model '{self.model}' uses default temperature; "
                "skipping explicit temperature parameter"
            )
        if openai_tools:
            kwargs["tools"] = openai_tools

        request_id = uuid.uuid4().hex[:8]
        role_sequence = [m.get("role", "?") for m in openai_messages]
        content_chars = 0
        for m in openai_messages:
            content = m.get("content")
            if isinstance(content, str):
                content_chars += len(content)
        _log_event(
            f"[OpenAI][{request_id}] payload ready | roles={role_sequence} "
            f"content_chars={content_chars} tool_defs={len(openai_tools or [])}"
        )
        _log_event(
            f"[OpenAI][{request_id}] request sent to API | messages={len(messages)} "
            f"converted_messages={len(openai_messages)} tools={len(tools or [])}"
        )
        response = self.client.chat.completions.create(**kwargs)
        usage = getattr(response, "usage", None)
        finish_reason = None
        if getattr(response, "choices", None):
            finish_reason = response.choices[0].finish_reason
        _log_event(
            f"[OpenAI][{request_id}] response received from API | "
            f"finish_reason={finish_reason} usage={usage}"
        )

        # Parse response
        message = response.choices[0].message
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))

        return AssistantMessage(
            content=message.content or "",
            tool_calls=tool_calls
        )


# =============================================================================
# ANTHROPIC PROVIDER
# =============================================================================

class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-sonnet-4-20250514)
            temperature: Temperature for generation (default: 0)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for Claude. "
                "Install with: pip install anthropic"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert messages to Anthropic format, extracting system prompt."""
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, UserMessage):
                anthropic_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AssistantMessage):
                if msg.tool_calls:
                    # Assistant with tool use
                    content = []
                    if msg.content:
                        content.append({"type": "text", "text": msg.content})
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments
                        })
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": content
                    })
                else:
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": msg.content
                    })
            elif isinstance(msg, ToolResultMessage):
                # Check if we need to merge with previous tool results
                if anthropic_messages and anthropic_messages[-1].get("role") == "user":
                    last_content = anthropic_messages[-1].get("content", [])
                    if isinstance(last_content, list):
                        # Merge tool results
                        last_content.append({
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content
                        })
                        continue

                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })

        return system_prompt, anthropic_messages

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None
    ) -> AssistantMessage:
        """Send messages to Anthropic and get response."""
        system_prompt, anthropic_messages = self._convert_messages(messages)

        # Build tools list
        anthropic_tools = None
        if tools:
            anthropic_tools = [t.to_anthropic_schema() for t in tools]

        # Make API call
        kwargs = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": self.temperature,
            "max_tokens": 4096
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        _log_event(
            f"[Anthropic] request sent to API | messages={len(messages)} "
            f"converted_messages={len(anthropic_messages)} tools={len(tools or [])}"
        )
        response = self.client.messages.create(**kwargs)
        _log_event("[Anthropic] response received from API")

        # Parse response
        text_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return AssistantMessage(content=text_content, tool_calls=tool_calls)


# =============================================================================
# AGENT EXECUTOR
# =============================================================================

class AgentExecutor:
    """
    Executes the ReAct (Reason + Act) loop with tool calling.

    The executor sends messages to the LLM, parses tool calls,
    executes tools, and feeds results back until the LLM provides
    a final answer (no tool calls).
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: List[Tool],
        max_iterations: int = 50,
        verbose: bool = False
    ):
        """
        Initialize the agent executor.

        Args:
            provider: LLM provider instance
            tools: List of available tools
            max_iterations: Maximum number of tool-calling iterations
            verbose: If True, print debug information
        """
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.tool_list = tools
        self.max_iterations = max_iterations
        self.verbose = verbose

    def run(
        self,
        system_prompt: str,
        user_input: str,
        chat_history: Optional[List[Message]] = None
    ) -> str:
        """
        Execute the agent loop until a final answer is reached.

        Args:
            system_prompt: System instructions for the agent
            user_input: User's query
            chat_history: Optional previous conversation history

        Returns:
            Final text response from the agent
        """
        # Build initial messages
        messages: List[Message] = [SystemMessage(system_prompt)]

        if chat_history:
            messages.extend(chat_history)

        messages.append(UserMessage(user_input))
        preview = user_input.replace("\n", " ")[:120]
        _log_event(
            f"AgentExecutor.run start | input='{preview}' | "
            f"history_messages={len(chat_history or [])} | max_iterations={self.max_iterations}"
        )

        for iteration in range(self.max_iterations):
            _log_event(
                f"Iteration {iteration + 1} start | message_count={len(messages)}"
            )
            if self.verbose:
                print(f"\n[Iteration {iteration + 1}] Calling LLM...")

            # Call LLM
            try:
                response = self.provider.chat(messages, self.tool_list)
            except Exception as e:
                _log_event(f"Provider call failed: {str(e)}")
                raise

            _log_event(
                f"Iteration {iteration + 1} response | tool_calls={len(response.tool_calls)} "
                f"content_chars={len(response.content or '')}"
            )

            # Check if we have a final answer (no tool calls)
            if not response.tool_calls:
                _log_event(f"Final answer reached on iteration {iteration + 1}")
                if self.verbose:
                    print(f"[Final Answer] {response.content[:200]}...")
                return response.content

            # Process tool calls
            messages.append(response)

            for tool_call in response.tool_calls:
                if self.verbose:
                    print(f"  Tool: {tool_call.name}")
                    print(f"  Args: {tool_call.arguments}")

                # Execute tool
                tool = self.tools.get(tool_call.name)
                if tool is None:
                    result = f"Error: Unknown tool '{tool_call.name}'"
                    _log_event(f"Tool lookup failed | name={tool_call.name}")
                else:
                    _log_event(
                        f"Running tool '{tool_call.name}' "
                        f"with args={list(tool_call.arguments.keys())}"
                    )
                    try:
                        result = tool.run(**tool_call.arguments)
                        _log_event(
                            f"Tool '{tool_call.name}' completed | result_chars={len(result)}"
                        )
                    except Exception as e:
                        _log_event(f"Tool '{tool_call.name}' failed: {str(e)}")
                        result = f"Error executing tool: {str(e)}"

                if self.verbose:
                    result_preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"  Result: {result_preview}")

                # Add tool result
                messages.append(ToolResultMessage(tool_call.id, result))

        # Max iterations reached
        _log_event("Max iterations reached without final answer")
        return "I apologize, but I couldn't complete the task within the allowed number of iterations."


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_provider(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    temperature: float = 0
) -> LLMProvider:
    """
    Factory function to create an LLM provider.

    Args:
        provider: Provider name ('gemini', 'openai', 'claude')
        api_key: API key for the provider
        model: Optional model name (uses default if not specified)
        temperature: Temperature for generation

    Returns:
        LLMProvider instance
    """
    provider = provider.lower()
    _log_event(f"Creating provider '{provider}' with model='{model or 'default'}'")

    if provider == "gemini":
        return GeminiProvider(
            api_key=api_key,
            model=model or "gemini-2.5-flash",
            temperature=temperature
        )
    elif provider == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-5-mini",
            temperature=temperature
        )
    elif provider == "claude":
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            temperature=temperature
        )
    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Supported providers: 'gemini', 'openai', 'claude'"
        )
