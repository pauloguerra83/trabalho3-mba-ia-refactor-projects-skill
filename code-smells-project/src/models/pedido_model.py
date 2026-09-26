def inserir(db, usuario_id, status, total):
    cursor = db.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
        (usuario_id, status, total),
    )
    return cursor.lastrowid


def inserir_item(db, pedido_id, produto_id, quantidade, preco_unitario):
    db.execute(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
        (pedido_id, produto_id, quantidade, preco_unitario),
    )


def atualizar_status(db, pedido_id, status):
    db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))


def listar_com_itens(db, usuario_id=None):
    """Pedidos com seus itens em uma única query (JOIN), opcionalmente filtrados por usuário."""
    rows = db.execute(
        """
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
        WHERE (? IS NULL OR p.usuario_id = ?)
        ORDER BY p.id, i.id
        """,
        (usuario_id, usuario_id),
    ).fetchall()

    pedidos = {}
    for row in rows:
        pedido = pedidos.setdefault(row["id"], {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] if row["produto_nome"] is not None else "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def resumo_vendas(db):
    row = db.execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(status = 'pendente'), 0) AS pendentes,
               COALESCE(SUM(status = 'aprovado'), 0) AS aprovados,
               COALESCE(SUM(status = 'cancelado'), 0) AS cancelados
        FROM pedidos
        """
    ).fetchone()
    return dict(row)
