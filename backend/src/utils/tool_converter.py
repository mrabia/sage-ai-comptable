"""
Utilitaire pour convertir les outils CrewAI en outils LangChain compatibles
Option A implementation - Modern LangChain stack
"""

from langchain.tools import BaseTool as LangChainBaseTool
from typing import Type, Any, Optional, Dict
from pydantic import BaseModel
import inspect


class CrewAIToLangChainToolWrapper(LangChainBaseTool):
    """Wrapper pour convertir un outil CrewAI en outil LangChain"""
    
    crewai_tool: Any
    
    def __init__(self, crewai_tool: Any, **kwargs):
        self.crewai_tool = crewai_tool
        
        # Extraire les métadonnées de l'outil CrewAI
        name = getattr(crewai_tool, 'name', crewai_tool.__class__.__name__)
        description = getattr(crewai_tool, 'description', f"Tool: {name}")
        
        super().__init__(
            name=name,
            description=description,
            **kwargs
        )
    
    def _run(self, *args, **kwargs) -> str:
        """Exécute l'outil CrewAI"""
        try:
            # Appeler la méthode _run de l'outil CrewAI
            if hasattr(self.crewai_tool, '_run'):
                return self.crewai_tool._run(*args, **kwargs)
            elif hasattr(self.crewai_tool, 'run'):
                return self.crewai_tool.run(*args, **kwargs)
            elif callable(self.crewai_tool):
                return self.crewai_tool(*args, **kwargs)
            else:
                return f"❌ Impossible d'exécuter l'outil {self.name}"
        except Exception as e:
            return f"❌ Erreur dans l'outil {self.name}: {str(e)}"
    
    async def _arun(self, *args, **kwargs) -> str:
        """Version async (fallback vers sync)"""
        return self._run(*args, **kwargs)


def convert_crewai_tools_to_langchain(crewai_tools: list) -> list:
    """
    Convertit une liste d'outils CrewAI en outils LangChain compatibles
    
    Args:
        crewai_tools: Liste des outils CrewAI
        
    Returns:
        Liste des outils LangChain compatibles
    """
    langchain_tools = []
    
    for tool in crewai_tools:
        try:
            wrapper = CrewAIToLangChainToolWrapper(tool)
            langchain_tools.append(wrapper)
            print(f"✅ Converted tool: {wrapper.name}")
        except Exception as e:
            print(f"❌ Failed to convert tool {getattr(tool, 'name', 'unknown')}: {e}")
            continue
    
    print(f"✅ Converted {len(langchain_tools)}/{len(crewai_tools)} tools successfully")
    return langchain_tools


def create_langchain_tool_from_function(func, name: str, description: str):
    """
    Crée un outil LangChain à partir d'une fonction simple
    
    Args:
        func: Fonction à wrapper
        name: Nom de l'outil
        description: Description de l'outil
        
    Returns:
        Outil LangChain compatible
    """
    
    class FunctionTool(LangChainBaseTool):
        name = name
        description = description
        
        def _run(self, *args, **kwargs) -> str:
            try:
                return str(func(*args, **kwargs))
            except Exception as e:
                return f"❌ Erreur dans {name}: {str(e)}"
        
        async def _arun(self, *args, **kwargs) -> str:
            return self._run(*args, **kwargs)
    
    return FunctionTool()