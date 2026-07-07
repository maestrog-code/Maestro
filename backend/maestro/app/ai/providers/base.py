from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
from app.ai.schemas import AIMessage, LLMResponse


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a complete response from the LLM based on the conversation history.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream the response chunks from the LLM. 
        Note: Tool calling during streaming is often provider-dependent and complex.
        """
        pass

    @abstractmethod
    async def embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        """
        pass
