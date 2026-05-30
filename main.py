"""Ponto de entrada do Agente Financeiro.

Executar com:  python -m main
"""
import asyncio

from financebot.bot import run

if __name__ == "__main__":
    asyncio.run(run())
