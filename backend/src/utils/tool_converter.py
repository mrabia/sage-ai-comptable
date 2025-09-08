"""
Utilitaire pour convertir les outils Sage en outils LangChain compatibles
Modern LangChain 0.3.x + Pydantic v2 implementation
"""

from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from typing import Type, Any, Optional, Dict, Union
from pydantic import BaseModel, Field
import inspect


class SageToLangChainToolWrapper(LangChainBaseTool):
    """Wrapper moderne pour convertir un outil Sage en outil LangChain 0.3.x"""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description") 
    sage_tool: Any = Field(..., description="The wrapped Sage tool")
    
    def __init__(self, sage_tool: Any, **kwargs):
        # Extraire les métadonnées de l'outil Sage
        tool_name = getattr(sage_tool, 'name', sage_tool.__class__.__name__)
        tool_description = getattr(sage_tool, 'description', f"Tool: {tool_name}")
        
        super().__init__(
            name=tool_name,
            description=tool_description,
            sage_tool=sage_tool,
            **kwargs
        )
    
    def _run(
        self, 
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any
    ) -> str:
        """Exécute l'outil Sage avec la nouvelle interface LangChain 0.3.x"""
        try:
            # Appeler la méthode _run de l'outil Sage
            if hasattr(self.sage_tool, '_run'):
                return str(self.sage_tool._run(**kwargs))
            elif hasattr(self.sage_tool, 'run'):
                return str(self.sage_tool.run(**kwargs))
            elif callable(self.sage_tool):
                return str(self.sage_tool(**kwargs))
            else:
                return f"❌ Impossible d'exécuter l'outil {self.name}"
        except Exception as e:
            return f"❌ Erreur dans l'outil {self.name}: {str(e)}"
    
    async def _arun(
        self, 
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any
    ) -> str:
        """Version async (fallback vers sync)"""
        return self._run(run_manager=run_manager, **kwargs)


def convert_sage_tools_to_langchain(sage_tools: list) -> list:
    """
    Convertit une liste d'outils Sage en outils LangChain 0.3.x compatibles
    
    Args:
        sage_tools: Liste des outils Sage
        
    Returns:
        Liste des outils LangChain compatibles
    """
    langchain_tools = []
    
    for tool in sage_tools:
        try:
            wrapper = SageToLangChainToolWrapper(tool)
            langchain_tools.append(wrapper)
            print(f"✅ Converted tool: {wrapper.name}")
        except Exception as e:
            print(f"❌ Failed to convert tool {getattr(tool, 'name', 'unknown')}: {e}")
            continue
    
    print(f"✅ Converted {len(langchain_tools)}/{len(sage_tools)} tools successfully")
    return langchain_tools

# Backward compatibility alias
convert_crewai_tools_to_langchain = convert_sage_tools_to_langchain


def create_langchain_tool_from_function(func, name: str, description: str):
    """
    Crée un outil LangChain 0.3.x à partir d'une fonction simple
    
    Args:
        func: Fonction à wrapper
        name: Nom de l'outil
        description: Description de l'outil
        
    Returns:
        Outil LangChain compatible
    """
    
    class FunctionTool(LangChainBaseTool):
        name: str = Field(default=name, description="Function tool name")
        description: str = Field(default=description, description="Function tool description")
        
        def _run(
            self, 
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any
        ) -> str:
            try:
                return str(func(**kwargs))
            except Exception as e:
                return f"❌ Erreur dans {name}: {str(e)}"
        
        async def _arun(
            self, 
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any
        ) -> str:
            return self._run(run_manager=run_manager, **kwargs)
    
    return FunctionTool()