"""Fachada de acesso ao banco de dados.

O restante da aplicação depende apenas deste módulo, e não diretamente de
`sqlite.py`. Isso mantém a porta aberta para, no futuro, trocar o mecanismo
de armazenamento local (outro arquivo, outra biblioteca) sem precisar
alterar quem consome `obter_conexao` / `inicializar_banco`.
"""

from database.sqlite import CAMINHO_BANCO, inicializar_banco, obter_conexao

__all__ = ["obter_conexao", "inicializar_banco", "CAMINHO_BANCO"]
