TABELAS_RESET = ("itens_pedido", "pedidos", "produtos", "usuarios")  # filhas antes das mães


def contagens(db):
    row = db.execute(
        """
        SELECT (SELECT COUNT(*) FROM produtos) AS produtos,
               (SELECT COUNT(*) FROM usuarios) AS usuarios,
               (SELECT COUNT(*) FROM pedidos) AS pedidos
        """
    ).fetchone()
    return dict(row)


def limpar_tabelas(db):
    for tabela in TABELAS_RESET:  # nomes fixos do código, nunca vindos do cliente
        db.execute(f"DELETE FROM {tabela}")


def executar_consulta_somente_leitura(db, sql):
    """Executa uma consulta com a conexão em modo query_only: qualquer escrita é recusada pelo SQLite."""
    db.execute("PRAGMA query_only = ON")
    try:
        return [dict(row) for row in db.execute(sql).fetchall()]
    finally:
        db.execute("PRAGMA query_only = OFF")
