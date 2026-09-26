CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def _to_dict(row):
    return {campo: row[campo] for campo in CAMPOS}


def listar(db):
    return [_to_dict(row) for row in db.execute("SELECT * FROM produtos").fetchall()]


def buscar_por_id(db, produto_id):
    row = db.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _to_dict(row) if row else None


def buscar(db, termo, categoria=None, preco_min=None, preco_max=None):
    sql, params = "SELECT * FROM produtos WHERE 1=1", []
    if termo:
        sql += " AND (nome LIKE ? OR descricao LIKE ?)"
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if preco_min:
        sql += " AND preco >= ?"
        params.append(preco_min)
    if preco_max:
        sql += " AND preco <= ?"
        params.append(preco_max)
    return [_to_dict(row) for row in db.execute(sql, params).fetchall()]


def criar(db, nome, descricao, preco, estoque, categoria):
    cursor = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    return cursor.lastrowid


def atualizar(db, produto_id, nome, descricao, preco, estoque, categoria):
    db.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )


def deletar(db, produto_id):
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))


def baixar_estoque(db, produto_id, quantidade):
    db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id))
