"""MEM: Método de Escolha Múltipla, com busca exaustiva ou por algoritmo genético.

Uso mais simples:

    from memga import memga, load_example
    print(memga(load_example("small"), size=2))
"""

from memga.api import MemgaResult, Ranked, load_example, memga
from memga.busca import GAConfig, traditional_choice
from memga.problema import Problem, load_problem

__version__ = "1.1.0"

__all__ = [
    "GAConfig",
    "MemgaResult",
    "Problem",
    "Ranked",
    "__version__",
    "load_example",
    "load_problem",
    "memga",
    "traditional_choice",
]
